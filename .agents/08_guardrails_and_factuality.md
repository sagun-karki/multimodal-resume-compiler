# FACTUALITY & IDENTITY GUARDRAILS

## Purpose
Protect the credibility of the resume document by enforcing strict integrity limits on the generative optimization loop.

## Guardrail Constraints
1. **Locked Personal Credentials:**
   The loop is strictly prohibited from modifying, updating, or deleting core personal identifiers:
   - Full Name
   - Contact coordinates (Email, Phone, Github/LinkedIn handles, Website URL links)
   - Academic names (Universities, Degrees, Dates)
   - Employer names and official Job Titles
2. **Fact Validation Check:**
   Before typesetting, the system validates that any added metrics, tools, or projects correspond directly to source accomplishments inside `user_profile.md`.
3. **Empty Profile Expansion Guard:**
   If the `VisualAuditorAgent` flags `EMPTY_BOTTOM` but the compiler confirms that all experiences and achievements from `user_profile.md` are already fully utilized, the loop halts. It refuses to hallucinate fake credentials to fill vertical gaps.
   - **UI Warning**: Returns an alert warning the user that their profile has been fully exhausted but layout could not reach the bottom, advising manual additions.
