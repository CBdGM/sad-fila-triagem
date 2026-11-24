import pytest

from collector import github

from .conftest import API, FakeResponse, FakeSession


def seq(*responses):
    it = iter(responses)
    return FakeSession(lambda url, params: next(it))


def test_limite_secundario_espera_retry_after(nosleep):
    slept, sleep = nosleep
    s = seq(FakeResponse(429, headers={"Retry-After": "60"}), FakeResponse(200, body={"ok": 1}))
    assert github.get(s, f"{API}/x", sleep=sleep).json() == {"ok": 1}
    assert slept == [60]


def test_limite_primario_espera_o_reset(nosleep):
    slept, sleep = nosleep
    s = seq(FakeResponse(403, headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1100"}),
            FakeResponse(200, body={}))
    github.get(s, f"{API}/x", sleep=sleep, clock=lambda: 1000)
    assert slept == [101]


def test_erro_5xx_repete_com_espera_crescente(nosleep):
    slept, sleep = nosleep
    s = seq(FakeResponse(502), FakeResponse(502), FakeResponse(200, body=[]))
    github.get(s, f"{API}/x", sleep=sleep)
    assert slept == [1, 2]


def test_5xx_persistente_falha(nosleep):
    _, sleep = nosleep
    s = FakeSession(lambda url, params: FakeResponse(503))
    with pytest.raises(github.GitHubError, match="503"):
        github.get(s, f"{API}/x", sleep=sleep)


def test_token_nunca_aparece_no_erro(nosleep):
    _, sleep = nosleep
    s = seq(FakeResponse(401))
    s.headers["Authorization"] = "Bearer SEGREDO123"
    with pytest.raises(github.GitHubError) as e:
        github.get(s, f"{API}/x", sleep=sleep)
    assert "SEGREDO123" not in str(e.value)
    assert "autenticação" in str(e.value)


def test_403_sem_limite_nao_espera(nosleep):
    slept, sleep = nosleep
    s = seq(FakeResponse(403))
    with pytest.raises(github.GitHubError, match="403"):
        github.get(s, f"{API}/x", sleep=sleep)
    assert slept == []


def test_paginacao_segue_link_next():
    pages = {
        f"{API}/items": FakeResponse(body=[1, 2], next_url=f"{API}/items?page=2"),
        f"{API}/items?page=2": FakeResponse(body=[3], next_url=f"{API}/items?page=3"),
        f"{API}/items?page=3": FakeResponse(body=[4]),
    }
    s = FakeSession(lambda url, params: pages[url])
    assert list(github.paginate(s, f"{API}/items", {"per_page": 2})) == [1, 2, 3, 4]
    assert s.calls[1] == (f"{API}/items?page=2", {})  # páginas seguintes usam só a URL do Link


def test_paginacao_respeita_teto():
    s = FakeSession(lambda url, params: FakeResponse(body=[1], next_url=f"{API}/items?mais"))
    with pytest.raises(github.GitHubError, match="3 páginas"):
        list(github.paginate(s, f"{API}/items", max_pages=3))


def test_repositorio_renomeado_mostra_nome_novo():
    s = seq(FakeResponse(body={"full_name": "react/react"}))
    with pytest.raises(github.RepoRenamed, match="react/react"):
        github.check_repo_name(s, "facebook/react")


def test_mesmo_nome_com_maiusculas_diferentes_passa():
    s = seq(FakeResponse(body={"full_name": "Apache/Airflow"}))
    assert github.check_repo_name(s, "apache/airflow") == "Apache/Airflow"


def test_conta_requisicoes_e_guarda_o_limite_restante(nosleep):
    _, sleep = nosleep
    s = seq(FakeResponse(429, headers={"Retry-After": "1"}),
            FakeResponse(200, body=[], headers={"X-RateLimit-Remaining": "4321", "X-RateLimit-Limit": "5000"}))
    github.get(s, f"{API}/x", sleep=sleep)
    u = github.usage(s)
    assert (u.requests, u.remaining, u.limit) == (2, 4321, 5000)


def test_on_page_recebe_o_numero_da_pagina():
    pages = {f"{API}/i": FakeResponse(body=[1], next_url=f"{API}/i?p=2"), f"{API}/i?p=2": FakeResponse(body=[2])}
    seen = []
    list(github.paginate(FakeSession(lambda url, params: pages[url]), f"{API}/i", on_page=seen.append))
    assert seen == [1, 2]
