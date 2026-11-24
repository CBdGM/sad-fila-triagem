"""Linha de comando do avaliador (chamada A do Jev).

    python -m evaluator --mode backfill --max 50     # fechadas com desfecho (treino do calibrador)
    python -m evaluator --mode daily                 # abertas
    python -m evaluator --mode backfill --repo microsoft/TypeScript --max 20

Precisa de TYPESAFE_API_KEY (.env ou ambiente), do issues.jsonl do coletor e, no backfill,
do outcomes.jsonl dos desfechos. A versão do Jev é o `model` de repos.yaml.
"""
import argparse
import sys

from dotenv import load_dotenv

from collector import github, store

from . import jev
from .run import BATCH_SIZE, evaluate_repo


def main(argv=None, *, make_github=github.session, make_jev=jev.session):
    ap = argparse.ArgumentParser(prog="python -m evaluator", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", required=True, choices=["backfill", "daily"])
    ap.add_argument("--repo", help="owner/nome de um repositório de repos.yaml")
    ap.add_argument("--config", default="repos.yaml", help="arquivo de configuração (padrão: repos.yaml)")
    ap.add_argument("--data-dir", default="data", help="pasta dos dados (padrão: data)")
    ap.add_argument("--max", type=int, help="teto de issues avaliadas por repositório nesta execução")
    ap.add_argument("--batch", type=int, default=BATCH_SIZE, help=f"issues por consulta ao GitHub (padrão: {BATCH_SIZE})")
    args = ap.parse_args(argv)

    load_dotenv()
    try:
        cfg = store.load_config(args.config)
        jev.check_model(cfg["model"])
        js = make_jev()
    except (OSError, store.ContractError, jev.JevError) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 2
    repos = [r for r in cfg["repos"] if r.get("enabled", True)]
    if args.repo:
        repos = [r for r in cfg["repos"] if r["repo"].lower() == args.repo.lower()]
        if not repos:
            print(f"ERRO: {args.repo} não está em {args.config}", file=sys.stderr)
            return 2

    gh = make_github()
    failed = 0
    for r in repos:
        repo = r["repo"]
        emit = lambda msg, repo=repo: print(f"  {repo} · {msg}", file=sys.stderr, flush=True)  # noqa: E731
        try:
            res = evaluate_repo(gh, js, repo, cfg["model"], args.data_dir, mode=args.mode,
                                max_items=args.max, batch_size=args.batch, emit=emit)
        except (github.GitHubError, jev.JevError, store.ContractError, FileNotFoundError) as e:
            failed += 1
            print(f"{repo}: FALHOU (previsões já feitas ficaram gravadas). {e}", file=sys.stderr)
            continue
        print(_report(repo, res), file=sys.stderr)
    return 1 if failed else 0


def _report(repo, res):
    avg = f", média {res['tokens'] // res['added']} por issue" if res["added"] else ""
    lines = [f"{repo}: {res['added']} previsões novas ({res['tokens']} tokens{avg})"
             + (f"; faltam {res['pending_left']} (rode de novo para continuar)" if res["pending_left"] else "")]
    if res["edited"]:
        lines.append(f"  editadas depois da coleta (rode o coletor antes): {res['edited'][:10]}")
    if res["skipped"]:
        lines.append(f"  puladas (apagadas ou transferidas): {res['skipped'][:10]}")
    if res["other_model"]:
        lines.append(f"  AVISO: o servidor respondeu com {res['other_model']}, diferente do model de repos.yaml")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
