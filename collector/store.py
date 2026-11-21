"""Leitura e gravação atômica dos arquivos de dados, sempre validados pelos contratos."""
import json
import os
import tempfile
from functools import lru_cache
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

CONTRACTS = Path(__file__).resolve().parent.parent / "contracts"


class ContractError(ValueError):
    """Um registro não passou no contrato; nada foi gravado."""


@lru_cache(maxsize=None)
def _validator(contract):
    schema = json.loads((CONTRACTS / f"{contract}.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def validate(contract, record, label=""):
    errors = sorted(_validator(contract).iter_errors(record), key=lambda e: list(e.path))
    if errors:
        msgs = [f"[{'/'.join(map(str, e.path)) or 'raiz'}] {e.message}" for e in errors[:5]]
        raise ContractError(f"{label or contract} fora do contrato {contract}: " + "; ".join(msgs))


def repo_dir(data_dir, repo):
    return Path(data_dir) / repo.replace("/", "__")


def load_config(path):
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    validate("repos", cfg, str(path))
    return cfg


def read_issues(path):
    """issues.jsonl → {número: linha}. Arquivo ausente = vazio."""
    path = Path(path)
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            out[rec["number"]] = rec
    return out


def read_state(path):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def write_issues(path, issues):
    """Valida todas as linhas e só então substitui o arquivo (ordenado por número)."""
    lines = []
    for number in sorted(issues):
        validate("issue", issues[number], f"issue #{number}")
        lines.append(json.dumps(issues[number], ensure_ascii=False, sort_keys=False))
    _atomic_write(path, "".join(line + "\n" for line in lines))


def read_jsonl(path):
    """Linhas de um JSONL como lista (arquivo ausente = vazio)."""
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_jsonl(path, rows, contract, label=lambda row: ""):
    """Acrescenta linhas a um JSONL só de acréscimo: valida as novas e regrava de forma atômica,
    mantendo as linhas antigas exatamente como estavam."""
    for row in rows:
        validate(contract, row, label(row))
    path = Path(path)
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if old and not old.endswith("\n"):
        old += "\n"
    _atomic_write(path, old + "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def write_state(path, state):
    validate("state", state, "state.json")
    _atomic_write(path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")
