# Claude Development Guidelines

## Code Quality Requirements

**CRITICAL: Code must be linted and tested before opening any PR.**

### Pre-Push Checklist

Always run these commands before pushing code:

```bash
make lint   # Must pass with no errors
make test   # Must pass all tests
```

### CI/CD Commands

The project uses these make commands in CI/CD:

```bash
make lint   # Run flake8 and pyright
make test   # Run pytest with coverage
make build  # Build Python package (if available)
```

### Development Workflow

1. Make code changes
2. **ALWAYS** run `make lint` - fix any errors
3. **ALWAYS** run `make test` - ensure all tests pass
4. Only then commit and push
5. Open PR only after local validation passes

### Make Commands

- `make dev` - Start development server
- `make lint` - Run code quality checks
- `make test` - Run test suite with coverage
- `make help` - Show all available commands

## Pull Requests and Issues

Terse is best. For example:

```
- Change package path from directory name to "." (root)
- Remove leading dot from manifest filename
- Use detailed extra-files config with TOML type and jsonpath
- Add top-level release-type for proper Python project detection
```

No emojis or excessive formatting.
