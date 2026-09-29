---
name: Add-on Template Infrastructure PR
about: Use this template for PRs that modify the AddonTemplate repository structure, build scripts, CI/CD, tooling, or documentation.
title: '[Template] '
labels: 'template'
---

## Summary of Template Changes
<!-- Describe the changes made to the AddonTemplate repository structure, build scripts, workflows, or documentation and why they are necessary. -->

## Related Issue
<!-- Link to related issue(s), e.g., Fixes #123 -->

## Type of Change
- [ ] Build System / SCons updates (`sconstruct`, `site_scons/`)
- [ ] CI/CD & GitHub Actions (`.github/workflows/`, `.github/scripts/`)
- [ ] Development Dependencies & Tooling (`pyproject.toml`, `uv.lock`, `prek.toml`)
- [ ] Template Documentation & Boilerplate (`readme.md`, `docs/`, `manifest.ini.tpl`)
- [ ] Bug fix in template scripts/code
- [ ] Refactoring / Code Quality improvement

## Downstream Add-on Impact
- [ ] **No Breaking Changes**: Existing add-ons created from this template can merge upstream changes without issue.
- [ ] **Breaking / Migration Needed**: Requires manual migration steps or configuration updates for existing add-ons (describe below).

### Migration / Upgrade Instructions (if applicable)
<!-- Detail any steps downstream maintainers must take to adopt these template changes. -->

## Local Quality Checks & Verification
- [ ] Ran `scons` and verified the add-on package builds cleanly.
- [ ] Ran `prek` / `ruff check .` with zero lint errors.
- [ ] Ran `pytest` with all tests passing.
- [ ] Verified CI workflow script behavior locally or via test workflow run.

## Documentation & Changelog
- [ ] Updated `readme.md` or developer documentation (if applicable).
