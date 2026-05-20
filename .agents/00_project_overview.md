# AGENT SPECIFICATION: AUTONOMOUS MULTIMODAL RESUME BUILDER

## 1. System Vision & Objective
This repository is an autonomous, layout-aware, self-healing resume optimization engine. It takes a comprehensive master profile (Markdown format) and a target job description, tailors the contents for maximum ATS semantic matching, and runs a class-based multi-agent feedback loop to ensure the final resume compiles to exactly one page with a balanced layout and correct margins.

### Core Architectural Mandate
- **Immutable Layout**: LaTeX margins, line spacing, font configurations, and vertical spacing are static. 
- **Content-Driven Layout Corrections**: The agents must **never** modify spacing variables (`\vspace`, `\vfill`) or margins to fix height violations.
- **Self-Healing Loop**: All spatial and layout constraints must be resolved dynamically by adjusting the text volume and density (e.g., shortening or expanding bullet points) through the cooperative agent feedback loop.

## 2. Technical Stack
- **AI Models**: Google Gemini API (via the `google-generativeai` SDK).
- **Backend Orchestrator**: Flask (Python 3.11+) running local compilation and page routing scripts.
- **Typesetting Engine**: XeLaTeX (via local subprocess compilation).
- **PDF Manipulation & Rasterization**: PyMuPDF (`fitz`).
- **UI Dashboard**: HTML5, Vanilla CSS for maximum styling flexibility and control, JavaScript with Server-Sent Events (SSE) for live agent logs, Chart.js for real-time diagnostics, and custom drag splitters for resizable panel divisions.

## 3. Multi-Agent Team Architecture
The system has been restructured from a rigid procedural pipeline into a robust, class-based **Multi-Agent Collaboration Network**:

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

- **Coordinator Agent (`agents/coordinator.py`):** Acts as the supervisor, guiding the optimization flow, handling intermediate variables, and invoking external programmatic tools.
- **ATS Analyzer Agent (`agents/ats_analyzer.py`):** Scores profile alignment against the job description, detects missing skills, and selects target keywords.
- **Resume Writer Agent (`agents/resume_writer.py`):** Formats experience blocks, dynamically injects target keywords, and shortens/lengthens bullet points to comply with layout boundaries.
- **Visual Auditor Agent (`agents/visual_auditor.py`):** Utilizes multimodal vision to review the final spacing, margins, orphan lines, and general visual layout of the rendered page.
- **Compiler Tool (`stages/stage2_pdf_manager.py`):** Programmatic tool that compiles LaTeX source using XeLaTeX, catches typographic warnings, and generates high-resolution page previews.
