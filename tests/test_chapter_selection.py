import pytest

import epub_to_print_pdf as module


def test_parse_chapters_selection_supports_ranges_and_individual_pages():
    assert module.parse_chapters_selection("1-3,5", 5) == [0, 1, 2, 4]


def test_parse_chapters_selection_blank_uses_all_chapters():
    assert module.parse_chapters_selection("", 3) == [0, 1, 2]


def test_parse_chapters_selection_normalizes_reversed_ranges():
    assert module.parse_chapters_selection("5-2", 5) == [1, 2, 3, 4]


@pytest.mark.parametrize("selection", ["999", "999-1000", "4-999", "1,999", "0-2", ","])
def test_parse_chapters_selection_rejects_invalid_components(selection):
    with pytest.raises(ValueError, match="Filtro de capítulos inválido"):
        module.parse_chapters_selection(selection, 5)


def test_run_pipeline_rejects_invalid_filter_before_browser(tmp_path, monkeypatch):
    context = module.EPUBContext(
        temp_dir=str(tmp_path / "epub-work"),
        opf_rel_path="content.opf",
        chapter_hrefs=["chapter-1.xhtml", "chapter-2.xhtml"],
        toc_map={},
    )
    output_path = tmp_path / "output.pdf"

    monkeypatch.setattr(
        module,
        "normalize_browser_command",
        lambda _: pytest.fail("o navegador não deveria ser localizado"),
    )

    with pytest.raises(ValueError, match="Filtro de capítulos inválido"):
        module.run_pipeline(
            epub_path="book.epub",
            output_pdf_path=str(output_path),
            font_size="12pt",
            margin="15mm",
            font_family="serif",
            mode="cut-stack",
            signature_size=16,
            chapters_filter="999-1000",
            browser_path="/fake/browser",
            epub_context=context,
        )

    assert not output_path.exists()


def test_main_reports_invalid_cli_filter_without_generating_pdf(tmp_path, monkeypatch, capsys):
    project_dir = tmp_path / "project"
    epub_path = tmp_path / "book.epub"
    epub_path.touch()
    context = module.EPUBContext(
        temp_dir=str(tmp_path / "epub-work"),
        opf_rel_path="content.opf",
        chapter_hrefs=["chapter-1.xhtml", "chapter-2.xhtml"],
        toc_map={},
    )

    monkeypatch.setattr(module, "PROJECT_DIR", project_dir)
    monkeypatch.setattr(module, "prepare_epub", lambda _: context)
    monkeypatch.setattr(
        module.sys,
        "argv",
        ["epub_to_print_pdf.py", str(epub_path), "-c", "999-1000"],
    )

    with pytest.raises(SystemExit) as error:
        module.main()

    assert error.value.code == 1
    assert "Filtro de capítulos inválido" in capsys.readouterr().out
    assert not list((project_dir / "pdf").glob("*.pdf"))
