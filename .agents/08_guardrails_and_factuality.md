# SYSTEM RULES: FACTUALITY & HALLUCINATION GUARDRAILS

To protect the integrity of professional resume documents, enforce strict boundary guardrails:

## 1. Locked Variables & Identity Anchors
The loop is strictly forbidden from altering, modifying, or deleting core identification variables:
- Full Name
- Contact Info (Email, Phone, Github, LinkedIn, Website links)
- Actual Degree Names & University Names
- Job Titles & Company Names

These structures are "locked anchors" and must map exactly to the inputs provided in `my-content/user_profile.md`.

## 2. Automated Fact Verification Pass
Prior to compiling the document, the Python engine must run a substring lookup check:
- Verify that all key metrics, technical tools, and specific project names generated in the LaTeX file exist as exact substrings inside the original `my-content/user_profile.md`.
- Prevents the generator model from creating fake projects or credentials to satisfy ATS keywords or layout empty margins.

## 3. Empty Profile Exception Handler
If the Vision model reports `STATUS: EMPTY_BOTTOM` but the state manager verifies that **all bullet points and achievements from the master profile have already been fully exhausted**, halt the loop. Do not allow the generator to invent details.
- Terminate the optimization loop immediately.
- Raise a user notification on the front-end dashboard:
  *"Layout consistent, but profile content is insufficient to fill the page. Please manually add more real achievements."*
