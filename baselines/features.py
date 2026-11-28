"""Sinais da heurística, definidos a priori (sinais clássicos de triagem), sem ajuste a estes dados."""
import math
import re

import numpy as np

SIGNALS = {
    "stack_trace": re.compile(r"Traceback \(most recent call last\)|^\s+at \S+\(.*:\d+|\b\w+(Error|Exception):|panic:|"
                              r"segmentation fault|SIGSEGV|core dumped", re.M | re.I),
    "code_block": re.compile(r"```"),
    "numbered_steps": re.compile(r"(?m)^\s*\d+[.)]\s+\S"),
    "version": re.compile(r"\bv?\d+\.\d+(\.\d+)+\b"),
    "usage_question": re.compile(r"\b(how (do|can|to|should) (i|we|you)|is (it|there) (possible|a way)|"
                                 r"what is the (best|right) way|any (way|idea))\b", re.I),
    "image": re.compile(r"\[image\]"),
    "link": re.compile(r"https?://"),
}
SHORT_WORDS = 30
NAMES = ["log_words", "short", *SIGNALS]

# Regras fixas: +1 aumenta a chance de "sem ação", -1 diminui. Escolhidas a priori:
# texto curto e pergunta de uso sugerem fechamento sem ação; evidência técnica sugere ação.
RULE_WEIGHTS = {"short": 1, "usage_question": 1, "stack_trace": -1, "code_block": -1,
                "numbered_steps": -1, "version": -1}


def signals(text):
    words = len(text.split())
    out = {"log_words": math.log1p(words), "short": int(words < SHORT_WORDS)}
    out.update({name: int(bool(rx.search(text))) for name, rx in SIGNALS.items()})
    return out


def matrix(texts):
    return np.array([[signals(t)[n] for n in NAMES] for t in texts], dtype=float)


def rule_score(text):
    """Pontuação das regras fixas: quanto maior, mais provável "sem ação". Sem nenhum parâmetro aprendido."""
    s = signals(text)
    return sum(w * s[name] for name, w in RULE_WEIGHTS.items())
