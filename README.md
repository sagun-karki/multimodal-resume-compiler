# Multimodal Resume Compiler

An autonomous, auto-correcting pipeline for tailoring and optimizing resumes. It leverages the power of Large Language Models (LLMs) and Multimodal Vision APIs to iteratively rewrite, format, and compile highly-tailored, ATS-friendly LaTeX resumes against specific job descriptions. 

The system detects visual and typographic layout issues (like orphan bullet points and uneven margins) and iteratively refines the text to produce a visually perfect, single-page PDF.

## Architecture Flow

```mermaid
graph TD
    classDef default fill:#1E293B,stroke:#475569,stroke-width:2px,color:#F8FAFC;
    classDef startNode fill:#0F766E,stroke:#14B8A6,stroke-width:2px,color:#F0FDFA;
    classDef stageNode fill:#0369A1,stroke:#0EA5E9,stroke-width:2px,color:#F0F9FF;
    classDef decisionNode fill:#B45309,stroke:#F59E0B,stroke-width:2px,color:#FEF3C7;
    classDef successNode fill:#15803D,stroke:#22C55E,stroke-width:2px,color:#F0FDF4;
    classDef failNode fill:#B91C1C,stroke:#EF4444,stroke-width:2px,color:#FEF2F2;

    A[Job Description & User Profile]:::startNode --> B(Stage 0: Closeness Analyzer):::stageNode
    B --> C(Stage 1: Text Generator):::stageNode
    C --> D(Stage 2: PDF Manager & Router):::stageNode
    
    D -->|Layout/Orphan/Overflow Errors| E(Auto-Correction State):::failNode
    D -->|Single Page OK| F{Stage 3: Vision Inspector}:::decisionNode
    
    F -->|Spacing/Margin/Skill Errors| E
    E -->|Feedback Loop| C
    
    F -->|Accepted Layout| G([Final resume.pdf & resume.tex]):::successNode
```

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
   Open your browser and navigate to `http://127.0.0.1:5000` to monitor and run the compilation pipeline.

## Other Commands

- `make compile` - Manually compile the LaTeX resume.
- `make clean` - Clean up output and build files.