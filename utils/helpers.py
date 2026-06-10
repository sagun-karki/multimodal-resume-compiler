"""Shared utilities for the resume optimization pipeline."""
import os
import re
from typing import Optional


def get_api_key() -> str:
    """Get Gemini API key from environment variables."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY must be set in the environment.")
    return api_key


def track_tokens(response, tracker, model_type: str = "text"):
    """Extract and track tokens from a Gemini API response."""
    in_tokens = 0
    out_tokens = 0
    if response.usage_metadata:
        in_tokens = response.usage_metadata.prompt_token_count
        out_tokens = response.usage_metadata.candidates_token_count
    tracker.track(model_type, in_tokens, out_tokens)


def extract_bullets(latex_content: str) -> list[str]:
    """
    Parses out the exact content strings inside all \\validatedbullet{...} macros.
    Handles nested curly braces up to arbitrary depths and optional bracket path parameters.
    """
    bullets = []
    pattern = r'\\validatedbullet'
    for match in re.finditer(pattern, latex_content):
        start = match.end()
        # Skip optional path parameter in brackets if present
        if start < len(latex_content) and latex_content[start] == '[':
            brace_count = 1
            i = start + 1
            while i < len(latex_content) and brace_count > 0:
                if latex_content[i] == '[':
                    brace_count += 1
                elif latex_content[i] == ']':
                    brace_count -= 1
                i += 1
            start = i
            
        # Find opening curly brace
        while start < len(latex_content) and latex_content[start] != '{':
            start += 1
        if start < len(latex_content):
            start += 1
            
        brace_count = 1
        i = start
        while i < len(latex_content) and brace_count > 0:
            if latex_content[i] == '{':
                brace_count += 1
            elif latex_content[i] == '}':
                brace_count -= 1
            i += 1
        if brace_count == 0:
            bullet_text = latex_content[start:i-1]
            if bullet_text not in bullets:
                bullets.append(bullet_text)
    return bullets


def extract_bullets_with_paths(latex_content: str) -> list[tuple[str, str]]:
    """
    Parses out the exact (path_id, content) tuple inside all \\validatedbullet[path_id]{content} macros.
    Handles nested curly braces up to arbitrary depths.
    """
    pairs = []
    pattern = r'\\validatedbullet'
    for match in re.finditer(pattern, latex_content):
        start = match.end()
        path_id = ""
        # Find optional path parameter in brackets
        if start < len(latex_content) and latex_content[start] == '[':
            brace_count = 1
            i = start + 1
            while i < len(latex_content) and brace_count > 0:
                if latex_content[i] == '[':
                    brace_count += 1
                elif latex_content[i] == ']':
                    brace_count -= 1
                i += 1
            path_id = latex_content[start+1:i-1]
            if path_id.startswith('{') and path_id.endswith('}'):
                path_id = path_id[1:-1]
            start = i
            
        # Find opening curly brace
        while start < len(latex_content) and latex_content[start] != '{':
            start += 1
        if start < len(latex_content):
            start += 1
            
        brace_count = 1
        i = start
        while i < len(latex_content) and brace_count > 0:
            if latex_content[i] == '{':
                brace_count += 1
            elif latex_content[i] == '}':
                brace_count -= 1
            i += 1
        if brace_count == 0:
            bullet_text = latex_content[start:i-1]
            pairs.append((path_id, bullet_text))
    return pairs


def clean_generated_tex(content: str) -> str:
    """Replace all \\validatedbullet{...} with \\item ..."""
    result = []
    idx = 0
    target = r'\validatedbullet'
    while idx < len(content):
        next_pos = content.find(target, idx)
        if next_pos == -1:
            result.append(content[idx:])
            break
        
        result.append(content[idx:next_pos])
        
        # Check if there is an optional [path] argument and skip it
        start = next_pos + len(target)
        if start < len(content) and content[start] == '[':
            brace_count = 1
            i = start + 1
            while i < len(content) and brace_count > 0:
                if content[i] == '[':
                    brace_count += 1
                elif content[i] == ']':
                    brace_count -= 1
                i += 1
            start = i
            
        # Find opening curly brace
        while start < len(content) and content[start] != '{':
            start += 1
        if start < len(content):
            start += 1
            
        brace_count = 1
        i = start
        while i < len(content) and brace_count > 0:
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
            i += 1
            
        if brace_count == 0:
            bullet_text = content[start:i-1]
            result.append(f'\\item {bullet_text}')
            idx = i
        else:
            result.append(content[next_pos:start])
            idx = start
            
    return "".join(result)


def clean_latex(main_content: str, gen_content: str) -> str:
    """Merge compiled blocks, strip debug helper macros, and flatten custom bullets."""
    # 1. Merge gen_content into main_content replacing the \input statement
    merged = re.sub(r'\\input\{.*?generated_data\.tex\}', lambda m: gen_content, main_content)
    if merged == main_content:
        merged = main_content.replace('\\input{resources/generated_data.tex}', gen_content)
        
    # 2. Remove \newsavebox{\linebox}
    merged = merged.replace('\\newsavebox{\\linebox}', '')
    
    # 3. Remove \validatedbullet macro definition
    macro_pattern = r'%\s*Custom wrapping helper.*?\n\\newcommand\{\\validatedbullet\}.*?%\s*Render bullet\s*\n\}'
    merged = re.sub(macro_pattern, '', merged, flags=re.DOTALL)
    
    # Also handle the macro if it doesn't match the exact regex above (fallback)
    macro_fallback = r'\\newcommand\{\\validatedbullet\}.*?\}'
    merged = re.sub(macro_fallback, '', merged, flags=re.DOTALL)

    # Remove any extra blank lines left in the preamble
    merged = re.sub(r'\n{3,}', '\n\n', merged)

    # 4. Replace all \validatedbullet{...} with \item ...
    return clean_generated_tex(merged)


def clean_and_write(main_path: str, gen_path: str, output_path: str):
    """Clean and flatten LaTeX content, then write output file to output_path."""
    with open(main_path, 'r', encoding='utf-8') as f:
        main_content = f.read()
    with open(gen_path, 'r', encoding='utf-8') as f:
        gen_content = f.read()
        
    cleaned = clean_latex(main_content, gen_content)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(cleaned)


def clean_generated_file_in_place(file_path: str):
    """Remove debug helper macros from a generated .tex file in place."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    cleaned = clean_generated_tex(content)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(cleaned)
