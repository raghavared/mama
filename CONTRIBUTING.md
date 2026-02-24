# Contributing to MAMA

Thank you for your interest in contributing! MAMA is an open-source project and we welcome contributions of all kinds — bug fixes, new features, documentation improvements, and more.

---

## Table of Contents

- [Before You Start](#before-you-start)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Reporting Bugs](#reporting-bugs)
- [Requesting Features](#requesting-features)
- [Commit Message Convention](#commit-message-convention)

---

## Before You Start

- Read the [Code of Conduct](CODE_OF_CONDUCT.md). All contributors are expected to follow it.
- Check the [open issues](https://github.com/your-org/MAMA/issues) and [pull requests](https://github.com/your-org/MAMA/pulls) to avoid duplicate work.
- For significant changes, open an issue first to discuss the approach before writing code.

---

## How to Contribute

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/your-username/MAMA.git
   cd MAMA
   ```
3. **Create a branch** from `main`:
   ```bash
   git checkout -b fix/bug-description
   # or
   git checkout -b feat/feature-name
   ```
4. Make your changes, following the [coding standards](#coding-standards).
5. **Test** your changes locally.
6. **Push** your branch and open a **Pull Request** against `main`.

---

## Development Setup

**Backend:**
```bash
pip install uv
uv sync --extra dev
pre-commit install

# Start infra
docker compose up postgres redis -d

# Apply migrations
alembic upgrade head

# Start API
uvicorn src.api.main:app --reload --port 8000
```

**Dashboard:**
```bash
cd dashboard
npm install
npm run dev
```

**Run tests:**
```bash
pytest
pytest --cov=src tests/        # with coverage
```

**Lint and type-check:**
```bash
ruff check .
ruff format .
mypy src/
```

---

## Coding Standards

- Python code must pass `ruff` (linting + formatting) and `mypy` (strict type checking).
- All new Python modules must have type annotations.
- New API endpoints must include docstrings.
- New database columns must include an Alembic migration file following the naming convention `NNN_description.py`.
- Frontend code must be TypeScript (no `any` except at well-typed API boundaries).
- Do not commit `.env` files, API keys, or secrets.
- Keep PRs focused — one concern per PR.

---

## Submitting a Pull Request

- Fill out the PR template completely.
- Link the PR to the issue it addresses (e.g., `Closes #42`).
- Make sure all CI checks pass before requesting review.
- Keep the PR description concise but complete — what changed and why.
- PRs that change the database schema must include the migration file.
- PRs that add new agents must include at least one unit test.

---

## Reporting Bugs

Open an issue and include:

- A clear title and description of the bug.
- Steps to reproduce.
- Expected vs. actual behavior.
- Your environment (OS, Python version, Docker version).
- Relevant logs or error messages.

---

## Requesting Features

Open an issue with the `enhancement` label and describe:

- The problem you're trying to solve.
- Your proposed solution or approach.
- Any alternatives you considered.

---

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(scope): <short description>

[optional body]

[optional footer]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`

**Examples:**
```
feat(agents): add VST agent for video script generation
fix(jobs): reinitiation_count not persisting after restart
docs(readme): add Docker setup instructions
chore(deps): bump anthropic to 0.46.0
```
