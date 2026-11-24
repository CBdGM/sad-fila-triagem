"""Linha de comando da auditoria do branch data.

    python -m audit --data-dir dados/data

Sai com 0 sem achados, 1 se só houver atenções (dados parados ou crescendo) e 2 se houver algum
erro (dados corrompidos). No job diário, só o código 2 impede a publicação da fila.
"""
import argparse
import sys
from datetime import datetime, timezone

from collector import store

from .checks import ERRO, audit, dir_size_mb


def main(argv=None, *, now=None):
    ap = argparse.ArgumentParser(prog="python -m audit", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="repos.yaml", help="arquivo de configuração (padrão: repos.yaml)")
    ap.add_argument("--data-dir", default="data", help="pasta dos dados (padrão: data)")
    ap.add_argument("--max-hours", type=int, default=36, help="idade máxima da última coleta, em horas (padrão: 36)")
    ap.add_argument("--max-days", type=int, default=4, help="dias que uma aberta pode ficar sem previsão (padrão: 4)")
    ap.add_argument("--max-mb", type=int, default=150, help="tamanho máximo da pasta de dados (padrão: 150)")
    args = ap.parse_args(argv)
    try:
        cfg = store.load_config(args.config)
    except (OSError, store.ContractError) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 2
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    findings = audit(cfg, args.data_dir, now, max_hours=args.max_hours, max_days=args.max_days, max_mb=args.max_mb)
    for level, repo, msg in findings:
        print(f"{level.upper():8} {repo}: {msg}", file=sys.stderr)
    n_err = sum(f[0] == ERRO for f in findings)
    print(f"auditoria: {n_err} erro(s), {len(findings) - n_err} atenção(ões); dados com "
          f"{dir_size_mb(args.data_dir):.0f} MB", file=sys.stderr)
    return 2 if n_err else (1 if findings else 0)


if __name__ == "__main__":
    sys.exit(main())
