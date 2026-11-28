"""Métricas: AUC com IC por bootstrap, precisão média, Brier e corte por precisão-alvo escolhido no treino."""
import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

TARGET_PRECISION = 0.90
MIN_FLAGGED = 10       # o corte precisa marcar ao menos isto no treino, para a precisão não vir de 2 ou 3 casos
BOOTSTRAP = 1000
SEED = 42


def auc_ci(y, s, n=BOOTSTRAP, seed=SEED):
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n):
        idx = rng.integers(0, len(y), len(y))
        if y[idx].min() == y[idx].max():
            continue
        vals.append(roc_auc_score(y[idx], s[idx]))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def threshold_for_precision(y, s, target=TARGET_PRECISION, min_flagged=MIN_FLAGGED):
    """Menor corte t com precisão(s >= t) >= alvo e pelo menos min_flagged marcados; None se não existe."""
    order = np.argsort(-s, kind="stable")
    ys, ss = y[order], s[order]
    tp = np.cumsum(ys)
    k = np.arange(1, len(ys) + 1)
    best = None
    for i in range(len(ss)):
        if i + 1 < len(ss) and ss[i + 1] == ss[i]:
            continue  # avalia só no último de um grupo de empates (o corte inclui todos os iguais)
        if k[i] >= min_flagged and tp[i] / k[i] >= target:
            best = ss[i]
    return None if best is None else float(best)


def evaluate(y_test, s_test, y_train, s_train_oof, probability):
    y_test, s_test = np.asarray(y_test), np.asarray(s_test, dtype=float)
    lo, hi = auc_ci(y_test, s_test)
    out = {"n": int(len(y_test)), "base_rate": float(y_test.mean()),
           "auc": float(roc_auc_score(y_test, s_test)), "auc_ci": [lo, hi],
           "average_precision": float(average_precision_score(y_test, s_test)),
           "brier": float(brier_score_loss(y_test, s_test)) if probability else None,
           "threshold": None, "precision_no_action": None, "recall_no_action": None, "coverage": None}
    t = threshold_for_precision(np.asarray(y_train), np.asarray(s_train_oof, dtype=float))
    if t is not None:
        flagged = s_test >= t
        out.update(threshold=t, coverage=float(flagged.mean()),
                   recall_no_action=float((flagged & (y_test == 1)).sum() / max(1, (y_test == 1).sum())),
                   precision_no_action=float((y_test[flagged] == 1).mean()) if flagged.any() else None)
    return out
