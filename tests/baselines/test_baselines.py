import json

import numpy as np
import pytest

from baselines import features
from baselines.__main__ import main
from baselines.data import load_repo, temporal_split
from baselines.metrics import evaluate, threshold_for_precision
from collector import store

from ..evaluator.fakes import outcome, rec


def pred(issue, text, is_defect=0.5, mode="backfill"):
    return {"schema_version": 1, "repo": "o/r", "number": issue["number"], "predicted_at": "2026-11-23T00:00:00Z",
            "mode": mode, "first_seen": True, "body_sha256": issue["body_sha256"],
            "versions": {"model": "jev-1.14.0", "questions": "q1", "cleaning": "clean-1"},
            "provenance": {"calls": [{"call": "A", "served_by": "jev-1.14.0", "request_id": None,
                                      "latency_ms": 1.0, "tokens": 10}]},
            "answers": {"is_defect": is_defect, "actionable": 0.5, "enough_info": 0.5, "usage_question": 0.1,
                        "severity": {"probs": [0.25] * 4, "level": "low"}}, "input_text": text}


def write_repo(root, rows):
    """rows: (número, created, label, texto, is_defect, closed)."""
    folder = store.repo_dir(root, "o/r")
    issues, outs, preds = {}, [], []
    for n, created, label, text, d, closed in rows:
        i = rec(n, state="closed", created=created, closed=closed)
        issues[n] = i
        outs.append(outcome(n, label, closed if label != "reopened" else "2026-01-01T00:00:00Z"))
        if label == "reopened":
            outs[-1]["label"] = "action"
        preds.append(pred(i, text, d))
    store.write_issues(folder / "issues.jsonl", issues)
    (folder / "outcomes.jsonl").write_text("".join(json.dumps(o) + "\n" for o in outs))
    (folder / "predictions.jsonl").write_text("".join(json.dumps(p) + "\n" for p in preds))
    return folder


C = "2026-11-15T00:00:00Z"


def test_rotulo_excluded_e_reaberta_ficam_fora(tmp_path):
    write_repo(tmp_path, [(1, "2026-10-01T00:00:00Z", "no_action", "a", 0.1, C),
                          (2, "2026-10-02T00:00:00Z", "action", "b", 0.9, C),
                          (3, "2026-10-03T00:00:00Z", "excluded", "c", 0.5, C),
                          (4, "2026-10-04T00:00:00Z", "reopened", "d", 0.5, C)])
    ex = {e.number: e.y for e in load_repo(tmp_path, "o/r")}
    assert ex == {1: 1, 2: 0}


def test_previsao_daily_nao_entra(tmp_path):
    folder = write_repo(tmp_path, [(1, "2026-10-01T00:00:00Z", "action", "a", 0.9, C)])
    p = json.loads((folder / "predictions.jsonl").read_text())
    p["mode"] = "daily"
    (folder / "predictions.jsonl").write_text(json.dumps(p) + "\n")
    assert load_repo(tmp_path, "o/r") == []


def test_corte_temporal_teste_mais_recente():
    from baselines.data import Example
    ex = [Example("o/r", n, f"2026-10-{n:02d}T00:00:00Z", "t", {}, n % 2) for n in (5, 1, 9, 3, 7, 2, 8, 4, 6, 10)]
    sp = temporal_split(ex)
    assert len(sp.train) == 7 and len(sp.test) == 3
    assert max(e.created_at for e in sp.train) < min(e.created_at for e in sp.test)


@pytest.mark.parametrize("name, text", [
    ("stack_trace", "Traceback (most recent call last):\n  File x"),
    ("stack_trace", "TypeError: undefined is not a function"),
    ("code_block", "```\ncode\n```"),
    ("numbered_steps", "1. open\n2. click"),
    ("version", "VS Code 1.107.0"),
    ("usage_question", "How do I configure this?"),
    ("image", "see [image]"),
    ("link", "https://example.com"),
])
def test_cada_sinal(name, text):
    assert features.signals(text)[name] == 1
    assert features.signals("plain words only")[name] == 0


def test_regras_fixas():
    assert features.rule_score("How do I change the theme?") == 2           # curto + pergunta
    assert features.rule_score("Crash " * 40 + "\nTypeError: x\n1. a\n```c```\nv1.2.3") == -4


def test_corte_por_precisao_alvo():
    y = np.array([1] * 12 + [0] + [1] * 5 + [0] * 10)
    s = np.arange(len(y))[::-1].astype(float)          # notas decrescentes na ordem acima
    t = threshold_for_precision(y, s, target=0.9, min_flagged=10)
    flagged = s >= t
    assert (y[flagged] == 1).mean() >= 0.9 and flagged.sum() == 18
    assert threshold_for_precision(np.array([0, 1] * 10), np.arange(20.0), target=0.9) is None


def test_metricas_nulas_quando_alvo_inatingivel():
    y = np.array([0, 1] * 20)
    r = evaluate(y, np.random.default_rng(0).random(40), y, np.random.default_rng(1).random(40), probability=True)
    assert r["precision_no_action"] is None and r["coverage"] is None and 0 <= r["auc"] <= 1


def test_cli_gera_relatorio_e_json_validos(tmp_path):
    rows = []
    for n in range(1, 81):
        noact = n % 2 == 0
        text = ("How do I change the setting? " if noact else "Crash on start\nTypeError: boom\n1. open\n```x```\n")
        rows.append((n, f"2026-0{1 + n // 20}-{1 + n % 20:02d}T00:00:00Z", "no_action" if noact else "action",
                     text + f" issue {n}", 0.2 if noact else 0.9, C))
    data = tmp_path / "data"
    write_repo(data, rows)
    out = tmp_path / "out"
    from datetime import datetime, timezone
    assert main(["--data-dir", str(data), "--out", str(out), "--repo", "o/r"],
                now=datetime(2026, 11, 24, tzinfo=timezone.utc)) == 0
    doc = json.loads((out / "baselines-2026-11-24.json").read_text())
    store.validate("metrics", doc)
    assert {e["model"] for e in doc["evaluations"]} == {"heuristic-rules", "heuristic-lr", "tfidf-lr", "jev-raw", "jev-lr"}
    assert {e["repo"] for e in doc["evaluations"]} == {"o/r", "all"}
    md = (out / "baselines-2026-11-24.md").read_text()
    assert "| TF-IDF + regressão logística |" in md
    tfidf = next(e for e in doc["evaluations"] if e["model"] == "tfidf-lr" and e["repo"] == "o/r")
    assert tfidf["auc"] > 0.9  # sinal fácil e separável: o modelo precisa achar


def test_autor_externo():
    from baselines.data import Example
    mk = lambda a: Example("o/r", 1, "2026-10-01T00:00:00Z", "t", {}, 1, a)  # noqa: E731
    assert [mk(a).external for a in ("NONE", "CONTRIBUTOR", "FIRST_TIME_CONTRIBUTOR", "MEMBER", "OWNER", "COLLABORATOR")] \
        == [True, True, True, False, False, False]
