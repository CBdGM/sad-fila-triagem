"""Checagens da auditoria. Cada uma devolve achados (nível, repositório, mensagem).

Erro: dado corrompido, não pode chegar ao site. Atenção: dado parado ou crescendo, alguém precisa olhar.
"""
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from collector import store
from collector.collect import is_open

ERRO, ATENCAO = "erro", "atenção"
CONTRACTS = {"issues.jsonl": "issue", "outcomes.jsonl": "outcome", "predictions.jsonl": "prediction"}


def parse_utc(s):
    return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")


def contract_errors(folder):
    """Linhas fora do contrato, por arquivo (para no primeiro erro de cada arquivo, com a contagem)."""
    out = []
    for name, contract in CONTRACTS.items():
        bad, first = 0, None
        for n, row in enumerate(store.read_jsonl(folder / name), 1):
            try:
                store.validate(contract, row, f"{name}:{n}")
            except store.ContractError as e:
                bad += 1
                first = first or str(e)
        if bad:
            out.append(f"{name}: {bad} linha(s) fora do contrato (ex.: {first[:200]})")
    state = store.read_state(folder / "state.json")
    if state is None:
        out.append("state.json ausente")
    else:
        try:
            store.validate("state", state, "state.json")
        except store.ContractError as e:
            out.append(str(e)[:200])
    return out


def integrity_errors(issues, outcomes, predictions):
    out = []
    dup = sum(v > 1 for v in Counter((o["number"], o["closed_at"]) for o in outcomes).values())
    if dup:
        out.append(f"{dup} desfecho(s) repetido(s)")
    keys = Counter((p["number"], p["body_sha256"], p["versions"]["model"], p["versions"]["questions"],
                    p["versions"]["cleaning"]) for p in predictions)
    dup = sum(v > 1 for v in keys.values())
    if dup:
        out.append(f"{dup} previsão(ões) repetida(s)")
    fs = sum(v > 1 for v in Counter(p["number"] for p in predictions if p["first_seen"]).values())
    if fs:
        out.append(f"{fs} issue(s) com mais de um first_seen")
    unknown = {p["number"] for p in predictions} - set(issues)
    if unknown:
        out.append(f"{len(unknown)} previsão(ões) de issue fora do issues.jsonl (ex.: {sorted(unknown)[:5]})")
    return out


def freshness_warnings(issues, outcomes, predictions, state, now, *, max_hours, max_days):
    out = []
    last = (state or {}).get("last_success_at")
    if not last or now - parse_utc(last) > timedelta(hours=max_hours):
        out.append(f"última coleta bem-sucedida: {last or 'nunca'} (limite: {max_hours} h)")
    have = {(o["number"], o["closed_at"]) for o in outcomes}
    pending = [i["number"] for i in issues.values()
               if i["state"] == "closed" and (i["number"], i.get("closed_at")) not in have]
    if pending:
        out.append(f"{len(pending)} fechada(s) sem desfecho (ex.: {sorted(pending)[:5]})")
    predicted = {p["number"] for p in predictions}
    cutoff = now - timedelta(days=max_days)
    stale = [i["number"] for i in issues.values()
             if is_open(i) and i["number"] not in predicted and parse_utc(i["first_seen_at"]) < cutoff]
    if stale:
        out.append(f"{len(stale)} aberta(s) vista(s) há mais de {max_days} dias sem previsão do Jev (ex.: {sorted(stale)[:5]})")
    return out


def dir_size_mb(path):
    return sum(f.stat().st_size for f in Path(path).rglob("*") if f.is_file()) / 1e6


def audit(cfg, data_dir, now, *, max_hours=36, max_days=4, max_mb=150):
    """Lista de (nível, repositório ou '*', mensagem) para os repositórios habilitados."""
    findings = []
    for r in cfg["repos"]:
        if not r.get("enabled", True):
            continue
        repo = r["repo"]
        folder = store.repo_dir(data_dir, repo)
        if not (folder / "issues.jsonl").exists():
            findings.append((ATENCAO, repo, "sem issues.jsonl (repositório ainda não coletado?)"))
            continue
        errs = contract_errors(folder)
        findings += [(ERRO, repo, m) for m in errs]
        if errs:
            continue  # com linhas fora do contrato, as outras checagens podem quebrar
        issues = store.read_issues(folder / "issues.jsonl")
        outcomes = store.read_jsonl(folder / "outcomes.jsonl")
        predictions = store.read_jsonl(folder / "predictions.jsonl")
        findings += [(ERRO, repo, m) for m in integrity_errors(issues, outcomes, predictions)]
        findings += [(ATENCAO, repo, m) for m in freshness_warnings(
            issues, outcomes, predictions, store.read_state(folder / "state.json"), now,
            max_hours=max_hours, max_days=max_days)]
    size = dir_size_mb(data_dir)
    if size > max_mb:
        findings.append((ATENCAO, "*", f"pasta de dados com {size:.0f} MB (limite: {max_mb} MB)"))
    return findings
