import json
from datetime import datetime, timezone

import pytest

from collector import github, store
from collector.collect import to_record
from outcomes.run import collect_outcomes, pending, phase0_summary

from ..collector.conftest import FakeResponse, issue

NOW = datetime(2026, 11, 21, 7, 0, tzinfo=timezone.utc)
CFG = {"repo": "o/r", "closing_labels": {"duplicate": "duplicate"}, "stale_bots": ["stale[bot]"]}


def closed_issue(n, *, closed="2026-11-10T00:00:00Z", reason="completed", labels=()):
    return to_record("o/r", issue(n, state="closed", closed=closed, reason=reason, labels=labels),
                     "2026-11-11T00:00:00Z")


def write_issues(tmp_path, records):
    store.write_issues(tmp_path / "o__r" / "issues.jsonl", {r["number"]: r for r in records})


class GraphSession:
    """Responde ao GraphQL: cada issue fechada por 'dev' com PR mesclado igual ao número + 1000,
    exceto as de `bot` (fechadas por stale[bot]) e as de `fail_on_call`."""

    def __init__(self, bot=(), fail_on_call=None):
        self.bot, self.fail_on_call, self.calls, self.headers = set(bot), fail_on_call, 0, {}

    def post(self, url, json=None, timeout=None):
        self.calls += 1
        if self.calls == self.fail_on_call:
            return FakeResponse(400)
        nums = [int(line.split(":")[0].strip()[1:]) for line in json["query"].splitlines()
                if line.strip().startswith("i") and "issue(number" in line]
        repo = {}
        for n in nums:
            if n in self.bot:
                ev = [{"__typename": "ClosedEvent", "actor": {"__typename": "Bot", "login": "stale"}, "closer": None}]
            else:
                ev = [{"__typename": "ClosedEvent", "actor": {"__typename": "User", "login": "dev"},
                       "closer": {"__typename": "PullRequest", "number": n + 1000, "merged": True,
                                  "repository": {"nameWithOwner": "o/r"}}}]
            repo[f"i{n}"] = {"timelineItems": {"nodes": ev}}
        return FakeResponse(body={"data": {"repository": repo}})


def outcomes_of(tmp_path):
    return store.read_jsonl(tmp_path / "o__r" / "outcomes.jsonl")


def test_pendentes_por_numero_e_data_de_fechamento():
    a, b = closed_issue(1), closed_issue(2)
    issues = {1: a, 2: b, 3: to_record("o/r", issue(3), "2026-11-11T00:00:00Z")}
    done = [{"number": 1, "closed_at": a["closed_at"]}]
    assert [i["number"] for i in pending(issues, done)] == [2]
    reclosed = closed_issue(1, closed="2026-11-15T00:00:00Z")  # reaberta e fechada de novo
    assert [i["number"] for i in pending({1: reclosed}, done)] == [1]


def test_grava_desfechos_validos_e_classificados(tmp_path):
    write_issues(tmp_path, [closed_issue(1), closed_issue(2, reason="not_planned"), closed_issue(3)])
    res = collect_outcomes(GraphSession(bot=[3]), "o/r", CFG, tmp_path, now=NOW)
    assert res["added"] == 3
    rows = {o["number"]: o for o in outcomes_of(tmp_path)}
    assert (rows[1]["label"], rows[1]["merged_pr"]) == ("action", 1001)
    assert (rows[2]["label"], rows[2]["reason"]) == ("no_action", "other")
    assert (rows[3]["label"], rows[3]["closed_by"], rows[3]["exclusion_reason"]) == \
        ("excluded", "stale[bot]", "stale_bot")
    for o in rows.values():
        store.validate("outcome", o)
        assert o["rules_version"] == "gab-1" and o["recorded_at"] == "2026-11-21T07:00:00Z"


def test_falha_no_meio_mantem_lotes_anteriores(tmp_path):
    write_issues(tmp_path, [closed_issue(n) for n in range(1, 8)])
    with pytest.raises(github.GitHubError):
        collect_outcomes(GraphSession(fail_on_call=3), "o/r", CFG, tmp_path, batch_size=2,
                         now=NOW, sleep=lambda s: None)
    assert sorted(o["number"] for o in outcomes_of(tmp_path)) == [1, 2, 3, 4]  # 2 lotes salvos
    res = collect_outcomes(GraphSession(), "o/r", CFG, tmp_path, batch_size=2, now=NOW)
    assert res["added"] == 3
    assert sorted(o["number"] for o in outcomes_of(tmp_path)) == list(range(1, 8))


def test_teto_por_execucao(tmp_path):
    write_issues(tmp_path, [closed_issue(n) for n in range(1, 6)])
    res = collect_outcomes(GraphSession(), "o/r", CFG, tmp_path, max_items=2, now=NOW)
    assert (res["added"], res["pending_left"]) == (2, 3)


def test_duas_execucoes_nao_repetem(tmp_path):
    write_issues(tmp_path, [closed_issue(1), closed_issue(2)])
    collect_outcomes(GraphSession(), "o/r", CFG, tmp_path, now=NOW)
    before = (tmp_path / "o__r" / "outcomes.jsonl").read_text()
    s = GraphSession()
    assert collect_outcomes(s, "o/r", CFG, tmp_path, now=NOW)["added"] == 0
    assert s.calls == 0
    assert (tmp_path / "o__r" / "outcomes.jsonl").read_text() == before


def test_linhas_antigas_ficam_identicas(tmp_path):
    write_issues(tmp_path, [closed_issue(1)])
    collect_outcomes(GraphSession(), "o/r", CFG, tmp_path, now=NOW)
    first = (tmp_path / "o__r" / "outcomes.jsonl").read_text()
    write_issues(tmp_path, [closed_issue(1), closed_issue(2)])
    collect_outcomes(GraphSession(), "o/r", CFG, tmp_path, now=NOW)
    assert (tmp_path / "o__r" / "outcomes.jsonl").read_text().startswith(first)


def test_sem_issues_jsonl_pede_o_coletor(tmp_path):
    with pytest.raises(FileNotFoundError, match="coletor"):
        collect_outcomes(GraphSession(), "o/r", CFG, tmp_path)


def test_resumo_da_fase_0():
    rows = [{"label": "no_action", "reason": "duplicate", "exclusion_reason": None}] * 3 + \
           [{"label": "action", "reason": None, "exclusion_reason": None}] * 7 + \
           [{"label": "excluded", "reason": None, "exclusion_reason": "stale_bot"}] * 5
    s = phase0_summary(rows)
    assert (s["no_action"], s["action"], s["excluded"]) == (3, 7, 5)
    assert s["pct_no_action"] == 30.0
    assert s["reasons"] == {"duplicate": 3} and s["exclusions"] == {"stale_bot": 5}
