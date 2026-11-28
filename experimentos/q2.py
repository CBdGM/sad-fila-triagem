"""Experimento q2: perguntas ajustadas ao Jev, comparadas com q1 e TF-IDF nas mesmas issues.

Não grava em predictions.jsonl nem muda o job. Uso:
    python -m experimentos.q2 --data-dir ../sad-fila-data/data --cache q2-cache.jsonl --out docs/resultados

Desenho:
- Amostra fixa (semente 42) das issues fechadas com desfecho no_action/action que já têm a resposta q1:
  todo o TypeScript e até 800 de Godot e de VS Code.
- Corte temporal dentro da amostra de cada repositório (70% mais antigas = treino), como nos baselines.
- Mesma regressão logística (calibrador simples) sobre as respostas q1 e sobre as q2; TF-IDF treinado
  no mesmo treino como régua. Mesmas métricas dos baselines (AUC com IC, precisão média, Brier).
"""
import argparse
import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from baselines.data import Split, load_repo, temporal_split
from baselines.metrics import evaluate
from baselines.models import Scores, _proba, tfidf_lr
from evaluator import jev

SEVERITY = ["Low: cosmetic issue or minor inconvenience, easy workaround",
            "Medium: a feature misbehaves for some users, a workaround exists",
            "High: a major feature is broken or results are wrong, no easy workaround",
            "Critical: crash, data loss, security vulnerability or outage"]

Q2 = {
    "is_defect": {"type": "noul", "instructions":
                  "Does this issue report a defect, meaning the software behaves incorrectly (a crash, an error, a "
                  "wrong result, broken behavior)? Answer no for feature requests, enhancement ideas, performance "
                  "wishes, usage questions and spam."},
    "is_feature_request": {"type": "noul", "instructions":
                           "Is the author asking for a new feature, an enhancement or a change of the intended "
                           "behavior, rather than reporting something that is broken?"},
    "is_spam": {"type": "noul", "instructions":
                "Is this issue spam, gibberish, placeholder or test text, or otherwise not a genuine report about "
                "the software?"},
    "actionable": {"type": "noul", "instructions":
                   "Could a maintainer act on this issue with what is written, without asking the author for "
                   "anything else?"},
    "enough_info": {"type": "noul", "instructions":
                    "Does the issue give enough information for a maintainer to understand and act on it? For a "
                    "defect: steps, versions or error output to reproduce it. For a request: a clear description of "
                    "what is wanted."},
    "usage_question": {"type": "noul", "instructions":
                       "Is the author asking how to use the software, rather than reporting a defect or requesting "
                       "a change?"},
    "severity": {"type": "score", "instructions": "How severe is the problem described in this issue?",
                 "criteria": SEVERITY},
}
NOUL_Q1 = ["is_defect", "actionable", "enough_info", "usage_question"]
NOUL_Q2 = ["is_defect", "is_feature_request", "is_spam", "actionable", "enough_info", "usage_question"]
REPOS = {"microsoft/TypeScript": None, "godotengine/godot": 800, "microsoft/vscode": 800}
SEED = 42


def sample(data_dir):
    rnd = random.Random(SEED)
    out = {}
    for repo, cap in REPOS.items():
        ex = load_repo(data_dir, repo)
        out[repo] = ex if cap is None or len(ex) <= cap else rnd.sample(ex, cap)
    return out


def ask_q2(s, model, text):
    body = {"model": model, "state": text, "questions": Q2}
    for attempt in range(6):
        r = s.post("https://api.typesafe.ai/v1/systemone", json=body, timeout=60)
        if r.status_code in (429, 529) or r.status_code >= 500:
            time.sleep(float(r.headers.get("retry-after", 2 ** attempt)))
            continue
        r.raise_for_status()
        data = r.json()
        a = data["answers"]
        ans = {k: float(a[k]["noul"]) for k in NOUL_Q2}
        probs = [float(a["severity"]["probabilities"][str(i)]) for i in range(4)]
        ans["severity_expected"] = sum(i * p for i, p in enumerate(probs))
        tok = (data.get("usage") or {})
        return ans, data.get("model"), (tok.get("input_tokens") or 0) + (tok.get("output_tokens") or 0)
    raise RuntimeError("Jev: muitas tentativas")


def run_q2(samples, cache_path, model, workers=4):
    cache = {}
    if cache_path.exists():
        for line in cache_path.read_text(encoding="utf-8").split("\n"):
            if line.strip():
                r = json.loads(line)
                cache[(r["repo"], r["number"])] = r
    todo = [e for ex in samples.values() for e in ex if (e.repo, e.number) not in cache]
    print(f"q2: {len(cache)} em cache, {len(todo)} a perguntar", file=sys.stderr, flush=True)
    s = jev.session()
    tokens, served = 0, set()

    def one(e):
        ans, srv, tok = ask_q2(s, model, e.text)
        return {"repo": e.repo, "number": e.number, "answers": ans, "served_by": srv, "tokens": tok}

    with ThreadPoolExecutor(workers) as pool, open(cache_path, "a", encoding="utf-8") as f:
        for i, r in enumerate(pool.map(one, todo), 1):
            cache[(r["repo"], r["number"])] = r
            f.write(json.dumps(r) + "\n")
            tokens += r["tokens"]
            served.add(r["served_by"])
            if i % 100 == 0:
                print(f"  {i}/{len(todo)}", file=sys.stderr, flush=True)
    return cache, tokens, served


def q1_matrix(xs):
    return np.array([[e.answers[k] for k in NOUL_Q1] + [sum(i * p for i, p in enumerate(e.answers["severity"]["probs"]))]
                     for e in xs], dtype=float)


