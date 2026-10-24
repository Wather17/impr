import zipfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter

import epub_to_print_pdf as module


def create_minimal_epub(path):
    container = """<?xml version="1.0" encoding="UTF-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    opf = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0">
  <manifest>
    <item id="chapter" href="Text/chapter.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapter"/>
  </spine>
</package>
"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr("META-INF/container.xml", container)
        archive.writestr("OEBPS/content.opf", opf)
        archive.writestr(
            "OEBPS/Text/chapter.xhtml",
            "<html><body><p>Capítulo</p></body></html>",
        )


def test_run_pipeline_uses_project_pdf_directory_for_automatic_output(
    tmp_path, monkeypatch
):
    project_dir = tmp_path / "project"
    epub_path = tmp_path / "Book.epub"
    create_minimal_epub(epub_path)

    def fake_convert_html_to_pdf(html_path, pdf_path, browser_command, browser_work_dir=None):
        writer = PdfWriter()
        writer.add_blank_page(width=420, height=595)
        with Path(pdf_path).open("wb") as output:
            writer.write(output)

    monkeypatch.setattr(module, "PROJECT_DIR", project_dir)
    monkeypatch.setattr(module, "normalize_browser_command", lambda _: ["fake-browser"])
    monkeypatch.setattr(module, "convert_html_to_pdf", fake_convert_html_to_pdf)

    module.run_pipeline(
        epub_path=str(epub_path),
        output_pdf_path=None,
        font_size="12pt",
        margin="15mm",
        font_family="serif",
        mode="cut-stack",
        signature_size=16,
        browser_path="/fake/browser",
    )

    generated = list((project_dir / "pdf").glob("*.pdf"))
    assert [path.name for path in generated] == ["Book_Completo.pdf"]
    assert len(PdfReader(str(generated[0])).pages) == 2
