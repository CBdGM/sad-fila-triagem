import json
from datetime import datetime, timezone

import pytest

from collector import github, store
from collector.collect import body_hash, collect_repo, months_ago, to_record

from .conftest import API, FakeResponse, FakeSession, issue, paged, params_of

NOW = datetime(2026, 11, 21, 6, 0, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 11, 22, 6, 0, 0, tzinfo=timezone.utc)


class Repo:
    """Repositório falso: issues abertas/fechadas, PRs e o que o `since` devolve."""

    def __init__(self, open_items=(), closed_items=(), updated=()):
        self.open, self.closed, self.updated = list(open_items), list(closed_items), list(updated)
        self.fail_on_page = None

    def __call__(self, url, params):
        p = params_of(url, params)
        if url == f"{API}/repos/o/r":
            return FakeResponse(body={"full_name": "o/r"})
        if self.fail_on_page and int(p.get("page", 1)) == self.fail_on_page:
            return FakeResponse(400)
        items = {"open": self.open, "closed": self.closed, "all": self.updated}[p["state"]]
        return paged(items, url.split("?")[0], p, page_size=2)


def run(tmp_path, repo, cfg, now=NOW):
    return collect_repo(FakeSession(repo), "o/r", cfg, tmp_path, now=now, done_at=lambda: now,
                        sleep=lambda s: None)


def issues_file(tmp_path):
    return store.read_issues(tmp_path / "o__r" / "issues.jsonl")


def test_registro_segue_o_contrato_e_hash_ignora_comentarios():
    a = to_record("o/r", issue(1, comments=0), "2026-11-02T00:00:00Z")
    b = to_record("o/r", issue(1, comments=7, labels=["x"]), "2026-11-02T00:00:00Z")
    store.validate("issue", a)
    assert a["body_sha256"] == b["body_sha256"] == body_hash("Issue 1", "corpo")
    assert body_hash("t", None) == body_hash("t", "")


def test_months_ago_ajusta_fim_de_mes():
    assert months_ago(datetime(2026, 3, 31), 1) == datetime(2026, 2, 28)
    assert months_ago(datetime(2026, 1, 15), 6) == datetime(2025, 7, 15)


def test_primeira_execucao_respeita_tetos_e_descarta_prs(tmp_path, cfg):
    repo = Repo(
        open_items=[issue(10, pr=True), issue(9), issue(8, pr=True), issue(7), issue(6)],
        closed_items=[
            issue(5, state="closed", closed="2026-11-10T00:00:00Z", reason="completed"),
            issue(4, state="closed", closed="2026-11-09T00:00:00Z", pr=True),
            issue(3, state="closed", closed="2026-10-01T00:00:00Z", updated="2026-11-05T00:00:00Z"),
        ])
    ch = run(tmp_path, repo, cfg)
    data = issues_file(tmp_path)
    assert sorted(data) == [5, 7, 9]           # 2 abertas (teto), 1 fechada na janela, sem PRs
    assert ch.as_dict() == {"new": [5, 7, 9], "edited": [], "closed": [5]}
    assert data[9]["first_seen_at"] == "2026-11-21T06:00:00Z"
    state = store.read_state(tmp_path / "o__r" / "state.json")
    assert state["cursor_since"] == "2026-11-21T06:00:00Z"
    assert state["versions"]["model"] == "jev-1.14.0"


