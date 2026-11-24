import yaml

from evaluator import jev
from evaluator.__main__ import main

from .fakes import GitHubSession, JevSession, rec, texts_of, write


def cfg(tmp_path, model="jev-1.14.0"):
    path = tmp_path / "repos.yaml"
    path.write_text(yaml.safe_dump({"schema_version": 1, "model": model,
                                    "first_run": {"open_max": 5, "closed_months": 1},
                                    "repos": [{"repo": "o/r", "closing_labels": {"duplicate": "duplicate"}}]}))
    return path


def test_cli_avalia_e_mostra_tokens(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("TYPESAFE_BASE_URL", "https://x")
    records = [rec(1), rec(2)]
    write(tmp_path / "data", records)
    code = main(["--mode", "daily", "--config", str(cfg(tmp_path)), "--data-dir", str(tmp_path / "data")],
                make_github=lambda: GitHubSession(texts_of(records)), make_jev=JevSession)
    assert code == 0
    assert "2 previsões novas (640 tokens, média 320 por issue)" in capsys.readouterr().err


def test_cli_recusa_jev_latest(tmp_path, capsys):
    code = main(["--mode", "daily", "--config", str(cfg(tmp_path, "jev-latest"))], make_jev=JevSession)
    assert code == 2 and "jev-latest" in capsys.readouterr().err  # o contrato já recusa


def test_cli_sem_chave(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr("evaluator.__main__.load_dotenv", lambda: None)
    code = main(["--mode", "daily", "--config", str(cfg(tmp_path))], make_jev=jev.session)
    assert code == 2 and "TYPESAFE_API_KEY" in capsys.readouterr().err
