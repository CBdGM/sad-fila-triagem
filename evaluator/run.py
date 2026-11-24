"""Execução do avaliador num repositório: seleção, texto, chamada A e gravação."""
from datetime import datetime, timezone

from collector import store
from collector.collect import body_hash, utc

from . import fetch, jev
from .redact import redact
from .clean import CLEANING_VERSION, clean_issue
from .questions import QUESTIONS_VERSION

BATCH_SIZE = 50
MAX_STATE_CHARS = 120_000  # ~30 mil tokens (PoC: 32k por chamada, com folga), estimados como chars ÷ 4
TRAINING_LABELS = {"no_action", "action"}


def versions(model):
    return {"model": model, "questions": QUESTIONS_VERSION, "cleaning": CLEANING_VERSION}


def _key(number, sha, v):
    return (number, sha, v["model"], v["questions"], v["cleaning"])


def select(issues, outcomes, mode):
    """Issues candidatas do modo, mais recentes primeiro.

    backfill: fechadas cujo desfecho mais recente é no_action ou action (as que treinam o calibrador).
    daily: abertas.
    """
    if mode == "daily":
        chosen = [i for i in issues.values() if i["state"] == "open"]
    elif mode == "backfill":
        latest = {}
        for o in outcomes:  # outcomes.jsonl só acrescenta: a última linha da issue é a mais recente
            latest[o["number"]] = o
        chosen = [i for i in issues.values()
                  if i["state"] == "closed" and latest.get(i["number"], {}).get("label") in TRAINING_LABELS
                  and latest[i["number"]]["closed_at"] == i.get("closed_at")]
    else:
        raise ValueError(f"modo desconhecido: {mode}")
    return sorted(chosen, key=lambda i: (i["created_at"], i["number"]), reverse=True)


def pending(candidates, predictions, v):
    done = {_key(p["number"], p["body_sha256"], p["versions"]) for p in predictions}
    return [i for i in candidates if _key(i["number"], i["body_sha256"], v) not in done]


def build_row(repo, issue, text, answers, prov, mode, first_seen, v, predicted_at):
    return {
        "schema_version": 1,
        "repo": repo,
        "number": issue["number"],
        "predicted_at": predicted_at,
        "mode": mode,
        "first_seen": first_seen,
        "body_sha256": issue["body_sha256"],
        "versions": v,
        "provenance": {"calls": [prov]},
        "answers": answers,
        "input_text": redact(text)[0],  # o Jev recebeu `text`; o gravado vai sem credenciais
    }


def evaluate_repo(gh, js, repo, model, data_dir, *, mode, max_items=None, batch_size=BATCH_SIZE,
                  now=None, emit=None, ask=jev.ask, **kw):
    """Avalia as issues pendentes. Devolve {"added", "tokens", "skipped", "edited", "redacted", "other_model", "pending_left"}.

    Cada previsão é gravada logo depois da chamada; uma falha no meio mantém as anteriores.
    """
    jev.check_model(model)
    folder = store.repo_dir(data_dir, repo)
    issues_path, preds_path = folder / "issues.jsonl", folder / "predictions.jsonl"
    if not issues_path.exists():
        raise FileNotFoundError(f"{issues_path} não existe; rode o coletor antes (python -m collector)")
    outcomes = store.read_jsonl(folder / "outcomes.jsonl") if mode == "backfill" else []
    if mode == "backfill" and not outcomes:
        raise FileNotFoundError(f"{folder / 'outcomes.jsonl'} vazio ou ausente; rode os desfechos antes (python -m outcomes)")
    predictions = store.read_jsonl(preds_path)
    v = versions(model)
    todo = pending(select(store.read_issues(issues_path), outcomes, mode), predictions, v)
    left_after = max(0, len(todo) - max_items) if max_items is not None else 0
    if max_items is not None:
        todo = todo[:max_items]

    seen = {p["number"] for p in predictions}
    res = {"added": 0, "tokens": 0, "skipped": [], "edited": [], "redacted": [], "other_model": set(),
           "pending_left": left_after}
    for start in range(0, len(todo), batch_size):
        chunk = todo[start:start + batch_size]
        texts = fetch.fetch_texts(gh, repo, [i["number"] for i in chunk], **kw)
        for issue in chunk:
            t = texts.get(issue["number"])
            if t is None:
                res["skipped"].append(issue["number"])
                continue
            if body_hash(t.get("title"), t.get("body")) != issue["body_sha256"]:
                res["edited"].append(issue["number"])  # editada depois da coleta: fica para a próxima
                continue
            text = clean_issue({"title": t.get("title") or "", "body": t.get("body") or ""})[:MAX_STATE_CHARS]
            answers, prov = ask(js, model, text)
            if redact(text)[1]:
                res["redacted"].append(issue["number"])
            row = build_row(repo, issue, text, answers, prov, mode, issue["number"] not in seen, v,
                            utc(now or datetime.now(timezone.utc)))
            store.append_jsonl(preds_path, [row], "prediction", label=lambda r: f"previsão #{r['number']}")
            seen.add(issue["number"])
            res["added"] += 1
            res["tokens"] += prov["tokens"] or 0
            if prov["served_by"] != model:
                res["other_model"].add(prov["served_by"])
        if emit:
            emit(f"previsões: {start + len(chunk)}/{len(todo)}")
    res["other_model"] = sorted(res["other_model"])
    return res
