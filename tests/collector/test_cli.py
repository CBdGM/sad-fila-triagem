import json

import yaml

from collector.__main__ import main

from .conftest import API, FakeResponse, FakeSession, issue, paged, params_of


def handler(url, params):
    p = params_of(url, params)
    if url.startswith(f"{API}/repos/") and not url.split("?")[0].endswith("/issues"):
        return FakeResponse(body={"full_name": url.removeprefix(f"{API}/repos/")})
    items = [issue(1), issue(2, pr=True)] if p["state"] == "open" else []
    return paged(items, url.split("?")[0], p)


def write_cfg(tmp_path, repos):
    path = tmp_path / "repos.yaml"
    path.write_text(yaml.safe_dump({"schema_version": 1, "model": "jev-1.14.0",
                                    "first_run": {"open_max": 5, "closed_months": 1},
                                    "repos": repos}))
    return path


def test_coleta_so_os_habilitados_e_imprime_mudancas(tmp_path, capsys):
    cfg = write_cfg(tmp_path, [{"repo": "o/a", "closing_labels": {"x": "other"}},
                               {"repo": "o/b", "closing_labels": {"x": "other"}, "enabled": False}])
    s = FakeSession(handler)
    code = main(["--config", str(cfg), "--data-dir", str(tmp_path / "data"), "--changes"],
                make_session=lambda: s)
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out == {"o/a": {"new": [1], "edited": [], "closed": []}}
    assert not any("/repos/o/b" in url for url, _ in s.calls)
    assert (tmp_path / "data" / "o__a" / "issues.jsonl").exists()


def test_repo_fora_da_config_da_erro(tmp_path, capsys):
    cfg = write_cfg(tmp_path, [{"repo": "o/a", "closing_labels": {"x": "other"}}])
    assert main(["--config", str(cfg), "--repo", "o/z"], make_session=lambda: None) == 2
    assert "não está" in capsys.readouterr().err


def test_config_invalida_da_erro(tmp_path, capsys):
    cfg = tmp_path / "repos.yaml"
    cfg.write_text("schema_version: 1\nmodel: jev-latest\n")
    assert main(["--config", str(cfg)], make_session=lambda: None) == 2
    assert "contrato" in capsys.readouterr().err


def test_changes_em_arquivo_e_resumo_com_uso_da_api(tmp_path, capsys):
    cfg = write_cfg(tmp_path, [{"repo": "o/a", "closing_labels": {"x": "other"}}])
    out_file = tmp_path / "mudancas.json"
    code = main(["--config", str(cfg), "--data-dir", str(tmp_path / "data"), "--changes", str(out_file)],
                make_session=lambda: FakeSession(handler))
    assert code == 0
    assert json.loads(out_file.read_text()) == {"o/a": {"new": [1], "edited": [], "closed": []}}
    captured = capsys.readouterr()
    assert captured.out == ""                      # nada despejado no terminal
    assert "requisições" in captured.err and "abertas" in captured.err
