from epub_to_print_pdf import parse_chapters_selection


def test_parse_chapters_selection_supports_ranges_and_individual_pages():
    assert parse_chapters_selection("1-3,5", 5) == [0, 1, 2, 4]


def test_parse_chapters_selection_blank_uses_all_chapters():
    assert parse_chapters_selection("", 3) == [0, 1, 2]


def test_parse_chapters_selection_never_returns_out_of_range_indices():
    selected = parse_chapters_selection("999", 5)
    assert all(0 <= index < 5 for index in selected)