def q2_matrix(xs, cache):
    return np.array([[cache[(e.repo, e.number)]["answers"][k] for k in NOUL_Q2]
                     + [cache[(e.repo, e.number)]["answers"]["severity_expected"]] for e in xs], dtype=float)


def lr(Xtr, ytr, Xte):
    return _proba(make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)), Xtr, ytr, Xte)


def compare(samples, cache):
    splits = {r: temporal_split(ex) for r, ex in samples.items()}
    splits["all"] = Split([e for s in splits.values() for e in s.train], [e for s in splits.values() for e in s.test])
    rows = {}
    for repo, sp in splits.items():
        ytr, yte = np.array([e.y for e in sp.train]), np.array([e.y for e in sp.test])
        variants = {
            "Jev q1 + regressão": lr(q1_matrix(sp.train), ytr, q1_matrix(sp.test)),
            "Jev q2 + regressão": lr(q2_matrix(sp.train, cache), ytr, q2_matrix(sp.test, cache)),
            "Jev q1 bruto (1 − é defeito)": Scores(1 - q1_matrix(sp.train)[:, 0], 1 - q1_matrix(sp.test)[:, 0], False),
            "Jev q2 bruto (1 − é defeito)": Scores(1 - q2_matrix(sp.train, cache)[:, 0],
                                                    1 - q2_matrix(sp.test, cache)[:, 0], False),
            "TF-IDF + regressão (régua)": tfidf_lr(sp.train, sp.test),
        }
        for name, sc in variants.items():
            rows[(repo, name)] = {**evaluate(yte, sc.test, ytr, sc.train_oof, sc.probability),
                                  "n_train": len(sp.train)}
        # AUC de cada pergunta q2 sozinha no teste (sinal invertido onde "sim" indica ação)
        from sklearn.metrics import roc_auc_score
        X = q2_matrix(sp.test, cache)
        rows[(repo, "_perguntas")] = {k: float(roc_auc_score(yte, X[:, i] if k in ("is_feature_request", "is_spam",
                                                                                    "usage_question") else -X[:, i]))
                                      for i, k in enumerate(NOUL_Q2)}
    return rows


def report(rows, tokens, served, n, generated_at):
    lines = [f"# Experimento q2: perguntas ajustadas ao Jev ({generated_at[:10]})", "",
             "Gerado por `python -m experimentos.q2`. Não muda o job nem o branch `data`.", "",
             f"Amostra: {n} issues fechadas (todo o TypeScript, até 800 de Godot e de VS Code, semente 42), com "
             "desfecho `no_action`/`action` (`gab-1`). Corte temporal dentro da amostra de cada repositório "
             "(70% mais antigas = treino). As respostas q1 são as do backfill; as q2 foram pedidas ao Jev "
             f"({', '.join(sorted(served))}) para este experimento, ~{tokens / 1e6:.1f} milhões de tokens.", "",
             "## O que mudou nas perguntas", "",
             "- **É defeito?** passa a dizer que pedido de recurso, desempenho, dúvida e spam não são defeito.",
             "- **É pedido de recurso?** (nova).",
             "- **É spam ou texto sem sentido?** (nova).",
             "- **Informação suficiente?** passa a valer também para pedidos (descrição clara do que se quer).",
             "- **Dá para agir?**, **pergunta de uso?** e **severidade** iguais à q1.", ""]
    for repo in ["microsoft/vscode", "microsoft/TypeScript", "godotengine/godot", "all"]:
        any_r = rows[(repo, "Jev q1 + regressão")]
        lines += [f"## {'Todos (3 repositórios)' if repo == 'all' else repo}", "",
                  f"Treino {any_r['n_train']} · teste {any_r['n']} · sem ação no teste: {100 * any_r['base_rate']:.0f}%", "",
                  "| Modelo | AUC [IC 95%] | Precisão média | Brier |", "|---|---|---|---|"]
        for name in ["Jev q1 bruto (1 − é defeito)", "Jev q2 bruto (1 − é defeito)", "Jev q1 + regressão",
                     "Jev q2 + regressão", "TF-IDF + regressão (régua)"]:
            r = rows[(repo, name)]
            b = "—" if r["brier"] is None else f"{r['brier']:.3f}"
            lines.append(f"| {name} | {r['auc']:.3f} [{r['auc_ci'][0]:.3f}–{r['auc_ci'][1]:.3f}] | "
                         f"{r['average_precision']:.3f} | {b} |")
        q = rows[(repo, "_perguntas")]
        lines += ["", "AUC de cada pergunta q2 sozinha no teste: " + ", ".join(f"{k} {v:.2f}" for k, v in q.items()) + ".", ""]
    lines += ["## Limitações", "",
              "- Amostra menor que a dos baselines (o TF-IDF também treina com menos dados aqui, então os números "
              "não são diretamente comparáveis com o relatório de baselines; a comparação justa é dentro desta tabela).",
              "- O Jev não é totalmente determinístico (variação de até ~0,04 por resposta).",
              "- TypeScript pequeno: intervalos largos.", ""]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m experimentos.q2")
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--cache", required=True, help="JSONL com as respostas q2 já pedidas (retoma de onde parou)")
    ap.add_argument("--out", default="docs/resultados")
    ap.add_argument("--model", default="jev-1.14.0")
    args = ap.parse_args(argv)
    load_dotenv(Path(".env"))
    samples = sample(args.data_dir)
    n = sum(len(v) for v in samples.values())
    cache, tokens, served = run_q2(samples, Path(args.cache), args.model)
    rows = compare(samples, cache)
    now = datetime.now(timezone.utc)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"experimento-q2-{now:%Y-%m-%d}.md"
    path.write_text(report(rows, tokens, served or {args.model}, n, now.strftime("%Y-%m-%dT%H:%M:%SZ")), encoding="utf-8")
    print(f"relatório em {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
