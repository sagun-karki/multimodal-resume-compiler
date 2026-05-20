# AGENT SPECIFICATION: AUTONOMOUS MULTIMODAL RESUME BUILDER

## 1. System Vision & Objective
You are tasked with building an autonomous, self-healing, layout-aware resume optimization engine. The system takes a comprehensive master markdown profile and a target job description, tailors the content for maximum semantic ATS alignment, and uses a multi-stage feedback loop (including a Vision LLM) to ensure the final output fits perfectly on a single page with consistent, professional typography.

### Core Architectural Mandate
- The LaTeX document geometry, line spacing, margins, and font paddings are **100% static and immutable**. 
- The agent loop is **FORBIDDEN** from modifying spacing variables (`\vspace`, `\vfill`) or altering margins to fix layout constraints.
- All spatial and layout problems **MUST** be solved exclusively by dynamically adjusting **content volume and linguistic density** (adding or trimming high-value bullet points).

## 2. Technical Stack
- **Backend Framework:** Flask (Python 3.11+)
- **Typesetting Engine:** XeLaTeX (via local system subprocess)
- **PDF Manipulation & Rasterization:** PyMuPDF (`fitz`)
- **LLM Orchestration:** OpenAI API (or compatible local endpoint)
- **Frontend View:** HTML5, Tailwind CSS, JavaScript (Vanilla Fetch API for streaming/SSE updates)

## 3. Repository Directory Structure
The workspace must match this structural schema exactly:
```text
python-resume-builder/
├── .agents/                                  # This agent instruction directory
├── my-content/                               # Input Context Layer
│   ├── user_profile.md                       # Comprehensive master data history
│   └── job_description.txt                   # Target job text block (UI input target)
├── resources/                                # Static LaTeX Template Layer
│   ├── awesome-cv.cls                        # Unmodified document stylesheet (locked layout)
│   ├── resume.tex                            # Root architecture layout (imports generated_data.tex)
│   └── generated_data.tex                    # Build-target overwritten by Loop (Gitignored)
├── stages/                                   # Programmatic Processing Layer
│   ├── __init__.py
│   ├── stage0_closeness_analyzer.py          # Pre-flight text matching & ATS analysis
│   ├── stage1_text_generator.py              # Semantic LaTeX macro scaling
│   ├── stage2_python_sanitizer.py            # String regex cleaning & orphan checks
│   ├── stage3_latex_compiler.py              # Headless compilation & log parsing
│   ├── stage4_pymupdf_router.py              # Page count routing & PNG rasterization
│   └── stage5_vision_inspector.py            # Multi-modal layout balance evaluation
├── utils/                                    # System Engine Core
│   ├── __init__.py
│   ├── token_tracker.py                      # Token calculator and pricing aggregator
│   └── state_manager.py                      # Loop state machine (hashes, histories)
├── output/                                   # Compilation Build Targets (Gitignored)
│   ├── resume.pdf                            # Final physical single-page PDF document
│   └── resume.log                            # Internal compilation trace log
├── templates/                                # Flask Web Templates
│   └── index.html                            # Dual-panel UI canvas
├── app.py                                    # Flask server & Server-Sent Events (SSE) orchestrator
├── Makefile                                  # Automation command interface
└── requirements.txt                          # Dependency configurations
```
