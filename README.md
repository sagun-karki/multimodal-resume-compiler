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

## Prerequisites

Before running the application, ensure you have a LaTeX distribution with `xelatex` installed on your system:
- **macOS:** Install MacTeX (`brew install --cask mactex-no-gui`) or BasicTeX.
- **Linux:** Install TeX Live (`sudo apt-get install texlive-xetex` / `texlive-fonts-recommended`).
- **Windows:** Install MiKTeX or TeX Live.

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
- `make test` - Run automated tests.
- `make clean` - Clean up output and build files.

## Customizing the Template

For step-by-step instructions on how to use an external LLM to update the LaTeX resume layout, formatting, or data fields, see the [LaTeX Template Customization Guide](.agents/10_update_latex_template.md).

## Notes
- Cancellation is request-scoped via `run_id` (passed to `/stream` and `/api/cancel`).
- Default resume compile can be triggered explicitly via `POST /api/compile-default`.
