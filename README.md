# Multimodal Resume Compiler

An autonomous, auto-correcting multi-agent system for tailoring and optimizing resumes. It leverages the power of Large Language Models (LLMs) and Multimodal Vision APIs to iteratively rewrite, format, and compile highly-tailored, ATS-friendly LaTeX resumes against specific job descriptions.

The system utilizes specialized cooperating agents overseen by a coordinator to detect visual, typographic, or content gaps, refining the document until it compiles perfectly to a single-page PDF.

## Multi-Agent Architecture

```mermaid
graph TD
    classDef default fill:#1E293B,stroke:#475569,stroke-width:2px,color:#F8FAFC;
    classDef startNode fill:#0F766E,stroke:#14B8A6,stroke-width:2px,color:#F0FDFA;
    classDef agentNode fill:#0369A1,stroke:#0EA5E9,stroke-width:2px,color:#F0F9FF;
    classDef toolNode fill:#6B21A8,stroke:#A855F7,stroke-width:2px,color:#FAF5FF;
    classDef successNode fill:#15803D,stroke:#22C55E,stroke-width:2px,color:#F0FDF4;

    A[Job Description & User Profile]:::startNode --> B(ATS Analyzer Agent):::agentNode
    B --> C(Coordinator Agent):::agentNode
    C --> D(Resume Writer Agent):::agentNode
    D -->|Initial/Revised JSON| E(Compiler Tool):::toolNode
    E -->|Rendered PNG / Compilation Errors| F(Visual Auditor Agent):::agentNode
    F -->|Accepted Layout| G([Final resume.pdf & resume.tex]):::successNode
    F -->|Critique / Adjustments| C
```

### Specialized Agents & Roles
*   **Coordinator Agent (`agents/coordinator.py`):** Acts as the supervisor, guiding the optimization flow, handling intermediate variables, and invoking external programmatic tools.
*   **ATS Analyzer Agent (`agents/ats_analyzer.py`):** Scores profile alignment against the job description, detects missing skills, and selects target keywords.
*   **Resume Writer Agent (`agents/resume_writer.py`):** Formats experience blocks, dynamically injects target keywords, and shortens/lengthens bullet points to comply with layout boundaries.
*   **Visual Auditor Agent (`agents/visual_auditor.py`):** Utilizes multimodal vision to review the final spacing, margins, orphan lines, and general visual layout of the rendered page.
*   **Compiler Tool (`stages/stage2_pdf_manager.py`):** Programmatic tool that compiles LaTeX source using XeLaTeX, catches typographic warnings, and generates high-resolution page previews.

## How to Run

1. **Install Dependencies:**
   ```bash
   make install
   # or run: pip install -r requirements.txt
   ```

2. **Set up Environment:**
   Ensure you have your `.env` file configured with your Gemini API keys.
   ```bash
   GEMINI_API_KEY=your_key_here
   ```

3. **Start the Application:**
   Run the Flask UI and orchestration server:
   ```bash
   make run
   # or run: python app.py
   ```

4. **Access the Web Interface:**
   Open your browser and navigate to `http://127.0.0.1:5001` to monitor and run the compilation pipeline.

## Other Commands

- `make compile` - Manually compile the LaTeX resume.
- `make clean` - Clean up output and build files.