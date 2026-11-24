"""Valida arquivos de dados contra os contratos em contracts/.

Uso:
    python contracts/validate.py                      # valida todos os exemplos de contracts/examples/
    python contracts/validate.py <contrato> <arquivo>  # ex.: queue public/queue.json

<contrato> é o nome do schema sem ".schema.json": repos, state, issue, prediction, outcome,
queue, metrics. Arquivos .jsonl são validados linha a linha; .yaml/.yml são lidos como YAML.
Sai com código 1 se algum arquivo for inválido.
"""
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

HERE = Path(__file__).parent
EXAMPLES = {  # contrato -> exemplo
    "repos": "repos.yaml",
    "state": "state.json",
    "issue": "issues.jsonl",
    "prediction": "predictions.jsonl",
    "outcome": "outcomes.jsonl",
    "queue": "queue.json",
    "metrics": "metrics.json",
}


def load_records(path: Path):
    """(rótulo, objeto) para cada registro do arquivo."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        for i, line in enumerate(text.split("\n"), 1):
            if line.strip():
                yield f"{path}:{i}", json.loads(line)
    elif path.suffix in (".yaml", ".yml"):
        yield str(path), yaml.safe_load(text)
    else:
        yield str(path), json.loads(text)


def validate_file(contract: str, path: Path) -> int:
    schema = json.loads((HERE / f"{contract}.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = 0
    for label, record in load_records(path):
        for err in sorted(validator.iter_errors(record), key=lambda e: list(e.path)):
            where = "/".join(str(p) for p in err.path) or "(raiz)"
            print(f"ERRO {label} [{where}]: {err.message}")
            errors += 1
    if not errors:
        print(f"ok   {path} ({contract})")
    return errors


def main(argv):
    if len(argv) == 2:
        return 1 if validate_file(argv[0], Path(argv[1])) else 0
    if argv:
        print(__doc__)
        return 2
    total = sum(validate_file(c, HERE / "examples" / f) for c, f in EXAMPLES.items())
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
