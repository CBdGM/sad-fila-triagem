import yaml

from outcomes.__main__ import main

from .test_run import GraphSession, closed_issue, write_issues


def write_cfg(tmp_path):
    path = tmp_path / "repos.yaml"
    path.write_text(yaml.safe_dump({"schema_version": 1, "model": "jev-1.14.0",
                                    "first_run": {"open_max": 5, "closed_months": 1},
                                    "repos": [{"repo": "o/r", "closing_labels": {"duplicate": "duplicate"}}]}))
    return path


def test_cli_grava_e_mostra_resumo_da_fase_0(tmp_path, capsys):
    data = tmp_path / "data"
    write_issues(data, [closed_issue(1), closed_issue(2, reason="duplicate")])
    code = main(["--config", str(write_cfg(tmp_path)), "--data-dir", str(data)],
                make_session=lambda: GraphSession())
    err = capsys.readouterr().err
    assert code == 0
    assert "2 desfechos novos" in err
    assert "1 sem ação, 1 com ação" in err and "sem ação = 50.0%" in err


def test_cli_sem_coletor_falha_com_mensagem(tmp_path, capsys):
    code = main(["--config", str(write_cfg(tmp_path)), "--data-dir", str(tmp_path / "vazio")],
                make_session=lambda: GraphSession())
    assert code == 1
    assert "rode o coletor" in capsys.readouterr().err
