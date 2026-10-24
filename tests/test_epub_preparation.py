import shutil
import zipfile
from pathlib import Path

from epub_to_print_pdf import prepare_epub


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
        archive.writestr(
            "OEBPS/content.opf",
            opf,
        )
        archive.writestr(
            "OEBPS/Text/chapter.xhtml",
            "<html><body><p>Capítulo</p></body></html>",
        )


def test_prepare_epub_extracts_and_parses_once(tmp_path, monkeypatch):
    epub_path = tmp_path / "book.epub"
    create_minimal_epub(epub_path)
    extraction_calls = []
    original_extractall = zipfile.ZipFile.extractall

    def track_extractall(archive, destination, *args, **kwargs):
        extraction_calls.append(destination)
        return original_extractall(archive, destination, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "extractall", track_extractall)
    context = prepare_epub(epub_path)
    try:
        assert extraction_calls == [context.temp_dir]
        assert context.chapter_hrefs == ["Text/chapter.xhtml"]
        assert not (tmp_path / "OEBPS" / "content.opf").exists()
        assert Path(context.temp_dir, "OEBPS/Text/chapter.xhtml").is_file()
    finally:
        shutil.rmtree(context.temp_dir, ignore_errors=True)
