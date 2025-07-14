# Repo Coding Conventions

## General Style
- Use **PEP8** formatting with 4 spaces per indent and line length <=79.
- Write docstrings for all new functions and classes using the **NumPy** style.
- Prefer explicit imports (e.g. `from module import name`).
- Use type hints on all new function definitions.

## Commits
- Commit messages should start with a short imperative summary (<50 chars).
- Follow the summary with a blank line and a more detailed explanation if needed.

## Testing
- Place tests under a `tests/` directory and run them with `pytest -q` from the repo root.
- When adding features, provide corresponding tests. If existing tests fail or cannot be run due to environment limitations, mention it in the PR description.

## Pull Request Message
Include the following sections in every PR description:

```
## Summary
- High level description of changes.

## Testing
- Commands run and their results. If tests couldn't run, state the reason.
```

