import pytest

from evaluator import jev
from evaluator.questions import QUESTIONS

from .fakes import MODEL, JevSession, jev_answers


def test_chamada_a_envia_as_cinco_perguntas_e_normaliza():
    s = JevSession()
    answers, prov = jev.ask(s, MODEL, "texto", base="https://x")
    url, body = s.calls[0]
    assert url == "https://x/v1/systemone"
    assert body["model"] == MODEL and body["state"] == "texto" and body["questions"] == QUESTIONS
    assert answers == {"is_defect": 0.9, "actionable": 0.8, "enough_info": 0.7, "usage_question": 0.1,
                       "severity": {"probs": [0.1, 0.2, 0.6, 0.1], "level": "high"}}
    assert prov["call"] == "A" and prov["served_by"] == MODEL and prov["request_id"] == "req_1"
    assert prov["tokens"] == 320 and prov["latency_ms"] >= 0


def test_repete_em_limite_e_sobrecarga():
    ok = (200, {"model": MODEL, "answers": jev_answers()}, {})
    s = JevSession(responses=[(429, {}, {"retry-after": "1"}), (529, {}, {}), ok])
    waits = []
    answers, prov = jev.ask(s, MODEL, "t", base="https://x", sleep=waits.append)
    assert len(s.calls) == 3 and waits == [1.0, 2]
    assert prov["tokens"] is None and prov["request_id"] is None


def test_resposta_em_formato_inesperado_vira_erro_claro():
    bad = jev_answers()
    del bad["severity"]
    s = JevSession(responses=[(200, {"model": MODEL, "answers": bad}, {})])
    with pytest.raises(jev.JevError, match="severity"):
        jev.ask(s, MODEL, "t", base="https://x")


def test_erro_de_autenticacao():
    s = JevSession(responses=[(401, {}, {})])
    with pytest.raises(jev.JevError, match="TYPESAFE_API_KEY"):
        jev.ask(s, MODEL, "t", base="https://x")


@pytest.mark.parametrize("model", ["jev-latest", "jev-1.14", "", None])
def test_recusa_modelo_sem_versao_explicita(model):
    with pytest.raises(jev.JevError, match="explícita"):
        jev.check_model(model)


def test_sessao_sem_chave(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    with pytest.raises(jev.JevError, match="TYPESAFE_API_KEY"):
        jev.session()
