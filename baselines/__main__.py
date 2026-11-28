"""Baselines da Fase 1 a partir do branch data.

    python -m baselines --data-dir ../sad-fila-data/data --out docs/resultados

Grava baselines-<data>.md (tabela e notas) e baselines-<data>.json (formato do metrics.schema.json).
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from collector import store
from collector.collect import utc

from .data import Split, load_repo, temporal_split
from .metrics import TARGET_PRECISION, evaluate
from .models import MODELS
from .report import markdown

PRINCIPAIS = ["microsoft/vscode", "microsoft/TypeScript", "godotengine/godot"]


def run(data_dir, repos):
    splits = {r: temporal_split(load_repo(data_dir, r)) for r in repos}
    splits["all"] = Split([e for s in splits.values() for e in s.train], [e for s in splits.values() for e in s.test])
    results = {}
    for repo, sp in splits.items():
        y_tr = np.array([e.y for e in sp.train])
        y_te = np.array([e.y for e in sp.test])
        for key, (_, fn) in MODELS.items():
            sc = fn(sp.train, sp.test)
            r = evaluate(y_te, sc.test, y_tr, sc.train_oof, sc.probability)
            ext = np.array([e.external for e in sp.test])
            if ext.sum() >= 20 and 0 < y_te[ext].mean() < 1:  # recorte: só autores de fora da equipe
                r["external"] = evaluate(y_te[ext], sc.test[ext], y_tr, sc.train_oof, sc.probability)
            r.update(note=sc.note, n_train=len(sp.train),
                     train_period=[sp.train[0].created_at[:10], sp.train[-1].created_at[:10]] if sp.train else None,
                     test_period=[sp.test[0].created_at[:10], sp.test[-1].created_at[:10]] if sp.test else None)
            results[(repo, key)] = r
            print(f"  {repo:22} {key:16} AUC {r['auc']:.3f}", file=sys.stderr, flush=True)
    return results


def metrics_doc(results, generated_at):
    evals = [{"design": "temporal", "repo": repo, "model": key, "n": r["n"], "auc": r["auc"],
              "precision_no_action": r["precision_no_action"], "recall_no_action": r["recall_no_action"],
              "coverage": r["coverage"], "brier": r["brier"], "calibrator": None,
              "target_precision": TARGET_PRECISION}
             for (repo, key), r in results.items()]
    return {"schema_version": 1, "generated_at": generated_at, "evaluations": evals}


def main(argv=None, *, now=None):
    ap = argparse.ArgumentParser(prog="python -m baselines", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default="data", help="pasta dos dados (padrão: data)")
    ap.add_argument("--out", default="docs/resultados", help="pasta do relatório (padrão: docs/resultados)")
    ap.add_argument("--repo", action="append", help="repositório (repita para vários; padrão: os 3 principais)")
    args = ap.parse_args(argv)
    now = now or datetime.now(timezone.utc)
    repos = args.repo or PRINCIPAIS
    results = run(args.data_dir, repos)
    doc = metrics_doc(results, utc(now))
    store.validate("metrics", doc, "avaliações dos baselines")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = out / f"baselines-{now:%Y-%m-%d}"
    stem.with_suffix(".json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    stem.with_suffix(".md").write_text(markdown(results, repos, utc(now)), encoding="utf-8")
    print(f"relatório em {stem}.md e {stem}.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
