import pytest
from pypdf import PdfReader, PdfWriter

from epub_to_print_pdf import impose_pdf


def make_pdf(path, page_count):
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=420, height=595)
    with path.open("wb") as output:
        writer.write(output)


@pytest.mark.parametrize("mode", ["cut-stack", "sequencial", "booklet"])
def test_impose_pdf_supports_all_modes(tmp_path, mode):
    input_pdf = tmp_path / f"{mode}-input.pdf"
    output_pdf = tmp_path / f"{mode}-output.pdf"
    make_pdf(input_pdf, 4)

    impose_pdf(
        str(input_pdf),
        str(output_pdf),
        mode,
        signature_size=4,
    )

    reader = PdfReader(str(output_pdf))
    assert len(reader.pages) == 2
    for page in reader.pages:
        assert float(page.mediabox.width) == pytest.approx(841.89)
        assert float(page.mediabox.height) == pytest.approx(595.275)
