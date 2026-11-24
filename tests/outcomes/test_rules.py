"""Um teste por cenário do spec regras-do-gabarito."""
from outcomes.rules import RULES_VERSION, classify

AIRFLOW = {"closing_labels": {"duplicate": "duplicate", "pending-response": "needs_info", "invalid": "other"},
           "stale_bots": ["github-actions[bot]"], "stale_labels": ["stale"]}
K8S = {"closing_labels": {"triage/duplicate": "duplicate"}, "stale_bots": [], "stale_labels": ["lifecycle/rotten"]}
VSCODE = {"closing_labels": {"info-needed": "needs_info"}}


def c(cfg=AIRFLOW, *, reason="completed", labels=(), by="maintainer", pr=None):
    return classify(state_reason=reason, labels=list(labels), closed_by=by, merged_pr=pr, repo_cfg=cfg)


def test_versao():
    assert RULES_VERSION == "gab-1"


def test_bot_de_inatividade_com_label_de_motivo_fica_fora():
    assert c(reason="not_planned", labels=["pending-response"], by="github-actions[bot]") == \
        {"label": "excluded", "reason": None, "exclusion_reason": "stale_bot"}


def test_label_de_inatividade_mesmo_com_bot_que_fecha_a_pedido():
    assert c(K8S, labels=["lifecycle/rotten"], by="kubernetes-prow[bot]")["exclusion_reason"] == "stale_bot"


def test_bot_que_nao_e_de_inatividade_nao_exclui():
    assert c(K8S, reason="not_planned", labels=["triage/duplicate"], by="kubernetes-prow[bot]") == \
        {"label": "no_action", "reason": "duplicate", "exclusion_reason": None}


def test_duplicata_pelo_github():
    assert c(reason="duplicate")["reason"] == "duplicate"


def test_completed_com_label_de_motivo():
    assert c(VSCODE, labels=["info-needed"], pr=123) == \
        {"label": "no_action", "reason": "needs_info", "exclusion_reason": None}


def test_not_planned_sem_label():
    assert c(reason="not_planned") == {"label": "no_action", "reason": "other", "exclusion_reason": None}


def test_prioridade_entre_motivos():
    assert c(labels=["invalid", "duplicate"])["reason"] == "duplicate"


def test_labels_sem_diferenca_de_maiusculas():
    assert c(labels=["Duplicate"])["reason"] == "duplicate"


def test_corrigida_por_pr():
    assert c(pr=74853) == {"label": "action", "reason": None, "exclusion_reason": None}


def test_completed_sem_pr():
    assert c()["exclusion_reason"] == "completed_without_pr"


def test_sem_state_reason_com_pr_e_acao():
    assert c(reason=None, pr=1)["label"] == "action"


def test_config_sem_listas_opcionais():
    assert c({"closing_labels": {"x": "other"}}, by="github-actions[bot]", pr=1)["label"] == "action"
