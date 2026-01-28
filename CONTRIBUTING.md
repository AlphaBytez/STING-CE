# Contributing to STING-CE

Thank you for your interest in contributing to STING-CE! This project is developed by **AlphaBytez** and maintained by the community.

## 🤝 Ways to Contribute

We welcome contributions in many forms:

- **Bug Reports**: Found a bug? Let us know! Opening an issue is a valuable contribution
- **Feature Requests**: Have an idea? We'd love to hear it! Issues help shape the roadmap
- **Code Contributions**: Want to fix a bug or add a feature? Awesome! Pull requests welcome
- **Documentation**: Help improve our docs - typo fixes, clarifications, examples
- **Testing**: Test new releases and report issues - real-world feedback is invaluable
- **Community Support**: Help others in discussions and share your experience

> **Remember:** You don't need to write code to contribute! Issues, documentation improvements, and helping other users are all valuable contributions to the project.

## 🚀 Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/sting-ce.git
cd sting-ce

# Add upstream remote
git remote add upstream https://github.com/alphabytez/sting-ce.git
```

### 2. Set Up Development Environment

```bash
# Install STING-CE
./install_sting.sh

# Verify installation
docker ps
```

### 3. Create a Branch

```bash
# Create a feature branch
git checkout -b feature/amazing-feature

# Or a bug fix branch
git checkout -b fix/bug-description
```

## 💻 Development Guidelines

### Code Style

**Python (Backend)**
- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints where appropriate
- Document functions with docstrings
- Maximum line length: 100 characters

**JavaScript/React (Frontend)**
- Follow ESLint configuration
- Use functional components with hooks
- PropTypes for component props
- Meaningful component and variable names

**Docker**
- Use multi-stage builds when possible
- Minimize layers
- Use specific version tags, not `latest`
- Document all environment variables

### Testing

Before submitting, ensure all tests pass:

```bash
# Run all tests
./scripts/run_tests.sh

# Test specific component
python3 -m pytest tests/test_auth.py

# Test email delivery
python3 scripts/health/validate_mailpit.py
```

### Documentation

- Update README.md for user-facing changes
- Update API docs for API changes
- Add inline comments for complex logic
- Update CHANGELOG.md with your changes

## 📝 Pull Request Process

### Before Submitting

1. **Sync with upstream**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run tests**: Ensure all tests pass

3. **Update docs**: Document your changes

4. **Clean commits**: Use meaningful commit messages
   ```bash
   # Good
   git commit -m "feat: Add passwordless login for mobile devices"
   git commit -m "fix: Resolve mailpit port mapping issue"

   # Not so good
   git commit -m "update stuff"
   git commit -m "fix"
   ```

### Submitting

1. **Push your branch**:
   ```bash
   git push origin feature/amazing-feature
   ```

2. **Open Pull Request** on GitHub

3. **Fill out PR template** with:
   - Description of changes
   - Issue number (if applicable)
   - Testing performed
   - Screenshots (if UI changes)

### After Submitting

- Respond to review feedback
- Keep your PR up to date with main branch
- Be patient - reviews may take a few days

## 🐛 Reporting Bugs

When reporting bugs, please include:

- **Description**: Clear description of the issue
- **Steps to Reproduce**: How to trigger the bug
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**:
  - OS version
  - Docker version
  - STING-CE version
- **Logs**: Relevant error messages or logs
  ```bash
  docker compose logs [service]
  ```

## 💡 Feature Requests

When requesting features:

- **Use Case**: Describe the problem you're trying to solve
- **Proposed Solution**: Your idea for solving it
- **Alternatives**: Other solutions you've considered
- **Additional Context**: Any other relevant information

## 🔒 Security Issues

**DO NOT** create public issues for security vulnerabilities.

Instead, email security concerns to: **security@alphabytez.dev**

See [SECURITY.md](SECURITY.md) for our security policy.

## 📜 License

By contributing, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).

All contributions must include:
```
Copyright 2025 AlphaBytez and the STING-CE Community

Licensed under the Apache License, Version 2.0
```

## 🎯 Development Priorities

Current focus areas:

### High Priority
- Authentication improvements
- Email delivery reliability
- Documentation enhancements
- Bug fixes

### Medium Priority
- Additional LLM provider support
- Performance optimizations
- Testing improvements

### Future
- Kubernetes deployment
- Multi-tenancy support
- Mobile app integration

## 🤔 Questions?

- **General Questions**: [GitHub Discussions](https://github.com/alphabytez/sting-ce/discussions)
- **Bug Reports**: [GitHub Issues](https://github.com/alphabytez/sting-ce/issues)
- **Contact**: olliec@alphabytez.dev

## 👥 Community

Join our growing community:

- **GitHub**: Star and watch the repository
- **Discussions**: Share ideas and get help
- **Issues**: Report bugs and request features
- **Pull Requests**: Contribute code

---

**Thank you for contributing to STING-CE!**

Developed by [AlphaBytez](https://github.com/alphabytez)
