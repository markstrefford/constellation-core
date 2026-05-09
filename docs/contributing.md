# Contributing

We welcome contributions to Constellation! Whether you're fixing a bug, adding a new feature, or improving documentation, your help is appreciated.

## Getting Started

1. **Fork the repository** on GitHub.
2. **Clone your fork** locally.
3. **Install dependencies**: `pip install -e ".[dev,server]"`.
4. **Create a branch** for your changes: `git checkout -b feature/my-new-feature`.

## Development Workflow

### Coding Standards
- We use `ruff` for linting and formatting.
- We use `mypy` for static type checking.
- Please ensure your code passes both before submitting a PR.

```bash
# Run linting
ruff check .

# Run type checking
mypy .
```

### Running Tests
All new features should include tests. We use `pytest`.

```bash
python -m pytest tests/ -v
```

## Pull Request Process

1. Ensure all tests pass.
2. Update the `CHANGELOG.md` with a brief description of your changes.
3. Submit a Pull Request to the `main` branch.
4. A maintainer will review your code and provide feedback.

## Questions?

If you have questions about the codebase or how to implement a specific feature, please open an issue on GitHub.

---

- **[Next: Changelog](changelog.md)**
- **[Back to Home](index.md)**
