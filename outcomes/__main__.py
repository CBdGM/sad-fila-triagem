"""Linha de comando dos desfechos.

    python -m outcomes                          # todos os repositórios habilitados em repos.yaml
    python -m outcomes --repo apache/airflow    # um repositório (precisa estar em repos.yaml)
    python -m outcomes --max 200                # no máximo 200 desfechos por repositório nesta execução

Precisa do issues.jsonl gerado pelo coletor (python -m collector).
"""
import argparse
import sys

from dotenv import load_dotenv

from collector import github, store

from .run import BATCH_SIZE, collect_outcomes, phase0_summary


def main(argv=None, *, make_session=github.session):
    ap = argparse.ArgumentParser(prog="python -m outcomes", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", help="owner/nome de um repositório de repos.yaml")
    ap.add_argument("--config", default="repos.yaml", help="arquivo de configuração (padrão: repos.yaml)")
    ap.add_argument("--data-dir", default="data", help="pasta dos dados (padrão: data)")
    ap.add_argument("--max", type=int, help="teto de desfechos por repositório nesta execução")
    ap.add_argument("--batch", type=int, default=BATCH_SIZE, help=f"issues por consulta (padrão: {BATCH_SIZE})")
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

    s = make_session()
    failed = 0
    for r in repos:
        repo = r["repo"]
        before = github.usage(s).requests
        emit = lambda msg, repo=repo: print(f"  {repo} · {msg}", file=sys.stderr, flush=True)  # noqa: E731
        try:
            res = collect_outcomes(s, repo, r, args.data_dir, max_items=args.max, batch_size=args.batch, emit=emit)
        except (github.GitHubError, store.ContractError, FileNotFoundError) as e:
            failed += 1
            print(f"{repo}: FALHOU (lotes já concluídos ficaram gravados). {e}", file=sys.stderr)
            continue
        summary = phase0_summary(store.read_jsonl(store.repo_dir(args.data_dir, repo) / "outcomes.jsonl"))
        print(_report(repo, res, summary, github.usage(s).requests - before), file=sys.stderr)
    return 1 if failed else 0


def _report(repo, res, sm, requests):
    pct = f"{sm['pct_no_action']:.1f}%" if sm["pct_no_action"] is not None else "—"
    lines = [f"{repo}: {res['added']} desfechos novos ({requests} consultas)"
             + (f"; faltam {res['pending_left']} (use sem --max para continuar)" if res["pending_left"] else ""),
             f"  total: {sm['no_action']} sem ação, {sm['action']} com ação, {sm['excluded']} fora da conta"
             f" → sem ação = {pct} (portão da Fase 0: ≥ 15%)"]
    if sm["reasons"]:
        lines.append("  motivos: " + ", ".join(f"{k} {v}" for k, v in sorted(sm["reasons"].items(), key=lambda x: -x[1])))
    if sm["exclusions"]:
        lines.append("  fora da conta: " + ", ".join(f"{k} {v}" for k, v in sm["exclusions"].items()))
    if res["skipped"]:
        lines.append(f"  puladas (apagadas ou transferidas): {res['skipped'][:10]}")
    if res["truncated"]:
        lines.append(f"  AVISO: eventos cortados em {len(res['truncated'])} issues (ex.: {res['truncated'][:5]})")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
