"""Montagem da fila e das métricas. Sem calibrador, todas as issues vão para human_review."""
import json
from pathlib import Path

from collector import store
from collector.collect import is_open

SEVERITY_ORDER = ["critical", "high", "medium", "low"]
INDEX_HTML = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fila de triagem</title></head>
<body style="font-family:system-ui,sans-serif;max-width:40rem;margin:2rem auto;padding:0 1rem">
<h1>Fila de triagem (SAD v3)</h1>
<p>O site da fila ainda está em construção. Os dados são atualizados todo dia pelo job:</p>
<ul><li><a href="queue.json">queue.json</a>: a fila</li><li><a href="metrics.json">metrics.json</a>: as métricas</li></ul>
<p>Gerado em {generated_at}.</p>
</body></html>
"""


def latest_predictions(predictions):
    """{número: previsão mais recente} (predicted_at maior; empate, a última do arquivo)."""
    out = {}
    for p in predictions:
        cur = out.get(p["number"])
        if cur is None or p["predicted_at"] >= cur["predicted_at"]:
            out[p["number"]] = p
    return out


def build_items(repo, issues, predictions):
    """Itens da fila de um repositório e quantas abertas ficaram de fora por falta de previsão."""
    latest = latest_predictions(predictions)
    items, missing = [], 0
    for i in issues.values():
        if not is_open(i):
            continue
        p = latest.get(i["number"])
        if p is None:
            missing += 1
            continue
        items.append({
            "repo": repo,
            "number": i["number"],
            "url": i["url"],
            "title": i["title"],
            "labels": i.get("labels", []),
            "created_at": i["created_at"],
            "updated_at": i["updated_at"],
            "first_seen_at": i["first_seen_at"],
            "band": "human_review",
            "p_no_action": None,
            "reason": None,
            "severity": p["answers"]["severity"]["level"],
            "evidence": [],
        })
    return items, missing


def sort_items(items):
    return sorted(items, key=lambda it: (SEVERITY_ORDER.index(it["severity"]), it["created_at"], it["repo"], it["number"]))


def build(cfg, data_dir, generated_at):
    """Devolve (queue, metrics, resumo por repositório)."""
    repos, items, summary = [], [], {}
    for r in cfg["repos"]:
        if not r.get("enabled", True):
            continue
        repo = r["repo"]
        folder = store.repo_dir(data_dir, repo)
        state = store.read_state(folder / "state.json") or {}
        its, missing = build_items(repo, store.read_issues(folder / "issues.jsonl"),
                                   store.read_jsonl(folder / "predictions.jsonl"))
        items += its
        summary[repo] = {"items": len(its), "open_without_prediction": missing}
        repos.append({
            "repo": repo,
            "last_success_at": state.get("last_success_at"),
            "model": cfg["model"],
            "calibrator": None,
            "counts": {"attention": 0, "human_review": len(its), "likely_no_action": 0},
        })
    queue = {"schema_version": 1, "generated_at": generated_at, "repos": repos, "items": sort_items(items)}
    metrics = {"schema_version": 1, "generated_at": generated_at, "evaluations": []}
    return queue, metrics, summary


def write(out_dir, queue, metrics):
    """Valida os dois e só então grava; fora do contrato, nada é gravado (ContractError)."""
    store.validate("queue", queue, "queue.json")
    store.validate("metrics", metrics, "metrics.json")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    compact = {"ensure_ascii": False, "separators": (",", ":")}  # ~30% menor; o Front formata se quiser
    (out / "queue.json").write_text(json.dumps(queue, **compact) + "\n", encoding="utf-8")
    (out / "metrics.json").write_text(json.dumps(metrics, **compact) + "\n", encoding="utf-8")
    (out / "index.html").write_text(INDEX_HTML.format(generated_at=queue["generated_at"]), encoding="utf-8")
