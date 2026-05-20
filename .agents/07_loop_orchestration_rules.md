# COORDINATOR AGENT & LOOP SUPERVISION (`agents/coordinator.py`)

## Purpose
Supervise the lifecycle of the optimization runs. The coordinator orchestrates the communication loop between specialized agents (ATS Analyzer, Resume Writer, Visual Auditor) and programmatic tools (Compiler, Router).

## Loop Orchestration Rules
1. **Loop Hard Constraints:**
   - **Iteration Limit:** Hard cap of **5 iterations** to prevent excessive token use or infinite loops.
   - **Content-Plateau Detection:** Hashes the generated LaTeX content in each round (using SHA-256 or MD5). If the hash matches a draft from a previous iteration, it indicates that the model has hit a plateau/dead-end. The coordinator aborts the loop immediately to conserve resources and returns the best draft.
2. **Dynamic Correction Cycles:**
   - **Phase 1:** Runs `ATSAnalyzerAgent` to build the initial gap report and closeness score.
   - **Phase 2 (Correction Loop):**
     - Writer drafts/modifies content.
     - Compiler compiles LaTeX code and checks for syntax errors or box overflows.
     - Router checks fit page count. If page count > 1, immediately loops back with shortening commands.
     - If page count == 1, `VisualAuditorAgent` reviews design spacing. If layout is balanced, accepts and terminates. If empty bottom, loops back with lengthening commands.
