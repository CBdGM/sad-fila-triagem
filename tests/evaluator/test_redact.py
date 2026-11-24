import pytest

from evaluator.redact import MARK, redact

# Tokens falsos montados em tempo de execução, para o arquivo não conter nada com cara de segredo.
FAKES = {
    "github": "ghp_" + "a1B2" * 9,
    "github_pat": "github_pat_" + "x9_" * 25,
    "azure_novo": "Q" * 76 + "AZDO" + "abcd",
    "azure_52": "abcdefghijklmnopqrstuvwxyz234567" + "abcdefghijklmnopqrst",
    "aws": "AKIA" + "ABCDEFGH23456789",
    "openai": "sk-" + "proj_" + "Z" * 30,
    "slack": "xoxb-" + "123456789012-abc",
    "google": "AIza" + "S" * 35,
}


@pytest.mark.parametrize("name", FAKES)
def test_troca_cada_padrao(name):
    text = f"meu token é {FAKES[name]} e quebrou"
    out, n = redact(text)
    assert n == 1 and out == f"meu token é {MARK} e quebrou"


def test_texto_comum_nao_muda():
    text = "Crash on start: TypeError at line 52 in extension host (v1.107.0, sha 8a14f0cc1b08d5)"
    assert redact(text) == (text, 0)
    assert redact("") == ("", 0) and redact(None) == (None, 0)
