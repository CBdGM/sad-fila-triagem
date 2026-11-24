"""Extração dos fatos a partir de respostas GraphQL (formato real do apache/airflow, 21/11/2026)."""
import pytest

from collector import github
from outcomes import fetch

from ..collector.conftest import FakeResponse

REPO = "apache/airflow"


def pr(number, merged=True, repo=REPO):
    return {"__typename": "PullRequest", "number": number, "merged": merged,
            "repository": {"nameWithOwner": repo}}


def closed(login, typename="User", closer=None):
    return {"__typename": "ClosedEvent", "actor": {"__typename": typename, "login": login}, "closer": closer}


def xref(source):
    return {"__typename": "CrossReferencedEvent", "source": source}


def node(*events):
    return {"timelineItems": {"nodes": list(events)}}


def test_fechada_pelo_pr():  # issue 74851
    f = fetch.extract(REPO, node(xref(pr(74853)), closed("potiuk", closer=pr(74853))))
    assert f == {"closed_by": "potiuk", "closed_by_bot": False, "merged_pr": 74853, "truncated": False}


def test_fechada_por_bot_normaliza_login():  # issue 69173
    f = fetch.extract(REPO, node(closed("github-actions", typename="Bot")))
    assert (f["closed_by"], f["closed_by_bot"], f["merged_pr"]) == ("github-actions[bot]", True, None)


def test_fechada_a_mao_com_pr_nao_mesclado():  # issue 77360
    f = fetch.extract(REPO, node(xref(pr(77361, merged=False)), closed("wayblink")))
    assert f["merged_pr"] is None


def test_pr_de_outro_repositorio_nao_conta():
    f = fetch.extract(REPO, node(xref(pr(5, repo="other/repo")), closed("x")))
    assert f["merged_pr"] is None


def test_sem_closer_usa_pr_mesclado_que_referencia():
    f = fetch.extract(REPO, node(xref(pr(9, merged=False)), xref(pr(10)), closed("x")))
    assert f["merged_pr"] == 10


def test_ultimo_fechamento_vale_quando_reaberta():
    f = fetch.extract(REPO, node(closed("bot", typename="Bot"), closed("human")))
    assert (f["closed_by"], f["closed_by_bot"]) == ("human", False)


def test_ator_apagado():
    f = fetch.extract(REPO, {"timelineItems": {"nodes": [{"__typename": "ClosedEvent", "actor": None,
                                                           "closer": None}]}})
    assert (f["closed_by"], f["closed_by_bot"]) == (None, False)


def test_eventos_cortados_sao_sinalizados():
    events = [xref(pr(n, merged=False)) for n in range(fetch.EVENTS_PER_ISSUE)]
    assert fetch.extract(REPO, node(*events))["truncated"] is True


def test_consulta_tem_um_alias_por_issue():
    q = fetch.build_query([1, 22])
    assert "i1: issue(number: 1)" in q and "i22: issue(number: 22)" in q and "fragment Closing" in q


class PostSession:
    def __init__(self, *bodies):
        self.bodies, self.headers, self.sent = list(bodies), {}, []

    def post(self, url, json=None, timeout=None):
        self.sent.append(json)
        return FakeResponse(body=self.bodies.pop(0))


def test_fetch_batch_issue_apagada_vem_none():
    s = PostSession({"data": {"repository": {"i1": node(closed("a")), "i2": None}},
                     "errors": [{"type": "NOT_FOUND", "message": "x"}]})
    out = fetch.fetch_batch(s, REPO, [1, 2])
    assert out[1]["closed_by"] == "a" and out[2] is None
    assert s.sent[0]["variables"] == {"owner": "apache", "name": "airflow"}


def test_graphql_erro_que_nao_e_not_found_falha():
    s = PostSession({"data": None, "errors": [{"type": "FORBIDDEN", "message": "Resource not accessible"}]})
    with pytest.raises(github.GitHubError, match="Resource not accessible"):
        github.graphql(s, "q")


def test_graphql_limite_espera_e_repete():
    slept = []
    s = PostSession({"errors": [{"type": "RATE_LIMITED", "message": "limit"}]}, {"data": {"ok": 1}})
    assert github.graphql(s, "q", sleep=slept.append) == {"ok": 1}
    assert slept == [60]
