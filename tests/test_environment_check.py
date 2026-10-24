import pytest

import epub_to_print_pdf as module


def make_project_directories(project_dir):
    (project_dir / "epub").mkdir(parents=True)
    (project_dir / "pdf").mkdir()


def checks_by_name(checks):
    return {name: (is_ok, detail) for name, is_ok, detail in checks}


def test_check_environment_reports_ready_environment(tmp_path, monkeypatch):
    make_project_directories(tmp_path)
    monkeypatch.setattr(module, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(
        module,
        "normalize_browser_command",
        lambda _: ["/usr/bin/chromium"],
    )

    checks = checks_by_name(module.check_environment())

    assert all(is_ok for is_ok, _ in checks.values())
    assert checks["Navegador Chromium"] == (
        True,
        "comando: /usr/bin/chromium",
    )


def test_check_environment_reports_missing_browser(tmp_path, monkeypatch):
    make_project_directories(tmp_path)
    monkeypatch.setattr(module, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(
        module,
        "normalize_browser_command",
        lambda _: (_ for _ in ()).throw(RuntimeError("navegador ausente")),
    )

    checks = checks_by_name(module.check_environment())

    assert checks["Navegador Chromium"] == (False, "navegador ausente")
    assert all(
        is_ok
        for name, (is_ok, _) in checks.items()
        if name != "Navegador Chromium"
    )


def test_report_environment_check_handles_missing_pypdf_without_traceback(
    tmp_path, monkeypatch, capsys
):
    make_project_directories(tmp_path)
    monkeypatch.setattr(module, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(
        module,
        "PYPDF_IMPORT_ERROR",
        ModuleNotFoundError("No module named 'pypdf'"),
    )
    monkeypatch.setattr(
        module,
        "normalize_browser_command",
        lambda _: ["/usr/bin/chromium"],
    )

    status = module.report_environment_check()
    output = capsys.readouterr().out

    assert status == 1
    assert "[ERRO] pypdf" in output
    assert "reinstale requirements.txt" in output
    assert "Traceback" not in output


def test_check_environment_reports_missing_directories_without_creating_them(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(module, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(
        module,
        "normalize_browser_command",
        lambda _: ["/usr/bin/chromium"],
    )

    checks = checks_by_name(module.check_environment())

    assert checks["Diretório epub"][0] is False
    assert checks["Diretório pdf"][0] is False
    assert not (tmp_path / "epub").exists()
    assert not (tmp_path / "pdf").exists()


def test_main_check_exits_without_starting_interactive_mode(tmp_path, monkeypatch):
    make_project_directories(tmp_path)
    monkeypatch.setattr(module, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(
        module,
        "normalize_browser_command",
        lambda _: ["/usr/bin/chromium"],
    )
    monkeypatch.setattr(module.sys, "argv", ["epub_to_print_pdf.py", "--check"])

    with pytest.raises(SystemExit) as error:
        module.main()

    assert error.value.code == 0
    assert not list(tmp_path.glob("*.pdf"))
