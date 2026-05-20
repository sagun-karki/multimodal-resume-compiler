# SYSTEM RULES: LOOP ORCHESTRATION & STATE MACHINE

To prevent the autonomous loop from running infinitely, consuming excessive tokens, or hitting feedback plateaus, build the following orchestration rules into `utils/state_manager.py`:

## 1. Loop Constraints
- **Iteration Limit:** Hard cap the execution at a maximum of **5 cycles/attempts**.
- **Cryptographic Hashing:** Before writing the generated content block to `resources/generated_data.tex`, compute the MD5 hash of the generated text string and append it to a historical list.
- **Plateau Termination:** If the newly generated text block's MD5 hash matches a hash from a previous iteration, it indicates that the model has plateaued or hit an optimization dead-end. **Terminate immediately** and raise a UI alert.

## 2. Average Pass Expectation
Due to the dual-stage validation architecture (internal Python sanitization & compiler log checks running locally for micro-checks, and Vision LLM running only for macro balance), most runs should converge in **2 to 3 iterations**:
- **Pass 1:** Tailoring/ATS gap injection and first compile.
- **Pass 2:** Visual validation. If perfect, terminate. If empty bottom, trigger expansion pass.
- **Pass 3:** Density self-healing generation and final verification compilation.
