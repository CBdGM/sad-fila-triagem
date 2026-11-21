"""Regras do gabarito: como um fechamento vira no_action, action ou excluded.

Funções puras (sem rede nem arquivo). Para mudar as regras, crie uma versão nova (ex.: gab-2) e
troque RULES_VERSION: cada desfecho grava a versão usada.

gab-1 (proposta SAD v3), nesta ordem:
  1. Inatividade → excluded/stale_bot: quem fechou está em stale_bots ou a issue tem label de
     stale_labels. Vem antes de tudo: gab-1 exclui todo fechamento por inatividade.
  2. Sem ação → no_action: state_reason not_planned ou duplicate, ou label de closing_labels.
  3. Com ação → action se houver PR mesclado ligado; senão excluded/completed_without_pr.
"""

RULES_VERSION = "gab-1"
REASON_PRIORITY = ("duplicate", "needs_info", "usage_question", "out_of_scope", "other")


def _norm(names):
    return {n.lower() for n in names or ()}


def classify(*, state_reason, labels, closed_by, merged_pr, repo_cfg):
    """Devolve {"label", "reason", "exclusion_reason"} para um fechamento."""
    labels_lc = _norm(labels)

    stale_bots = _norm(repo_cfg.get("stale_bots"))
    stale_labels = _norm(repo_cfg.get("stale_labels"))
    if (closed_by and closed_by.lower() in stale_bots) or labels_lc & stale_labels:
        return {"label": "excluded", "reason": None, "exclusion_reason": "stale_bot"}

    mapped = {motive for label, motive in (repo_cfg.get("closing_labels") or {}).items()
              if label.lower() in labels_lc}
    if mapped or state_reason in ("not_planned", "duplicate"):
        if not mapped:
            mapped = {"duplicate" if state_reason == "duplicate" else "other"}
        reason = next(r for r in REASON_PRIORITY if r in mapped)
        return {"label": "no_action", "reason": reason, "exclusion_reason": None}

    if merged_pr:
        return {"label": "action", "reason": None, "exclusion_reason": None}
    return {"label": "excluded", "reason": None, "exclusion_reason": "completed_without_pr"}