def test_incremental_nova_editada_comentada_e_fechada(tmp_path, cfg):
    run(tmp_path, Repo(open_items=[issue(2), issue(1)]), cfg)
    later = Repo(updated=[
        issue(1, body="corpo editado", updated="2026-11-21T10:00:00Z"),
        issue(2, comments=5, labels=["kind:bug"], updated="2026-11-21T11:00:00Z"),
        issue(3, created="2026-11-21T12:00:00Z"),
        issue(4, pr=True),
    ])
    ch = run(tmp_path, later, cfg, now=LATER)
    assert ch.as_dict() == {"new": [3], "edited": [1], "closed": []}
    data = issues_file(tmp_path)
    assert data[2]["labels"] == ["kind:bug"]
    assert data[2]["first_seen_at"] == "2026-11-21T06:00:00Z"   # preservado
    assert data[3]["first_seen_at"] == "2026-11-22T06:00:00Z"
    assert 4 not in data

    closing = Repo(updated=[issue(2, state="closed", closed="2026-11-22T09:00:00Z",
                                  reason="not_planned", updated="2026-11-22T09:00:00Z")])
    ch = run(tmp_path, closing, cfg, now=datetime(2026, 11, 23, 6, tzinfo=timezone.utc))
    assert ch.closed == [2]
    assert issues_file(tmp_path)[2]["state_reason"] == "not_planned"


def test_incremental_usa_o_cursor(tmp_path, cfg):
    run(tmp_path, Repo(open_items=[issue(1)]), cfg)
    s = FakeSession(Repo())
    collect_repo(s, "o/r", cfg, tmp_path, now=LATER, done_at=lambda: LATER)
    listing = [p for url, p in s.calls if url.endswith("/issues")]
    assert listing[0]["since"] == "2026-11-21T06:00:00Z"
    assert listing[0]["state"] == "all"


def test_falha_no_meio_nao_grava_nada(tmp_path, cfg):
    run(tmp_path, Repo(open_items=[issue(1)]), cfg)
    folder = tmp_path / "o__r"
    before = {f: (folder / f).read_text() for f in ("issues.jsonl", "state.json")}
    broken = Repo(updated=[issue(n) for n in range(2, 8)])
    broken.fail_on_page = 2
    with pytest.raises(github.GitHubError):
        run(tmp_path, broken, cfg, now=LATER)
    assert {f: (folder / f).read_text() for f in before} == before


def test_duas_execucoes_seguidas_nao_duplicam(tmp_path, cfg):
    first = Repo(open_items=[issue(2), issue(1)])
    run(tmp_path, first, cfg)
    snapshot = (tmp_path / "o__r" / "issues.jsonl").read_text()
    again = Repo(updated=[issue(2), issue(1)])  # since é inclusivo: as mesmas voltam
    ch = run(tmp_path, again, cfg, now=LATER)
    assert ch.as_dict() == {"new": [], "edited": [], "closed": []}
    assert (tmp_path / "o__r" / "issues.jsonl").read_text() == snapshot


def test_repositorio_renomeado_nao_grava(tmp_path, cfg):
    s = FakeSession(lambda url, params: FakeResponse(body={"full_name": "novo/nome"}))
    with pytest.raises(github.RepoRenamed):
        collect_repo(s, "o/r", cfg, tmp_path, now=NOW)
    assert not (tmp_path / "o__r").exists()


def test_arquivos_gerados_passam_nos_contratos(tmp_path, cfg):
    run(tmp_path, Repo(open_items=[issue(1, labels=["duplicate"])],
                       closed_items=[issue(2, state="closed", closed="2026-11-20T00:00:00Z",
                                           reason="duplicate")]), cfg)
    folder = tmp_path / "o__r"
    for line in (folder / "issues.jsonl").read_text().splitlines():
        store.validate("issue", json.loads(line))
    store.validate("state", json.loads((folder / "state.json").read_text()))


def test_progresso_mostra_andamento_e_fim(tmp_path, cfg):
    from collector.collect import Progress
    msgs = []
    repo = Repo(open_items=[issue(n) for n in range(10, 0, -1)])  # 5 páginas de 2
    cfg["first_run"]["open_max"] = 10
    collect_repo(FakeSession(repo), "o/r", cfg, tmp_path, now=NOW, done_at=lambda: NOW,
                 progress=Progress(msgs.append, every=2))
    assert "abertas: 2/10 issues, 2 páginas" in msgs       # a cada 2 páginas
    assert "abertas: 10/10 issues, 5 páginas (fim)" in msgs
    assert any(m.startswith("fechadas desde 2026-10-21") and m.endswith("(fim)") for m in msgs)
