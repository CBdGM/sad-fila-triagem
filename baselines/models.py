"""Modelos comparados. Cada um devolve, para o treino, pontuações fora da amostra (validação cruzada,
usadas para escolher o corte) e, para o teste, as pontuações a avaliar. Nada do teste é usado no ajuste."""
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import features

SEED = 42
FOLDS = 5
TFIDF_C = [0.1, 0.3, 1.0, 3.0, 10.0]
JEV_NOUL = ["is_defect", "actionable", "enough_info", "usage_question"]


@dataclass
class Scores:
    train_oof: np.ndarray   # pontuações do treino fora da amostra (para o corte)
    test: np.ndarray
    probability: bool       # se as pontuações são probabilidades (Brier faz sentido)
    note: str = ""


def _cv(n_pos):
    return StratifiedKFold(n_splits=min(FOLDS, max(2, n_pos)), shuffle=True, random_state=SEED)


def _proba(model, X_train, y_train, X_test):
    oof = cross_val_predict(model, X_train, y_train, cv=_cv(int(y_train.sum())), method="predict_proba")[:, 1]
    model.fit(X_train, y_train)
    return Scores(oof, model.predict_proba(X_test)[:, 1], True)


def rules(train, test):
    f = lambda xs: np.array([features.rule_score(e.text) for e in xs], dtype=float)  # noqa: E731
    return Scores(f(train), f(test), False, "sem treino")


def heuristic_lr(train, test):
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
    y = np.array([e.y for e in train])
    return _proba(model, features.matrix([e.text for e in train]), y, features.matrix([e.text for e in test]))


def tfidf_lr(train, test):
    y = np.array([e.y for e in train])
    pipe = make_pipeline(
        TfidfVectorizer(lowercase=True, strip_accents="unicode", ngram_range=(1, 2), min_df=3, max_df=0.9,
                        sublinear_tf=True, max_features=100_000),
        LogisticRegression(max_iter=4000, solver="liblinear"))
    search = GridSearchCV(pipe, {"logisticregression__C": TFIDF_C}, scoring="roc_auc", cv=_cv(int(y.sum())))
    search.fit([e.text for e in train], y)
    best = search.best_params_["logisticregression__C"]
    pipe.set_params(logisticregression__C=best)
    s = _proba(pipe, np.array([e.text for e in train], dtype=object), y, np.array([e.text for e in test], dtype=object))
    s.note = f"C={best} (validação cruzada no treino)"
    return s


def _jev_matrix(xs):
    rows = []
    for e in xs:
        a = e.answers
        expected_sev = sum(i * p for i, p in enumerate(a["severity"]["probs"]))
        rows.append([a[k] for k in JEV_NOUL] + [expected_sev])
    return np.array(rows, dtype=float)


def jev_raw(train, test):
    f = lambda xs: np.array([1 - e.answers["is_defect"] for e in xs])  # noqa: E731
    return Scores(f(train), f(test), False, "1 − is_defect, sem treino")


def jev_lr(train, test):
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
    return _proba(model, _jev_matrix(train), np.array([e.y for e in train]), _jev_matrix(test))


MODELS = {
    "heuristic-rules": ("Heurística (regras fixas)", rules),
    "heuristic-lr": ("Heurística (pesos aprendidos)", heuristic_lr),
    "tfidf-lr": ("TF-IDF + regressão logística", tfidf_lr),
    "jev-raw": ("Jev bruto (1 − é defeito)", jev_raw),
    "jev-lr": ("Jev + regressão logística (referência)", jev_lr),
}
