import os
import shutil
import subprocess
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
INSTALLER = PROJECT_DIR / "scripts" / "install-linux.sh"


def run_installer(project_dir, home_dir, *arguments, fake_bin=None):
    environment = os.environ.copy()
    environment["HOME"] = str(home_dir)
    environment["XDG_BIN_HOME"] = str(home_dir / ".local" / "bin")
    if fake_bin is not None:
        environment["PATH"] = f"{fake_bin}{os.pathsep}{environment['PATH']}"

    return subprocess.run(
        ["bash", str(project_dir / "scripts" / "install-linux.sh"), *arguments],
        cwd="/tmp",
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def create_fake_python(fake_bin):
    fake_python = fake_bin / "python3"
    fake_python.write_text(
        """#!/usr/bin/env bash
set -Eeuo pipefail

if [[ \"${1:-}\" == \"-c\" ]]; then
    exit 0
fi

if [[ \"${1:-}\" == \"-m\" && \"${2:-}\" == \"venv\" ]]; then
    venv_dir=\"$3\"
    mkdir -p \"$venv_dir/bin\"
    cat > \"$venv_dir/bin/python\" <<'PYTHON'
#!/usr/bin/env bash
set -Eeuo pipefail

if [[ \"${1:-}\" == \"-m\" && \"${2:-}\" == \"pip\" ]]; then
    exit 0
fi

if [[ \"${1:-}\" == \"-m\" && \"${2:-}\" == \"ensurepip\" ]]; then
    exit 0
fi

exit 0
PYTHON
    chmod 755 \"$venv_dir/bin/python\"
    exit 0
fi

exit 0
"""
    )
    fake_python.chmod(0o755)


def copy_installer_project(tmp_path):
    project_dir = tmp_path / "project"
    (project_dir / "scripts").mkdir(parents=True)
    shutil.copy2(INSTALLER, project_dir / "scripts" / INSTALLER.name)
    (project_dir / "requirements.txt").write_text("fake-package==1.0\n")
    return project_dir


def test_installer_has_valid_shell_syntax_and_help_output():
    syntax = subprocess.run(
        ["bash", "-n", str(INSTALLER)],
        capture_output=True,
        text=True,
        check=False,
    )
    help_result = subprocess.run(
        ["bash", str(INSTALLER), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert syntax.returncode == 0, syntax.stderr
    assert help_result.returncode == 0, help_result.stderr
    assert "--dev" in help_result.stdout
    assert "--uninstall" in help_result.stdout


def test_installer_is_idempotent_and_uninstall_preserves_project_data(tmp_path):
    project_dir = copy_installer_project(tmp_path)
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    create_fake_python(fake_bin)
    home_dir = tmp_path / "home"

    first_install = run_installer(
        project_dir,
        home_dir,
        "--dev",
        fake_bin=fake_bin,
    )
    assert first_install.returncode == 0, first_install.stderr

    launcher = home_dir / ".local" / "bin" / "impr"
    assert launcher.is_file()
    assert launcher.stat().st_mode & 0o111
    assert str(project_dir) in launcher.read_text()
    assert (project_dir / ".venv" / "bin" / "python").is_file()
    assert (project_dir / "epub").is_dir()
    assert (project_dir / "pdf").is_dir()

    epub_data = project_dir / "epub" / "keep.epub"
    pdf_data = project_dir / "pdf" / "keep.pdf"
    epub_data.write_text("preserve")
    pdf_data.write_text("preserve")

    second_install = run_installer(
        project_dir,
        home_dir,
        "--update",
        fake_bin=fake_bin,
    )
    assert second_install.returncode == 0, second_install.stderr
    assert epub_data.read_text() == "preserve"
    assert pdf_data.read_text() == "preserve"

    uninstall = run_installer(
        project_dir,
        home_dir,
        "--uninstall",
        fake_bin=fake_bin,
    )
    assert uninstall.returncode == 0, uninstall.stderr
    assert not launcher.exists()
    assert (project_dir / ".venv").is_dir()
    assert epub_data.exists()
    assert pdf_data.exists()


def test_installer_does_not_overwrite_unmanaged_launcher(tmp_path):
    project_dir = copy_installer_project(tmp_path)
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    create_fake_python(fake_bin)
    home_dir = tmp_path / "home"
    launcher = home_dir / ".local" / "bin" / "impr"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("#!/usr/bin/env bash\necho user-owned\n")

    result = run_installer(project_dir, home_dir, fake_bin=fake_bin)

    assert result.returncode != 0
    assert "já existe e não foi criado por este instalador" in result.stderr
    assert launcher.read_text() == "#!/usr/bin/env bash\necho user-owned\n"
