"""Experimento de configurações do calibrador (sem chamar o Jev): o que melhora a previsão de "sem ação"?

    python -m experimentos.configs --data-dir ../sad-fila-data/data --out docs/resultados

Mesmos dados, rótulo, corte temporal e métricas dos baselines (baselines/). Configurações:
  1. Jev + quem escreveu (autor da equipe, de primeira vez)
  2. Jev + TF-IDF juntos (empilhamento: a nota do TF-IDF entra como mais uma variável do calibrador)
  3. calibrador por repositório × global (os 3 repositórios juntos, com o repositório como variável)
  4. Jev + sinais simples do texto (os da heurística)
e as referências Jev sozinho, TF-IDF sozinho e tudo junto.
"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from baselines import features
from baselines.data import Split, load_repo, temporal_split
from baselines.metrics import evaluate
from baselines.models import _jev_matrix, _proba, tfidf_lr

REPOS = ["microsoft/vscode", "microsoft/TypeScript", "godotengine/godot"]
FIRST_TIME = {"FIRST_TIME_CONTRIBUTOR", "FIRST_TIMER"}


def author_matrix(xs):
    return np.array([[int(not e.external), int(e.author_association in FIRST_TIME)] for e in xs], dtype=float)


def repo_matrix(xs):
    return np.array([[int(e.repo == r) for r in REPOS] for e in xs], dtype=float)


def calibrate(Xtr, ytr, Xte):
    return _proba(make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000)), Xtr, ytr, Xte)


def blocks(xs, tfidf_scores=None):
    """Blocos de variáveis disponíveis para o calibrador."""
    b = {"jev": _jev_matrix(xs), "autor": author_matrix(xs), "texto": features.matrix([e.text for e in xs]),
         "repo": repo_matrix(xs)}
    if tfidf_scores is not None:
        b["tfidf"] = np.asarray(tfidf_scores, dtype=float).reshape(-1, 1)
    return b


CONFIGS = {
    "Jev sozinho (referência)": ["jev"],
    "1. Jev + quem escreveu": ["jev", "autor"],
    "2. Jev + TF-IDF juntos": ["jev", "tfidf"],
    "4. Jev + sinais do texto": ["jev", "texto"],
    "Tudo junto (Jev + autor + texto + TF-IDF)": ["jev", "autor", "texto", "tfidf"],
}


def run_split(sp):
    ytr, yte = np.array([e.y for e in sp.train]), np.array([e.y for e in sp.test])
    tf = tfidf_lr(sp.train, sp.test)  # nota do TF-IDF: fora da amostra no treino (validação cruzada), ajustada no teste
    btr, bte = blocks(sp.train, tf.train_oof), blocks(sp.test, tf.test)
    out = {"TF-IDF sozinho (referência)": (evaluate(yte, tf.test, ytr, tf.train_oof, True), tf.test)}
    for name, keys in CONFIGS.items():
        sc = calibrate(np.hstack([btr[k] for k in keys]), ytr, np.hstack([bte[k] for k in keys]))
        out[name] = (evaluate(yte, sc.test, ytr, sc.train_oof, True), sc.test)
    return out, yte


def run(data_dir):
    splits = {r: temporal_split(load_repo(data_dir, r)) for r in REPOS}
    per_repo = {}
    for r, sp in splits.items():
        print(f"  por repositório: {r}", file=sys.stderr, flush=True)
        per_repo[r] = run_split(sp)
    print("  global (3 juntos)", file=sys.stderr, flush=True)
    pooled = Split([e for s in splits.values() for e in s.train], [e for s in splits.values() for e in s.test])
    ytr = np.array([e.y for e in pooled.train])
    tf = tfidf_lr(pooled.train, pooled.test)
    btr, bte = blocks(pooled.train, tf.train_oof), blocks(pooled.test, tf.test)
    glob = {}
    for name, keys in {"Jev sozinho (referência)": ["jev"], "Tudo junto (Jev + autor + texto + TF-IDF)":
                       ["jev", "autor", "texto", "tfidf"]}.items():
        ks = keys + ["repo"]
        sc = calibrate(np.hstack([btr[k] for k in ks]), ytr, np.hstack([bte[k] for k in ks]))
        glob[name] = sc
    # avalia o global em cada repositório, com o mesmo corte escolhido no treino global
    glob_eval = {}
    for r in REPOS:
        mask_te = np.array([e.repo == r for e in pooled.test])
        mask_tr = np.array([e.repo == r for e in pooled.train])
        yte = np.array([e.y for e in pooled.test])[mask_te]
        for name, sc in glob.items():
            glob_eval[(r, name)] = evaluate(yte, sc.test[mask_te], ytr[mask_tr], sc.train_oof[mask_tr], True)
    # recorte só autores de fora, por repositório, para as configurações por repositório
    external = {}
    for r, sp in splits.items():
        res, yte = per_repo[r]
        ext = np.array([e.external for e in sp.test])
        if ext.sum() >= 20 and 0 < yte[ext].mean() < 1:
            for name, (_, scores) in res.items():
                external[(r, name)] = float(roc_auc_score(yte[ext], scores[ext]))
    return per_repo, glob_eval, external


def _row(name, r):
    b = "—" if r["brier"] is None else f"{r['brier']:.3f}"
    return f"| {name} | {r['auc']:.3f} [{r['auc_ci'][0]:.3f}–{r['auc_ci'][1]:.3f}] | {r['average_precision']:.3f} | {b} |"


def report(per_repo, glob_eval, external, generated_at):
    order = ["Jev sozinho (referência)", "TF-IDF sozinho (referência)", "1. Jev + quem escreveu",
             "2. Jev + TF-IDF juntos", "4. Jev + sinais do texto", "Tudo junto (Jev + autor + texto + TF-IDF)"]
    L = [f"# Experimento: configurações do calibrador ({generated_at[:10]})", "",
         "Gerado por `python -m experimentos.configs`, sem chamar o Jev. Mesmos dados (backfill `q1`, gabarito `gab-1`), "
         "rótulo (positivo = sem ação), corte temporal por repositório (70% mais antigas = treino) e métricas dos baselines. "
         "Todo calibrador é uma regressão logística padronizada; a nota do TF-IDF entra como variável (empilhamento), "
         "calculada fora da amostra no treino.", ""]
    for r in REPOS:
        res, yte = per_repo[r]
        L += [f"## {r}", "", f"Teste: {len(yte)} issues, sem ação: {100 * yte.mean():.0f}%.", "",
              "| Configuração (calibrador por repositório) | AUC [IC 95%] | Precisão média | Brier |", "|---|---|---|---|"]
        L += [_row(n, res[n][0]) for n in order]
        ext = [f"{n.split(' (')[0]} {external[(r, n)]:.3f}" for n in order if (r, n) in external]
        if ext:
            L += ["", "AUC só com autores de fora da equipe: " + " · ".join(ext) + "."]
        L += ["", "**3. Por repositório × global** (global = um calibrador para os 3, com o repositório como variável):", "",
              "| Configuração | Por repositório | Global |", "|---|---|---|"]
        for n in ["Jev sozinho (referência)", "Tudo junto (Jev + autor + texto + TF-IDF)"]:
            L.append(f"| {n} | {res[n][0]['auc']:.3f} | {glob_eval[(r, n)]['auc']:.3f} |")
        L.append("")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m experimentos.configs")
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out", default="docs/resultados")
    args = ap.parse_args(argv)
    per_repo, glob_eval, external = run(args.data_dir)
    now = datetime.now(timezone.utc)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"experimento-configs-{now:%Y-%m-%d}.md"
    path.write_text(report(per_repo, glob_eval, external, now.strftime("%Y-%m-%dT%H:%M:%SZ")), encoding="utf-8")
    print(f"relatório em {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
