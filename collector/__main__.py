"""Linha de comando do coletor.

    python -m collector                          # todos os repositórios habilitados em repos.yaml
    python -m collector --repo apache/airflow    # um repositório (precisa estar em repos.yaml)
    python -m collector --changes mudancas.json  # grava new/edited/closed de cada repositório em JSON
    python -m collector --changes                # o mesmo, no stdout (para encadear com outro programa)
    python -m collector --config repos.yaml --data-dir data
"""
import argparse
import json
import sys

from dotenv import load_dotenv

from . import github, store
from .collect import Progress, collect_repo


def main(argv=None, *, make_session=github.session):
    ap = argparse.ArgumentParser(prog="python -m collector", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", help="owner/nome de um repositório de repos.yaml")
    ap.add_argument("--config", default="repos.yaml", help="arquivo de configuração (padrão: repos.yaml)")
    ap.add_argument("--data-dir", default="data", help="pasta dos dados (padrão: data)")
    ap.add_argument("--changes", nargs="?", const="-", metavar="ARQUIVO",
                    help="grava o que mudou (new/edited/closed) em JSON no ARQUIVO; sem ARQUIVO, no stdout")
    args = ap.parse_args(argv)

    load_dotenv()
    try:
        cfg = store.load_config(args.config)
    except (OSError, store.ContractError) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 2

    repos = [r for r in cfg["repos"] if r.get("enabled", True)]
    if args.repo:
        repos = [r for r in cfg["repos"] if r["repo"].lower() == args.repo.lower()]
        if not repos:
            print(f"ERRO: {args.repo} não está em {args.config}", file=sys.stderr)
            return 2
        if not repos[0].get("enabled", True):
            print(f"ERRO: {args.repo} está com enabled: false em {args.config}", file=sys.stderr)
            return 2

    s = make_session()
    result, failed = {}, 0
    for r in repos:
        repo = r["repo"]
        before = github.usage(s).requests
        progress = Progress(lambda msg, repo=repo: print(f"  {repo} · {msg}", file=sys.stderr, flush=True))
        try:
            ch = collect_repo(s, repo, cfg, args.data_dir, progress=progress)
        except (github.GitHubError, store.ContractError) as e:
            failed += 1
            print(f"{repo}: FALHOU, nada gravado. {e}", file=sys.stderr)
            continue
        result[repo] = ch.as_dict()
        print(f"{repo}: {len(ch.new)} novas, {len(ch.edited)} editadas, {len(ch.closed)} fechadas"
              f" ({_usage_text(github.usage(s), before)})", file=sys.stderr)

    if args.changes == "-":
        print(json.dumps(result, ensure_ascii=False))
    elif args.changes:
        with open(args.changes, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Mudanças gravadas em {args.changes}", file=sys.stderr)
    return 1 if failed else 0


def _usage_text(u, before):
    text = f"{u.requests - before} requisições"
    if u.remaining is not None and u.limit is not None:
        text += f"; restam {u.remaining} de {u.limit} nesta hora"
    return text


if __name__ == "__main__":
    sys.exit(main())
