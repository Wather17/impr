import subprocess
import sys


def test_interactive_mode_stops_after_invalid_epub(tmp_path):
    invalid_epub = tmp_path / "invalid.epub"
    invalid_epub.write_text("não é um arquivo EPUB", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "epub_to_print_pdf.py"],
        input=f"{invalid_epub}\n",
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Erro ao ler os capítulos do livro" in result.stdout
    assert "Selecione o(s) capítulo(s) que você deseja imprimir" not in result.stdout
