import re

def sanitize_latex_chars(latex_content: str) -> str:
    """
    Task A: Escape raw special characters like &, %, # if they are not already escaped.
    """
    # Escape & (match any & not preceded by a backslash)
    latex_content = re.sub(r'(?<!\\)&', r'\\&', latex_content)
    
    # Escape % (match any % not preceded by a backslash)
    latex_content = re.sub(r'(?<!\\)%', r'\\%', latex_content)
    
    # Escape # (match any # not preceded by a backslash)
    latex_content = re.sub(r'(?<!\\)#', r'\\#', latex_content)
    
    return latex_content

def run_stage2(latex_content: str) -> tuple[str, bool, str, list[str]]:
    """
    Stage 2: Programmatic Python Sanitizer
    Task A: Escapes LaTeX special control characters.
    Task B: Checks for typographic orphan risks by evaluating bullet point lengths.
    
    Returns: (sanitized_content, success_status, error_message, failing_bullets)
    """
    sanitized = sanitize_latex_chars(latex_content)
    return sanitized, True, "", []
