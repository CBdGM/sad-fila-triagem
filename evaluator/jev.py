"""Cliente do Jev (TypeSafe), chamada A.

Formato da API como na PoC (sad-poc-decisao, models.py), conferido numa chamada real em 20/10/2026:
    POST {base}/v1/systemone  {"model", "state", "questions"}
    -> {"model": "jev-1.14.0", "answers": {"<id>": {"type": "noul", "noul": 0.95} | {"type": "score",
        "probabilities": {"0": p0, ...}, "score": s}}, "usage": {"input_tokens", "output_tokens"}}
    Cabeçalho x-typesafe-request-id; 429/529 = limite ou sobrecarga (repetir com retry-after).
"""
import os
import re
import time

import requests

from .questions import QUESTIONS, SEVERITY_LEVELS

MODEL_PATTERN = re.compile(r"^jev-\d+\.\d+\.\d+$")
MAX_RETRIES = 5


class JevError(RuntimeError):
    pass


def session(key=None):
    key = key or os.getenv("TYPESAFE_API_KEY")
    if not key:
        raise JevError("TYPESAFE_API_KEY não definida (coloque no .env ou nos secrets do Actions)")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    return s


def check_model(model):
    if not MODEL_PATTERN.match(model or ""):
        raise JevError(f"model {model!r} em repos.yaml: use uma versão explícita, ex.: jev-1.14.0 (nunca jev-latest)")


def normalize(answers):
    """Respostas do Jev → bloco `answers` do contrato prediction.schema.json."""
    out = {}
    try:
        for qid, q in QUESTIONS.items():
            a = answers[qid]
            if q["type"] == "noul":
                if a.get("type") != "noul":
                    raise ValueError(qid)
                out[qid] = float(a["noul"])
            else:
                if a.get("type") != "score":
                    raise ValueError(qid)
                probs = [float(a["probabilities"][str(i)]) for i in range(len(SEVERITY_LEVELS))]
                out[qid] = {"probs": probs, "level": SEVERITY_LEVELS[max(range(len(probs)), key=probs.__getitem__)]}
    except (KeyError, TypeError, ValueError) as e:
        raise JevError(f"resposta inesperada do Jev (pergunta {e}): {str(answers)[:300]}") from None
    return out


def ask(s, model, state, *, base=None, sleep=time.sleep, clock=time.perf_counter):
    """Chamada A. Devolve (answers normalizadas, procedência da chamada)."""
    base = (base or os.getenv("TYPESAFE_BASE_URL", "https://api.typesafe.ai")).rstrip("/")
    body = {"model": model, "state": state, "questions": QUESTIONS}
    for attempt in range(MAX_RETRIES):
        t0 = clock()
        try:
            r = s.post(f"{base}/v1/systemone", json=body, timeout=60)
        except requests.RequestException as e:
            if attempt == MAX_RETRIES - 1:
                raise JevError(f"erro de rede no Jev: {type(e).__name__}") from None
            sleep(2 ** attempt)
            continue
        latency = (clock() - t0) * 1000
        if r.status_code in (429, 529) or r.status_code >= 500:
            sleep(float(r.headers.get("retry-after", 2 ** attempt)))
            continue
        if r.status_code == 401:
            raise JevError("autenticação no Jev falhou (TYPESAFE_API_KEY inválida?)")
        if r.status_code >= 400:
            raise JevError(f"Jev respondeu {r.status_code}: {r.text[:300]}")
        data = r.json()
        usage = data.get("usage") or {}
        tokens = (usage.get("input_tokens") or 0) + (usage.get("output_tokens") or 0) if usage else None
        prov = {"call": "A", "served_by": data.get("model") or "?",
                "request_id": r.headers.get("x-typesafe-request-id") or None,
                "latency_ms": round(latency, 1), "tokens": tokens}
        return normalize(data.get("answers") or {}), prov
    raise JevError(f"Jev: {MAX_RETRIES} tentativas com limite, sobrecarga ou erro do servidor")
