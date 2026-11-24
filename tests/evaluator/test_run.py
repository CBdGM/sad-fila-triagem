from datetime import datetime, timezone

import pytest

from collector import store
from evaluator import jev
from evaluator.run import evaluate_repo, select

from .fakes import MODEL, GitHubSession, JevSession, outcome, rec, texts_of, write

NOW = datetime(2026, 11, 21, 7, 0, tzinfo=timezone.utc)
C = "2026-11-15T00:00:00Z"


def preds(folder):
    return store.read_jsonl(folder / "predictions.jsonl")


def run(tmp_path, gh, js, **kw):
    kw.setdefault("mode", "daily")
    return evaluate_repo(gh, js, "o/r", MODEL, tmp_path, now=NOW, ask=lambda s, m, t: jev.ask(s, m, t, base="https://x"), **kw)


def test_backfill_so_com_desfechos_que_contam():
    issues = {n: rec(n, state="closed", closed=C) for n in (1, 2, 3)}
    issues[4] = rec(4)
    outs = [outcome(1, "no_action", C), outcome(2, "action", C), outcome(3, "excluded", C)]
    assert sorted(i["number"] for i in select(issues, outs, "backfill")) == [1, 2]
    assert [i["number"] for i in select(issues, outs, "daily")] == [4]


def test_backfill_ignora_desfecho_de_fechamento_antigo():
    issues = {1: rec(1, state="closed", closed="2026-11-18T00:00:00Z")}  # reaberta e fechada de novo
    assert select(issues, [outcome(1, "action", C)], "backfill") == []


def test_grava_previsoes_validas(tmp_path):
    records = [rec(1), rec(2)]
    folder = write(tmp_path, records)
    res = run(tmp_path, GitHubSession(texts_of(records)), JevSession())
    assert res["added"] == 2 and res["tokens"] == 640
    for p in preds(folder):
        store.validate("prediction", p)
        assert p["first_seen"] is True and p["mode"] == "daily" and p["predicted_at"] == "2026-11-21T07:00:00Z"
        assert p["versions"] == {"model": MODEL, "questions": "q1", "cleaning": "clean-1"}
        assert p["answers"]["severity"]["level"] == "high" and p["input_text"].startswith("Issue ")


def test_duas_execucoes_nao_repetem(tmp_path):
    records = [rec(1)]
    write(tmp_path, records)
    run(tmp_path, GitHubSession(texts_of(records)), JevSession())
    js = JevSession()
    assert run(tmp_path, GitHubSession(texts_of(records)), js)["added"] == 0
    assert js.calls == []


def test_issue_editada_e_avaliada_de_novo_sem_first_seen(tmp_path):
    folder = write(tmp_path, [rec(1)])
    run(tmp_path, GitHubSession({1: ("Issue 1", "corpo")}), JevSession())
    write(tmp_path, [rec(1, body="corpo novo")])
    res = run(tmp_path, GitHubSession({1: ("Issue 1", "corpo novo")}), JevSession())
    assert res["added"] == 1
    assert [p["first_seen"] for p in preds(folder)] == [True, False]


def test_hash_divergente_fica_para_depois(tmp_path):
    folder = write(tmp_path, [rec(1), rec(2)])
    gh = GitHubSession({1: ("Issue 1", "editado depois da coleta"), 2: ("Issue 2", "corpo")})
    res = run(tmp_path, gh, JevSession())
    assert res["edited"] == [1] and [p["number"] for p in preds(folder)] == [2]


def test_issue_apagada_e_pulada(tmp_path):
    write(tmp_path, [rec(1), rec(2)])
    res = run(tmp_path, GitHubSession({2: ("Issue 2", "corpo")}), JevSession())
    assert res["skipped"] == [1] and res["added"] == 1


def test_falha_no_meio_mantem_o_que_foi_feito(tmp_path):
    records = [rec(n) for n in range(1, 5)]
    folder = write(tmp_path, records)
    with pytest.raises(jev.JevError):
        run(tmp_path, GitHubSession(texts_of(records)), JevSession(fail_on_call=3))
    assert len(preds(folder)) == 2
    assert run(tmp_path, GitHubSession(texts_of(records)), JevSession())["added"] == 2


def test_teto_e_mais_recentes_primeiro(tmp_path):
    records = [rec(n) for n in range(1, 11)]
    folder = write(tmp_path, records)
    res = run(tmp_path, GitHubSession(texts_of(records)), JevSession(), max_items=3)
    assert (res["added"], res["pending_left"]) == (3, 7)
    assert [p["number"] for p in preds(folder)] == [10, 9, 8]


def test_texto_cortado_no_limite(tmp_path, monkeypatch):
    monkeypatch.setattr("evaluator.run.MAX_STATE_CHARS", 20)
    big = rec(1, body="x" * 500)
    folder = write(tmp_path, [big])
    run(tmp_path, GitHubSession({1: ("Issue 1", "x" * 500)}), JevSession())
    assert len(preds(folder)[0]["input_text"]) == 20


def test_avisa_quando_servidor_responde_outra_versao(tmp_path):
    records = [rec(1)]
    write(tmp_path, records)
    res = run(tmp_path, GitHubSession(texts_of(records)), JevSession(served_by="jev-1.15.0"))
    assert res["other_model"] == ["jev-1.15.0"]


def test_recusa_jev_latest_antes_de_chamar(tmp_path):
    write(tmp_path, [rec(1)])
    js = JevSession()
    with pytest.raises(jev.JevError):
        evaluate_repo(GitHubSession({}), js, "o/r", "jev-latest", tmp_path, mode="daily")
    assert js.calls == []


def test_backfill_sem_desfechos_pede_o_passo(tmp_path):
    write(tmp_path, [rec(1)])
    with pytest.raises(FileNotFoundError, match="desfechos"):
        run(tmp_path, GitHubSession({}), JevSession(), mode="backfill")


def test_backfill_grava_modo(tmp_path):
    records = [rec(1, state="closed", closed=C)]
    folder = write(tmp_path, records, [outcome(1, "no_action", C)])
    run(tmp_path, GitHubSession(texts_of(records)), JevSession(), mode="backfill")
    assert preds(folder)[0]["mode"] == "backfill"
