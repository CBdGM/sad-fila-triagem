"""Troca trechos com formato de credencial conhecida por [REDACTED] no texto gravado.

Issues públicas às vezes trazem tokens colados pelo autor. Gravá-los no branch `data` republicaria
credenciais de terceiros, e a proteção de segredos do GitHub bloqueia o push (aconteceu com
microsoft/vscode#338747). Só o `input_text` gravado é redigido; o texto enviado ao Jev não muda.
"""
import re

MARK = "[REDACTED]"

PATTERNS = [
    r"\bgh[opusr]_[A-Za-z0-9]{36,}\b",            # GitHub (clássico e de apps)
    r"\bgithub_pat_[A-Za-z0-9_]{60,}\b",           # GitHub (fine-grained)
    r"\b[A-Za-z0-9]{76}AZDO[A-Za-z0-9]{4}\b",      # Azure DevOps (formato novo)
    r"\b[a-z2-7]{52}\b",                           # Azure DevOps (52 base32 minúsculos)
    r"\bAKIA[0-9A-Z]{16}\b",                       # AWS access key id
    r"\bsk-[A-Za-z0-9_-]{20,}\b",                  # OpenAI e similares
    r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b",           # Slack
    r"\bAIza[0-9A-Za-z_-]{35}\b",                  # Google API key
]
_RE = re.compile("|".join(PATTERNS))


def redact(text):
    """Devolve (texto redigido, quantos trechos foram trocados)."""
    if not text:
        return text, 0
    return _RE.subn(MARK, text)
