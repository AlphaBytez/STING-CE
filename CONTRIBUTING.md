# Contributing to STING CE

Thank you for your interest in contributing to STING CE! This document provides guidelines for contributing to the project.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/your-org/sting-ce-dev-preview/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Docker version, etc.)
   - Relevant logs or screenshots

### Suggesting Features

1. Check [Issues](https://github.com/your-org/sting-ce-dev-preview/issues) for existing feature requests
2. Create a new issue with:
   - Clear use case description
   - Proposed solution
   - Alternative solutions considered
   - Impact on existing features

### Pull Requests

1. **Fork the repository** and create a feature branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our coding standards:
   - Write clean, readable code
   - Add comments for complex logic
   - Follow existing code style
   - Keep commits atomic and well-described

3. **Test your changes**
   ```bash
   # Run tests
   ./manage_sting_dev.sh test

   # Test manually
   ./manage_sting_dev.sh update <service>
   ```

4. **Document your changes**
   - Update relevant documentation
   - Add docstrings to new functions
   - Update API documentation if needed

5. **Submit your PR** with:
   - Clear title and description
   - Reference to related issues
   - Screenshots/logs if applicable
   - Checklist of completed items

## Development Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.9+
- Node.js 16+ (for frontend)
- Git

### Local Setup

```bash
# Clone your fork
git clone https://github.com/your-username/sting-ce-dev-preview.git
cd sting-ce-dev-preview

# Add upstream remote
git remote add upstream https://github.com/your-org/sting-ce-dev-preview.git

# Start development environment
./manage_sting_dev.sh start

# Check status
./manage_sting_dev.sh status
```

### Development Workflow

1. **Keep your fork updated**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Create feature branch**
   ```bash
   git checkout -b feature/my-feature
   ```

3. **Make changes and commit**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

4. **Push to your fork**
   ```bash
   git push origin feature/my-feature
   ```

5. **Create Pull Request** on GitHub

## Coding Standards

### Python

- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints where applicable
- Maximum line length: 100 characters
- Use meaningful variable names
- Write docstrings for functions and classes

Example:
```python
def process_document(content: str, metadata: dict) -> dict:
    """
    Process a document and extract relevant information.

    Args:
        content: The document content as string
        metadata: Dictionary containing document metadata

    Returns:
        Dictionary with processed document data

    Raises:
        ValueError: If content is empty
    """
    if not content:
        raise ValueError("Content cannot be empty")

    # Process document
    return {"status": "processed", "data": content}
```

### JavaScript/TypeScript

- Use ESLint configuration
- Prefer functional components
- Use TypeScript for type safety
- Follow React best practices

### Docker

- Multi-stage builds where appropriate
- Minimize layer count
- Use specific version tags
- Document build arguments

## Testing

### Unit Tests

```bash
# Python
cd app
python -m pytest tests/

# JavaScript
cd frontend
npm test
```

### Integration Tests

```bash
# Test service interactions
./scripts/test_integration.sh
```

### Manual Testing

```bash
# Update and restart service
./manage_sting_dev.sh update <service>

# View logs
./manage_sting_dev.sh logs <service>
```

## Documentation

### Code Documentation

- Add docstrings to all public functions
- Document complex algorithms
- Include usage examples

### API Documentation

- Update `docs/api/` for API changes
- Include request/response examples
- Document error codes

### User Documentation

- Update `docs/guides/` for feature changes
- Add tutorials for new features
- Keep README.md current

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Build/tooling changes

Examples:
```
feat(knowledge): add semantic search functionality

Implement vector-based semantic search using Chroma.
Includes document embedding and similarity scoring.

Closes #123
```

```
fix(auth): resolve session expiration issue

Sessions were expiring too quickly due to incorrect
TTL configuration in Kratos.

Fixes #456
```

## Review Process

1. **Automated Checks**: CI/CD pipeline runs tests and linting
2. **Code Review**: At least one maintainer reviews the code
3. **Testing**: Reviewer tests the changes locally
4. **Approval**: PR is approved and merged

## Release Process

1. Version bump in relevant files
2. Update CHANGELOG.md
3. Create release tag
4. Build and publish containers
5. Update documentation

## Getting Help

- **Documentation**: Check `docs/` directory
- **Discussions**: Use GitHub Discussions
- **Issues**: Open an issue for bugs or questions
- **Chat**: Join our Discord/Slack community

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project README

Thank you for contributing to STING CE!
