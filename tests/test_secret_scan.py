from pathlib import Path

from scripts.scan_secrets import main, scan_path, scan_text


def _fake_telegram_token() -> str:
    return "123456789" + ":" + "A" * 35


def test_blocks_fake_telegram_token(tmp_path: Path) -> None:
    target = tmp_path / "leak.py"
    target.write_text(f'BOT = "{_fake_telegram_token()}"\n', encoding="utf-8")
    assert main([str(target)]) == 1


def test_blocks_service_account_json(tmp_path: Path) -> None:
    target = tmp_path / "sa.json"
    header = "-" * 5 + "BEGIN " + "PRIVATE KEY" + "-" * 5
    target.write_text('{"private_key": "' + header + '\\nabc"}', encoding="utf-8")
    assert "gcp_service_account_key" in scan_path(target)[0]


def test_blocks_generic_assignment() -> None:
    assert scan_text('api_key = "' + "q7Wm2" * 4 + '"')


def test_allows_placeholders() -> None:
    assert scan_text("TELEGRAM_INTAKE_BOT_TOKEN=<from-secret-manager>") == []
    assert scan_text('token = "CHANGE_ME_before_use_1234"') == []


def test_blocks_env_file_but_not_example(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("X=1\n", encoding="utf-8")
    example = tmp_path / ".env.example"
    example.write_text("X=<value>\n", encoding="utf-8")
    assert scan_path(env) == ["env_file"]
    assert scan_path(example) == []


def test_blocks_red_paths(tmp_path: Path) -> None:
    red = tmp_path / "real_inputs" / "a.csv"
    red.parent.mkdir()
    red.write_text("x\n", encoding="utf-8")
    assert scan_path(red) == ["red_path"]


def test_clean_repo_files_pass() -> None:
    root = Path(__file__).resolve().parents[1]
    files = [p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts and ".venv" not in p.parts]
    files = [p for p in files if p.name != "test_secret_scan.py"]
    assert main([str(p) for p in files]) == 0
