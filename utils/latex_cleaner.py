import os
import re

def clean_generated_tex(content: str) -> str:
    # Replace all \validatedbullet{...} with \item ...
    result = []
    idx = 0
    target = r'\validatedbullet{'
    while idx < len(content):
        next_pos = content.find(target, idx)
        if next_pos == -1:
            result.append(content[idx:])
            break
        
        result.append(content[idx:next_pos])
        
        start = next_pos + len(target)
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
    with open(main_path, 'r', encoding='utf-8') as f:
        main_content = f.read()
    with open(gen_path, 'r', encoding='utf-8') as f:
        gen_content = f.read()
        
    cleaned = clean_latex(main_content, gen_content)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(cleaned)

def clean_generated_file_in_place(file_path: str):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    cleaned = clean_generated_tex(content)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(cleaned)

if __name__ == '__main__':
    # Script execution for Makefile
    WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_tex = os.path.join(WORKSPACE, 'resources', 'resume.tex')
    gen_tex = os.path.join(WORKSPACE, 'resources', 'generated_data.tex')
    out_tex = os.path.join(WORKSPACE, 'output', 'resume.tex')
    clean_and_write(main_tex, gen_tex, out_tex)
