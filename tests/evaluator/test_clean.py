from evaluator.clean import CLEANING_VERSION, clean_issue


def test_tira_template_comando_de_bot_e_prefixo_do_titulo():
    body = "### What happened?\nIt crashes\n<!-- dica do template -->\n/kind bug\n- [x] I searched\n_No response_"
    assert clean_issue({"title": "[Bug] Crash on start", "body": body}) == "Crash on start\n\nIt crashes"


def test_encurta_bloco_de_codigo_longo():
    code = "\n".join(str(i) for i in range(30))
    out = clean_issue({"title": "t", "body": f"```\n{code}\n```"})
    assert "[... 20 more lines]" in out and "\n9\n" in out and "\n10\n" not in out


def test_corpo_vazio_fica_so_o_titulo():
    assert clean_issue({"title": "Só título", "body": ""}) == "Só título"
    assert CLEANING_VERSION == "clean-1"
