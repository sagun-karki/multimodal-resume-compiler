from utils.helpers import clean_generated_tex
from agents.resume_writer import apply_atomic_edit


def test_clean_generated_tex_replaces_validatedbullet():
    content = r"""\begin{itemize}\validatedbullet{Did X with {nested} data}\end{itemize}"""
    cleaned = clean_generated_tex(content)
    assert "\\validatedbullet" not in cleaned
    assert "\\item Did X with {nested} data" in cleaned


def test_apply_atomic_edit():
    resume = {
        "skills": {
            "Languages": ["Python", "SQL"]
        },
        "experience": [
            {
                "bullets": ["Did A", "Did B"]
            }
        ]
    }
    
    # Modify bullet in list
    assert apply_atomic_edit(resume, {
        "path": "experience[0].bullets[1]",
        "replacement": "Did B (improved)"
    })
    assert resume["experience"][0]["bullets"][1] == "Did B (improved)"
    
    # Modify skill in list
    assert apply_atomic_edit(resume, {
        "path": "skills.Languages[0]",
        "replacement": "Python3"
    })
    assert resume["skills"]["Languages"][0] == "Python3"

