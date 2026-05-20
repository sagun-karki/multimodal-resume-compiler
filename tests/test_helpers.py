from utils.helpers import clean_generated_tex


def test_clean_generated_tex_replaces_validatedbullet():
    content = r"""\begin{itemize}\validatedbullet{Did X with {nested} data}\end{itemize}"""
    cleaned = clean_generated_tex(content)
    assert "\\validatedbullet" not in cleaned
    assert "\\item Did X with {nested} data" in cleaned
