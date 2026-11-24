"""Execução dos desfechos de um repositório: pendentes, lotes e gravação."""
from collections import Counter
from datetime import datetime, timezone

from collector import store
from collector.collect import utc

from . import fetch, rules

BATCH_SIZE = 50
STATE_REASONS = {"completed", "not_planned", "duplicate"}


def pending(issues, outcomes):
    """Issues fechadas sem desfecho para aquele fechamento (number + closed_at), mais antigas primeiro."""
    done = {(o["number"], o["closed_at"]) for o in outcomes}
    todo = [i for i in issues.values()
            if i["state"] == "closed" and i.get("closed_at") and (i["number"], i["closed_at"]) not in done]
    return sorted(todo, key=lambda i: (i["closed_at"], i["number"]))


def build_row(repo, issue, facts, repo_cfg, recorded_at):
    state_reason = issue.get("state_reason") if issue.get("state_reason") in STATE_REASONS else None
    verdict = rules.classify(state_reason=state_reason, labels=issue.get("labels", []),
                             closed_by=facts["closed_by"], merged_pr=facts["merged_pr"], repo_cfg=repo_cfg)
    return {
        "schema_version": 1,
        "repo": repo,
        "number": issue["number"],
        "recorded_at": recorded_at,
        "closed_at": issue["closed_at"],
        "state_reason": state_reason,
        "labels_at_close": issue.get("labels", []),  # labels atuais (limitação registrada no design)
        "closed_by": facts["closed_by"],
        "closed_by_bot": facts["closed_by_bot"],
        "merged_pr": facts["merged_pr"],
        "label": verdict["label"],
        "reason": verdict["reason"],
        "exclusion_reason": verdict["exclusion_reason"],
        "rules_version": rules.RULES_VERSION,
    }


def collect_outcomes(s, repo, repo_cfg, data_dir, *, max_items=None, batch_size=BATCH_SIZE,
                     now=None, emit=None, **kw):
    """Grava desfechos pendentes em lotes. Devolve {"added", "skipped", "truncated", "pending_left"}.

    Cada lote é gravado assim que termina; uma falha no meio mantém os lotes anteriores.
    """
    folder = store.repo_dir(data_dir, repo)
    issues_path, outcomes_path = folder / "issues.jsonl", folder / "outcomes.jsonl"
    if not issues_path.exists():
        raise FileNotFoundError(f"{issues_path} não existe; rode o coletor antes (python -m collector)")
    todo = pending(store.read_issues(issues_path), store.read_jsonl(outcomes_path))
    left_after = max(0, len(todo) - max_items) if max_items is not None else 0
    if max_items is not None:
        todo = todo[:max_items]

    added, skipped, truncated = 0, [], []
    for start in range(0, len(todo), batch_size):
        chunk = todo[start:start + batch_size]
        facts = fetch.fetch_batch(s, repo, [i["number"] for i in chunk], **kw)
        recorded_at = utc(now or datetime.now(timezone.utc))
        rows = []
        for issue in chunk:
            f = facts.get(issue["number"])
            if f is None:
                skipped.append(issue["number"])
                continue
            if f["truncated"]:
                truncated.append(issue["number"])
            rows.append(build_row(repo, issue, f, repo_cfg, recorded_at))
        store.append_jsonl(outcomes_path, rows, "outcome", label=lambda r: f"desfecho #{r['number']}")
        added += len(rows)
        if emit:
            emit(f"desfechos: {start + len(chunk)}/{len(todo)}")
    return {"added": added, "skipped": skipped, "truncated": truncated, "pending_left": left_after}


def phase0_summary(outcomes):
    """Totais por classe e % sem ação entre no_action e action (o portão da Fase 0)."""
    counts = Counter(o["label"] for o in outcomes)
    decided = counts["no_action"] + counts["action"]
    pct = 100 * counts["no_action"] / decided if decided else None
    reasons = Counter(o["reason"] for o in outcomes if o["label"] == "no_action")
    excluded = Counter(o["exclusion_reason"] for o in outcomes if o["label"] == "excluded")
    return {"no_action": counts["no_action"], "action": counts["action"], "excluded": counts["excluded"],
            "pct_no_action": pct, "reasons": dict(reasons), "exclusions": dict(excluded)}
