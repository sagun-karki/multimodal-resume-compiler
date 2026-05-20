# Agent Rules

## Core Style
- Write minimal code that solves the exact problem.
- Prefer clarity over cleverness.
- Keep functions small and single-purpose.
- Avoid unnecessary abstractions.
- Remove dead code quickly.

## Reliability
- Fail fast with clear error messages.
- Never swallow exceptions silently.
- Validate all external inputs.
- Keep side effects explicit and localized.
- Make cancellation and timeouts first-class.

## Project Conventions
- Keep business logic out of route handlers when possible.
- Avoid global mutable state for request-dependent behavior.
- Use typed interfaces (`dataclass`/type hints) for shared payloads.
- Centralize constants/config; avoid scattered magic numbers.
- Keep prompts/versioned templates in dedicated files.

## Testing and Quality
- Add tests for critical flows and failure paths.
- Add regression tests for every fixed bug.
- Prefer deterministic tests over network-dependent tests.
- Run lint/format checks before finalizing changes.

## Logging and Observability
- Log stage boundaries and major decisions.
- Include enough context to debug failures.
- Do not log secrets or full sensitive user content.
- Emit structured status payloads consistently.

## Git Hygiene
- Keep commits focused and small.
- Do not mix refactor and behavior changes in one commit.
- Update docs when behavior or commands change.
