import json
from datetime import datetime

import yaml

from audit.__main__ import main
from audit.checks import ATENCAO, ERRO, audit
from collector import store

from ..evaluator.fakes import outcome, rec

NOW = datetime(2026, 11, 24, 12, 0)
CFG = {"schema_version": 1, "model": "jev-1.14.0", "first_run": {"open_max": 5, "closed_months": 1},
       "repos": [{"repo": "o/r", "closing_labels": {"duplicate": "duplicate"}}]}
C = "2026-11-15T00:00:00Z"


def pred(issue, first_seen=True):
    return {"schema_version": 1, "repo": "o/r", "number": issue["number"], "predicted_at": "2026-11-23T00:00:00Z",
            "mode": "daily", "first_seen": first_seen, "body_sha256": issue["body_sha256"],
            "versions": {"model": "jev-1.14.0", "questions": "q1", "cleaning": "clean-1"},
            "provenance": {"calls": [{"call": "A", "served_by": "jev-1.14.0", "request_id": None,
                                      "latency_ms": 1.0, "tokens": 10}]},
            "answers": {"is_defect": 0.5, "actionable": 0.5, "enough_info": 0.5, "usage_question": 0.1,
                        "severity": {"probs": [0.25] * 4, "level": "low"}}}


def setup(tmp_path, issues, outcomes=(), predictions=(), last="2026-11-24T06:00:00Z"):
    folder = store.repo_dir(tmp_path, "o/r")
    store.write_issues(folder / "issues.jsonl", {i["number"]: i for i in issues})
    (folder / "outcomes.jsonl").write_text("".join(json.dumps(o) + "\n" for o in outcomes))
    (folder / "predictions.jsonl").write_text("".join(json.dumps(p) + "\n" for p in predictions))
    store.write_state(folder / "state.json", {"schema_version": 1, "repo": "o/r", "cursor_since": last,
                                              "last_success_at": last,
                                              "versions": {"model": "jev-1.14.0", "questions": "q1", "cleaning": "clean-1"}})
    return folder


def levels(findings):
    return sorted((lvl, msg.split(" (")[0]) for lvl, _, msg in findings)


def healthy(tmp_path):
    a, b = rec(1), rec(2, state="closed", closed=C)
    return setup(tmp_path, [a, b], [outcome(2, "action", C)], [pred(a)])


def test_dados_integros_sem_achados(tmp_path):
    healthy(tmp_path)
    assert audit(CFG, tmp_path, NOW) == []


def test_previsao_repetida_e_first_seen_duplo(tmp_path):
    a = rec(1)
    setup(tmp_path, [a], predictions=[pred(a), pred(a)])
    assert levels(audit(CFG, tmp_path, NOW)) == [
        (ERRO, "1 issue(s) com mais de um first_seen"), (ERRO, "1 previsão(ões) repetida(s)")]


def test_desfecho_repetido_e_previsao_de_issue_desconhecida(tmp_path):
    b = rec(2, state="closed", closed=C)
    other = rec(9)
    setup(tmp_path, [b], [outcome(2, "action", C)] * 2, [pred(other)])
    assert levels(audit(CFG, tmp_path, NOW)) == [
        (ERRO, "1 desfecho(s) repetido(s)"), (ERRO, "1 previsão(ões) de issue fora do issues.jsonl")]


def test_linha_fora_do_contrato(tmp_path):
    folder = healthy(tmp_path)
    with open(folder / "outcomes.jsonl", "a") as f:
        f.write(json.dumps({"number": 3}) + "\n")
    found = audit(CFG, tmp_path, NOW)
    assert [lvl for lvl, _, _ in found] == [ERRO] and "outcomes.jsonl: 1 linha(s) fora do contrato" in found[0][2]


def test_coleta_parada(tmp_path):
    a = rec(1)
    setup(tmp_path, [a], predictions=[pred(a)], last="2026-11-21T06:00:00Z")
    assert levels(audit(CFG, tmp_path, NOW)) == [(ATENCAO, "última coleta bem-sucedida: 2026-11-21T06:00:00Z")]


def test_fechada_sem_desfecho_inclusive_reaberta(tmp_path):
    b = rec(2, state="closed", closed="2026-11-20T00:00:00Z")  # desfecho guardado é do fechamento anterior
    setup(tmp_path, [b], [outcome(2, "action", C)])
    assert levels(audit(CFG, tmp_path, NOW)) == [(ATENCAO, "1 fechada(s) sem desfecho")]


def test_aberta_sem_previsao_so_depois_do_limite(tmp_path):
    old = rec(1)                    # first_seen_at 2026-11-20 (fakes): 4 dias e 12 h antes de NOW
    setup(tmp_path, [old])
    assert levels(audit(CFG, tmp_path, NOW)) == [(ATENCAO, "1 aberta(s) vista(s) há mais de 4 dias sem previsão do Jev")]
    assert audit(CFG, tmp_path, NOW, max_days=5) == []


def test_tamanho(tmp_path):
    healthy(tmp_path)
    assert levels(audit(CFG, tmp_path, NOW, max_mb=0)) == [(ATENCAO, "pasta de dados com 0 MB")]


def test_cli_codigos_de_saida(tmp_path, capsys):
    cfg = tmp_path / "repos.yaml"
    cfg.write_text(yaml.safe_dump(CFG))
    data = tmp_path / "data"
    healthy(data)
    assert main(["--config", str(cfg), "--data-dir", str(data)], now=NOW) == 0
    assert main(["--config", str(cfg), "--data-dir", str(data), "--max-hours", "1"], now=NOW) == 1
    folder = store.repo_dir(data, "o/r")
    with open(folder / "predictions.jsonl") as f:
        line = f.readline()
    with open(folder / "predictions.jsonl", "a") as f:
        f.write(line)
    assert main(["--config", str(cfg), "--data-dir", str(data)], now=NOW) == 2
    assert "auditoria: 2 erro(s)" in capsys.readouterr().err


def test_aberta_que_saiu_do_repositorio_nao_gera_atencao(tmp_path):
    old = {**rec(1), "gone_at": "2026-11-22T00:00:00Z"}
    setup(tmp_path, [old])
    assert audit(CFG, tmp_path, NOW) == []
