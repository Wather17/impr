from epub_to_print_pdf import consolidate_chapters


def test_consolidate_chapters_preserves_stylesheets_and_rebases_resources(tmp_path):
    chapter_dir = tmp_path / "OEBPS" / "Text"
    styles_dir = tmp_path / "OEBPS" / "Styles"
    images_dir = tmp_path / "OEBPS" / "Images"
    chapter_dir.mkdir(parents=True)
    styles_dir.mkdir(parents=True)
    images_dir.mkdir(parents=True)

    styles_dir.joinpath("book.css").write_text(
        ".chapter-title { font-weight: bold; }", encoding="utf-8"
    )
    images_dir.joinpath("cover.png").write_bytes(b"png")

    chapter = """<!doctype html>
<html>
<head>
  <style>
    p { color: red; }
    .hero { background: url("../Images/cover.png"); }
  </style>
  <link rel="stylesheet" media="print" href="../Styles/book.css">
</head>
<body><p>Capítulo 1</p><img src="../Images/cover.png"></body>
</html>"""
    chapter_dir.joinpath("chapter.xhtml").write_text(chapter, encoding="utf-8")
    chapter_dir.joinpath("chapter-2.xhtml").write_text(
        "<html><head></head><body><p>Capítulo 2</p></body></html>",
        encoding="utf-8",
    )

    output = tmp_path / "consolidated.html"
    consolidate_chapters(
        temp_dir=str(tmp_path),
        opf_rel_path="OEBPS/content.opf",
        chapter_hrefs=["Text/chapter.xhtml", "Text/chapter-2.xhtml"],
        output_html_path=str(output),
        font_size="12pt",
        margin="15mm",
        font_family="serif",
    )

    result = output.read_text(encoding="utf-8")
    assert "p { color: red; }" in result
    assert 'href="OEBPS/Styles/book.css"' in result
    assert 'url("OEBPS/Images/cover.png")' in result
    assert 'src="OEBPS/Images/cover.png"' in result
    assert "Capítulo 1" in result
    assert "Capítulo 2" in result
