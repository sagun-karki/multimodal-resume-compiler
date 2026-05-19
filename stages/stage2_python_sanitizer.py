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
    
    # Find all occurrences of \validatedbullet{...}
    # Matches nested curly braces up to one level
    bullet_pattern = re.compile(r'\\validatedbullet\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}')
    bullets = bullet_pattern.findall(sanitized)
    
    failing_bullets = []
    for bullet in bullets:
        bullet_len = len(bullet)
        # Typographic check: if length falls in risk zone (90-112 chars), flag a potential orphan
        if 90 <= bullet_len <= 112:
            failing_bullets.append(bullet)
            
    if failing_bullets:
        bullet_list_str = "\n- ".join([f'"{b[:40]}..." (length {len(b)})' for b in failing_bullets])
        err_msg = (
            f"STATUS: TYPOGRAPHY_ERROR\n"
            f"CRITIQUE: The following bullet points have lengths falling in the risky zone of 90-112 characters:\n"
            f"- {bullet_list_str}\n"
            f"This is highly likely to wrap a single dangling word onto a new line (orphan). Please shorten or lengthen them to align spacing."
        )
        return sanitized, False, err_msg, failing_bullets
            
    return sanitized, True, "", []
