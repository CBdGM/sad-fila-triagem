import json

import pytest

from collector import store
from publisher.build import build, build_items, write
from publisher.__main__ import main

from ..evaluator.fakes import rec

NOW = "2026-11-24T09:00:00Z"
CFG = {"schema_version": 1, "model": "jev-1.14.0", "first_run": {"open_max": 5, "closed_months": 1},
       "repos": [{"repo": "o/r", "closing_labels": {"duplicate": "duplicate"}}]}


def pred(n, level="medium", at="2026-11-22T00:00:00Z"):
    return {"number": n, "predicted_at": at,
            "answers": {"severity": {"probs": [0.25] * 4, "level": level}}}


def issues_of(*records):
    return {r["number"]: r for r in records}


def test_so_abertas_com_previsao():
    issues = issues_of(rec(1), rec(2), rec(3), rec(4, state="closed", closed="2026-11-10T00:00:00Z"))
    items, missing = build_items("o/r", issues, [pred(1), pred(2), pred(4)])
    assert sorted(i["number"] for i in items) == [1, 2] and missing == 1
    it = items[0]
    assert (it["band"], it["p_no_action"], it["reason"], it["evidence"]) == ("human_review", None, None, [])


def test_severidade_da_previsao_mais_recente():
    items, _ = build_items("o/r", issues_of(rec(1)),
                           [pred(1, "low", "2026-11-22T00:00:00Z"), pred(1, "critical", "2026-11-23T00:00:00Z")])
    assert items[0]["severity"] == "critical"


def test_ordem_severidade_depois_data(tmp_path):
    folder = store.repo_dir(tmp_path, "o/r")
    store.write_issues(folder / "issues.jsonl", issues_of(
        rec(1, created="2026-11-01T00:00:00Z"), rec(2, created="2026-11-20T00:00:00Z"),
        rec(3, created="2026-11-05T00:00:00Z")))
    (folder / "predictions.jsonl").write_text(
        "".join(json.dumps(p) + "\n" for p in [pred(1, "low"), pred(2, "critical"), pred(3, "low")]))
    queue, metrics, summary = build(CFG, tmp_path, NOW)
    assert [i["number"] for i in queue["items"]] == [2, 1, 3]
    assert queue["repos"][0]["counts"] == {"attention": 0, "human_review": 3, "likely_no_action": 0}
    assert queue["repos"][0]["calibrator"] is None and metrics["evaluations"] == []
    write(tmp_path / "public", queue, metrics)
    for name, contract in (("queue.json", "queue"), ("metrics.json", "metrics")):
        store.validate(contract, json.loads((tmp_path / "public" / name).read_text()))
    assert "queue.json" in (tmp_path / "public" / "index.html").read_text()


def test_nada_gravado_fora_do_contrato(tmp_path):
    out = tmp_path / "public"
    bad = {"schema_version": 1, "generated_at": NOW, "repos": [], "items": [{"repo": "o/r"}]}
    with pytest.raises(store.ContractError):
        write(out, bad, {"schema_version": 1, "generated_at": NOW, "evaluations": []})
    assert not out.exists()


def test_cli_resumo(tmp_path, capsys):
    import yaml
    cfg = tmp_path / "repos.yaml"
    cfg.write_text(yaml.safe_dump(CFG))
    data = tmp_path / "data"
    folder = store.repo_dir(data, "o/r")
    store.write_issues(folder / "issues.jsonl", issues_of(rec(1), rec(2)))
    (folder / "predictions.jsonl").write_text(json.dumps(pred(1)) + "\n")
    code = main(["--config", str(cfg), "--data-dir", str(data), "--out", str(tmp_path / "public")])
    err = capsys.readouterr().err
    assert code == 0 and "o/r: 1 na fila (1 abertas ainda sem previsão do Jev)" in err


def test_issue_que_saiu_do_repositorio_nao_entra_na_fila():
    gone = {**rec(1), "gone_at": "2026-11-23T00:00:00Z"}
    items, missing = build_items("o/r", issues_of(gone, rec(2)), [pred(1), pred(2)])
    assert [i["number"] for i in items] == [2] and missing == 0
