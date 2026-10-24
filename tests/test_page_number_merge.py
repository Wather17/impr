import pytest
from pypdf import PdfReader, PdfWriter

from epub_to_print_pdf import merge_page_numbers


def make_pdf(path, page_count):
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=420, height=595)
    with path.open("wb") as output:
        writer.write(output)


def test_merge_page_numbers_preserves_all_matching_pages(tmp_path):
    content_path = tmp_path / "content.pdf"
    numbers_path = tmp_path / "numbers.pdf"
    make_pdf(content_path, 3)
    make_pdf(numbers_path, 3)

    writer = merge_page_numbers(
        PdfReader(str(content_path)),
        PdfReader(str(numbers_path)),
    )

    assert len(writer.pages) == 3


@pytest.mark.parametrize("content_count,number_count", [(3, 2), (2, 3)])
def test_merge_page_numbers_rejects_mismatched_counts(
    tmp_path, content_count, number_count
):
    content_path = tmp_path / "content.pdf"
    numbers_path = tmp_path / "numbers.pdf"
    make_pdf(content_path, content_count)
    make_pdf(numbers_path, number_count)

    with pytest.raises(RuntimeError, match="diverge"):
        merge_page_numbers(
            PdfReader(str(content_path)),
            PdfReader(str(numbers_path)),
        )
