# CLAUDE.md

## Project Info

- **Repository**: `<https://github.com/natsinger/tender-dashboard.git>`
- **Tech Stack**: Python (backend/scripts) · React (frontend/dashboards) · PostgreSQL/SQLite (data)
- **Primary Language**: Hebrew (UI/content) · English (code/comments/docs)

---

## Core Rules

### Code Quality

- Keep code **clean and readable**. Prefer clarity over cleverness.
- Every file must have a top-level docstring or comment explaining its purpose.
- If a block of code is used more than once, extract it into a shared utility function — either in the same file or in a dedicated `utils/` module.
- When making changes, **delete all orphaned code** — unused imports, dead functions, commented-out blocks. Do not leave them "just in case."
- Follow PEP 8 for Python. Use ESLint + Prettier conventions for React/JS.
- Use **type hints** in all Python functions. Use **PropTypes or TypeScript** in React components.
- Never hardcode secrets, API keys, or credentials. Use environment variables (`.env` files).

### File & Folder Hygiene

- All temporary files, test outputs, scratch scripts, and one-off experiments go in the `tmp/` directory. This folder is `.gitignore`d.
- Do not create files outside the project structure without asking me first.
- If you create a new module or directory, update the project structure section in `STATUS.md` immediately.

### Git Discipline

- **Never push directly to `main`** (or whatever the protected branch is). Always work on a feature branch.
- Make **small, frequent commits** with clear messages in the format: `type(scope): description` (e.g., `feat(dashboard): add MADRS trajectory chart`).
- Commit after every meaningful, working change — not after a marathon of 20 changes. If something breaks, we need to be able to roll back cleanly.
- Before committing, verify the code runs without errors. Run linting and tests.
- **Never run destructive commands** (`rm -rf`, `git push --force`, `DROP TABLE`, `git reset --hard`) without explicit confirmation from me.

### Self-Correction & Learning

- When I correct you on something meaningful (a wrong assumption, a bad pattern, a misunderstanding about the project), **add the lesson to this file** under the "Lessons Learned" section below.
- If you are unsure about something, **ask me before proceeding**. Do not guess and build on top of a guess.

---

## Project Documentation (Required Files)

This project must always contain these three files at the root level. **Read all three at the start of every new session.**

| File | Purpose |
|------|---------|
| `PRD.md` | Product Requirements Document — background, problem, user stories, success metrics, roadmap |
| `TECH_SPEC.md` | Technical specification — architecture, data models, APIs, dependencies, deployment |
| `STATUS.md` | **Living document** — current project state, folder structure, what's done, what's pending, known bugs, recent decisions |

### STATUS.md Rules

- **Update `STATUS.md` after every meaningful code change.** This is non-negotiable.
- Include: what changed, what files were affected, any new bugs or decisions.
- If a session ends mid-task, write a clear "handoff note" in STATUS.md so the next session can pick up seamlessly.
- Structure it with sections: `## Current State`, `## Recent Changes`, `## Known Issues`, `## Next Steps`, `## Project Structure`.

---

## How I Work (Read This Carefully)

- I am not a senior developer. I rely on you to catch mistakes I won't notice — bad architecture decisions, security issues, performance problems, missing edge cases.
- **Be proactive about flagging problems.** Don't silently implement something you know is fragile or wrong just because I asked for it. Push back and explain why.
- When I describe what I want, **ask me clarifying questions first** before writing code. At minimum, confirm your understanding of the requirement.
- When presenting a solution, briefly explain **why** you chose this approach over alternatives — especially for architecture decisions.
- If a task is complex, **break it into steps and show me the plan** before executing. Don't build the whole thing in one shot.

---

## Coding Patterns & Preferences

### Python

- Use `pathlib` for file paths, not `os.path`.
- Use `logging` module (not `print()`) for all diagnostic output. Configure structured logs with timestamps and severity levels.
- For data work, prefer `pandas` for tabular data, `matplotlib`/`plotly` for visualization.
- For NLP/text analysis tasks, follow validated methodology: preprocessing → annotation/labeling → analysis → validation. Document every analytical decision.
- Virtual environments: use `venv` or `conda`. Pin all dependencies in `requirements.txt` with exact versions.
- Write docstrings in Google style.

### React

- Functional components with hooks only. No class components.
- State management: React Context or Zustand for simple projects, Redux only if justified.
- Component files: one component per file, named to match the component.
- Keep API calls in dedicated `services/` or `api/` modules, not inside components.
- Use CSS Modules or Tailwind — no inline styles for anything beyond trivial one-offs.

### Data & Analysis

- Every dataset must have a companion README or metadata section explaining: source, date collected, schema, known quality issues.
- Never modify raw data files. Always work on copies, and keep the transformation pipeline reproducible.
- For clinical/research data: maintain full audit trail of transformations. Document every filter, exclusion, and assumption.

---

## Testing

- Write tests for any function that processes data, handles business logic, or could silently produce wrong results.
- Python: use `pytest`. React: use `vitest` or `jest` + React Testing Library.
- Before telling me "it works," actually run the code and verify the output. Don't assume.
- For dashboards: visually verify that charts render correctly with edge cases (empty data, single data point, very large datasets).

---

## Logging & Debugging

- Every backend process and script must produce **detailed logs** saved to `logs/` directory.
- Log format: `[TIMESTAMP] [LEVEL] [MODULE] message`
- Log at minimum: script start/end, data loaded (row counts), key decision points, errors with full tracebacks.
- For web apps: use browser dev tools output. If using Playwright for testing, capture screenshots on failure.

---

## Security & Privacy (Critical)

- This project may handle **clinical research data or personal information**. Treat all data as sensitive by default.
- Never log, print, commit, or expose: patient identifiers, personal health information, API keys, passwords.
- Ensure `.gitignore` covers: `.env`, `tmp/`, `logs/`, `data/raw/`, any file containing real patient data.
- If sample/test data is needed, create synthetic data. Never use real records for testing.

---

## Communication Style

- Respond in **English** unless I write to you in Hebrew. If I write in Hebrew, respond in Hebrew.
- Be direct and concise. Skip the preamble.
- When explaining technical decisions, use plain language — I understand product and design, but I'm not a senior engineer.
- If something will take multiple steps, give me a numbered plan first.

---

## Lessons Learned

<!-- Claude: Add entries here when Nathanael corrects you on something important. Format: -->
<!-- - **[Date]**: Description of the mistake and the correct approach. -->

_No entries yet._

---

## Quick Reference Commands

```bash
# Start dev server
# <ADD YOUR COMMAND>

# Run tests
# pytest tests/ -v

# Lint Python
# ruff check .

# Lint React
# npx eslint src/

# Format code
# ruff format . && npx prettier --write src/
```

---

## MCP Integrations

- **Playwright** (for web app testing/debugging) — configured in `settings.json`
- Add others as needed: `<LIST_HERE>`

---

## Hooks (Configured in settings.json)

1. **Pre-commit: Protected branch guard** — Block commits to `main`.
2. **Pre-commit: Dangerous command check** — Block `rm -rf`, `--force`, `DROP`, `TRUNCATE`.
3. **Post-change: Auto-format** — Run `ruff format` + `prettier` after significant changes.
4. **Post-change & Pre-commit: Code review** — Run a separate agent-based code review. Block commits that fail review.

---

_Last updated: <DATE>_
