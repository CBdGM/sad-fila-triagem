"""Linha de comando da publicação.

    python -m publisher --data-dir dados/data --out public

Monta public/queue.json, public/metrics.json e public/index.html. Se algum JSON não passar no
contrato, nada é gravado e o comando sai com erro (o site anterior continua no ar).
"""
import argparse
import sys
from datetime import datetime, timezone

from collector import store
from collector.collect import utc

from .build import build, write


def main(argv=None, *, now=None):
    ap = argparse.ArgumentParser(prog="python -m publisher", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="repos.yaml", help="arquivo de configuração (padrão: repos.yaml)")
    ap.add_argument("--data-dir", default="data", help="pasta dos dados (padrão: data)")
    ap.add_argument("--out", default="public", help="pasta de saída (padrão: public)")
    args = ap.parse_args(argv)
    try:
        cfg = store.load_config(args.config)
        queue, metrics, summary = build(cfg, args.data_dir, utc(now or datetime.now(timezone.utc)))
        write(args.out, queue, metrics)
    except (OSError, store.ContractError) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    for repo, s in summary.items():
        extra = f" ({s['open_without_prediction']} abertas ainda sem previsão do Jev)" if s["open_without_prediction"] else ""
        print(f"{repo}: {s['items']} na fila{extra}", file=sys.stderr)
    print(f"publicado em {args.out}/: {len(queue['items'])} itens", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
