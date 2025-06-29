# Release Guide

This document outlines the recommended workflow for creating proper releases of the ADK Agents project.

## Overview

The project uses a hybrid versioning approach:
- **Development**: Manual version management in `src/wrapper/adk/version.py`
- **Releases**: Git tag-based versioning with automatic CI/CD publishing
- **Dynamic Resolution**: The `extract_version.sh` script handles version detection across different contexts

## Pre-Release Checklist

### 1. Code Quality & Testing
- [ ] All tests pass locally: `uv run pytest`
- [ ] Code coverage meets requirements (≥80%)
- [ ] Linting passes: `uv run ruff check`
- [ ] Type checking passes: `uv run mypy`
- [ ] No security vulnerabilities in dependencies

### 2. Documentation
- [ ] Update `CHANGELOG.md` with new features, changes, and fixes
- [ ] Update `README.md` if needed
- [ ] Ensure documentation is up-to-date
- [ ] Review and update any API documentation

### 3. Version Planning
- [ ] Determine version number following [Semantic Versioning](https://semver.org/):
  - **MAJOR**: Breaking changes
  - **MINOR**: New features (backward compatible)
  - **PATCH**: Bug fixes (backward compatible)

## Release Workflow

### Step 1: Prepare the Release

1. **Create a release branch**:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b release/v1.2.3
   ```

2. **Update the version in code**:
   ```bash
   # Edit src/wrapper/adk/version.py
   __version__ = "1.2.3"
   ```

3. **Update CHANGELOG.md**:
   ```markdown
   ## [1.2.3] - 2024-01-15
   ### Added
   - New feature description
   
   ### Changed
   - Modified functionality description
   
   ### Fixed
   - Bug fix description
   ```

4. **Commit the changes**:
   ```bash
   git add src/wrapper/adk/version.py CHANGELOG.md
   git commit -m "chore: prepare release v1.2.3"
   ```

### Step 2: Test the Release

1. **Run comprehensive tests**:
   ```bash
   uv run pytest tests/ --cov --cov-report=term
   ```

2. **Test the package build**:
   ```bash
   uv build
   ```

3. **Verify version extraction**:
   ```bash
   ./scripts/ci/extract_version.sh
   # Should output: 1.2.3
   ```

### Step 3: Create the Release

1. **Push the release branch**:
   ```bash
   git push origin release/v1.2.3
   ```

2. **Create and merge PR**:
   - Create a PR from `release/v1.2.3` to `main`
   - Title: "Release v1.2.3"
   - Include changelog in PR description
   - Get required approvals
   - Merge the PR

3. **Create the release tag**:
   ```bash
   git checkout main
   git pull origin main
   git tag -a v1.2.3 -m "Release v1.2.3"
   git push origin v1.2.3
   ```

### Step 4: Automated Publishing

The CI/CD pipeline (`.github/workflows/publish.yml`) will automatically:
- Detect the new tag
- Build the package
- Publish to PyPI
- Create a GitHub release

Monitor the workflow at: `https://github.com/BlueCentre/adk-agents/actions`

## Post-Release Tasks

### 1. Verify Publication
- [ ] Check PyPI: https://pypi.org/project/adk-agent/
- [ ] Test installation: `pip install adk-agent==1.2.3`
- [ ] Verify GitHub release created

### 2. Communication
- [ ] Announce the release in relevant channels
- [ ] Update project documentation if needed
- [ ] Notify stakeholders of significant changes

### 3. Prepare for Next Development
- [ ] Update version to next development version:
   ```bash
   # src/wrapper/adk/version.py
   __version__ = "1.2.4-dev"  # or next planned version
   ```

## Emergency Hotfix Releases

For critical bug fixes that need immediate release:

1. **Create hotfix branch from main**:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b hotfix/v1.2.4
   ```

2. **Apply minimal fix and test thoroughly**

3. **Follow standard release process with accelerated review**

4. **Consider backporting to supported versions if needed**

## Version Management Best Practices

### Development Versions
- Keep `src/wrapper/adk/version.py` updated during development
- Use `-dev` suffix for unreleased versions
- Example: `1.2.3-dev`

### Release Versions
- Always use clean semantic versions for releases
- Example: `1.2.3` (no suffixes)

### Git Tags
- Always use `v` prefix: `v1.2.3`
- Use annotated tags with release notes
- Tags trigger automatic publishing

### CI/CD Integration
- The `extract_version.sh` script handles version detection
- Git tags take precedence over file-based versions
- Supports PEP 440 version formatting

## Troubleshooting

### Version Not Detected Correctly
```bash
# Test version extraction
./scripts/ci/extract_version.sh

# Check git tags
git tag -l --sort=-version:refname

# Verify version file
cat src/wrapper/adk/version.py
```

### CI/CD Pipeline Issues
- Check GitHub Actions logs
- Verify PyPI token is configured
- Ensure tag follows `v*` pattern

### Package Build Issues
```bash
# Clean build
rm -rf dist/ build/
uv build

# Check built package
ls -la dist/
```

## Release Checklist Template

Copy this checklist for each release:

```markdown
## Release v1.2.3 Checklist

### Pre-Release
- [ ] All tests pass
- [ ] Code coverage ≥80%
- [ ] Linting passes
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version number determined

### Release Process
- [ ] Release branch created
- [ ] Version updated in code
- [ ] Changes committed
- [ ] Tests pass on release branch
- [ ] Package builds successfully
- [ ] PR created and approved
- [ ] PR merged to main
- [ ] Git tag created and pushed

### Post-Release
- [ ] CI/CD pipeline completed
- [ ] PyPI publication verified
- [ ] GitHub release created
- [ ] Installation tested
- [ ] Stakeholders notified
- [ ] Next development version prepared
```

## Additional Resources

- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [PyPI Publishing](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
