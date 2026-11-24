import json

import pytest

from collector import store

from .conftest import issue
from collector.collect import to_record


def rec(n):
    return to_record("o/r", issue(n), "2026-11-02T00:00:00Z")


def test_grava_e_le_issues(tmp_path):
    path = tmp_path / "o__r" / "issues.jsonl"
    store.write_issues(path, {2: rec(2), 1: rec(1)})
    lines = path.read_text().splitlines()
    assert [json.loads(line)["number"] for line in lines] == [1, 2]  # ordenado
    assert set(store.read_issues(path)) == {1, 2}


def test_linha_invalida_nao_substitui_o_arquivo(tmp_path):
    path = tmp_path / "issues.jsonl"
    store.write_issues(path, {1: rec(1)})
    before = path.read_text()
    bad = rec(2) | {"state": "talvez"}
    with pytest.raises(store.ContractError, match="issue #2"):
        store.write_issues(path, {1: rec(1), 2: bad})
    assert path.read_text() == before
    assert not list(tmp_path.glob(".*tmp"))  # temporário removido


def test_state_invalido_nao_grava(tmp_path):
    path = tmp_path / "state.json"
    with pytest.raises(store.ContractError):
        store.write_state(path, {"schema_version": 1, "repo": "o/r"})
    assert not path.exists()


def test_le_os_exemplos_dos_contratos():
    ex = store.CONTRACTS / "examples"
    assert len(store.read_issues(ex / "issues.jsonl")) == 3
    assert store.read_state(ex / "state.json")["repo"] == "apache/airflow"
    assert store.load_config(ex / "repos.yaml")["first_run"]["open_max"] == 500


def test_repo_dir():
    assert store.repo_dir("data", "apache/airflow").as_posix() == "data/apache__airflow"


def test_jsonl_com_separador_unicode_dentro_do_texto(tmp_path):
    # U+2028, U+0085 e \x0c ficam crus no json.dumps(ensure_ascii=False); não podem quebrar a linha
    rows = [{"n": 1, "texto": "a b\u0085c\x0cd"}, {"n": 2, "texto": "ok"}]
    path = tmp_path / "x.jsonl"
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    assert store.read_jsonl(path) == rows
    issues = tmp_path / "issues.jsonl"
    issues.write_text(json.dumps({"number": 7, "title": "x y"}, ensure_ascii=False) + "\n", encoding="utf-8")
    assert store.read_issues(issues)[7]["title"] == "x y"
