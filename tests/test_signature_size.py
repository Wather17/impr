import pytest
from pypdf import PdfReader, PdfWriter

from epub_to_print_pdf import impose_pdf, validate_signature_size


@pytest.mark.parametrize("signature_size", [4, 8, 16, 32])
def test_validate_signature_size_accepts_positive_multiples(signature_size):
    validate_signature_size(signature_size)


@pytest.mark.parametrize("signature_size", [0, -4, 2, 6])
def test_validate_signature_size_rejects_invalid_values(signature_size):
    with pytest.raises(ValueError, match="múltiplo de 4 maior que zero"):
        validate_signature_size(signature_size)


def test_impose_booklet_rejects_zero_signature_size(tmp_path):
    input_pdf = tmp_path / "input.pdf"
    output_pdf = tmp_path / "output.pdf"

    writer = PdfWriter()
    writer.add_blank_page(width=420, height=595)
    with input_pdf.open("wb") as output:
        writer.write(output)

    with pytest.raises(ValueError, match="múltiplo de 4 maior que zero"):
        impose_pdf(str(input_pdf), str(output_pdf), "booklet", signature_size=0)

    assert not output_pdf.exists()


def test_impose_booklet_accepts_valid_signature_size(tmp_path):
    input_pdf = tmp_path / "input.pdf"
    output_pdf = tmp_path / "output.pdf"

    writer = PdfWriter()
    writer.add_blank_page(width=420, height=595)
    with input_pdf.open("wb") as output:
        writer.write(output)

    impose_pdf(str(input_pdf), str(output_pdf), "booklet", signature_size=4)

    assert len(PdfReader(str(output_pdf)).pages) == 2
