---
name: NVDA Add-on Feature / Fix PR
about: Use this template for PRs that modify add-on functionality, features, bug fixes, or translations.
title: ''
labels: ''
---

## Summary
<!-- Describe the changes made in this PR and why they are necessary. -->

## Related Issue
<!-- Link to related issue(s), e.g., Fixes #123 -->

## Type of Change
- [ ] Bug fix (fixes an issue without breaking existing API/behavior)
- [ ] New feature (adds new capability to the add-on)
- [ ] Performance improvement
- [ ] Code refactoring (no functional changes)
- [ ] Dependency update / CI pipeline tweak

## NVDA Testing & Verification Environment
- **Minimum NVDA Version Tested:** <!-- e.g. 2024.1 -->
- **Latest NVDA Version Tested:** <!-- e.g. 2026.2 / latest alpha -->
- **OS / Platform:** Windows 10 / 11

### Screen Reader & Accessibility Impact
- [ ] **Speech Output**: Verified speech feedback in affected NVDA modes/dialogs.
- [ ] **Braille Output**: Checked braille output/formatting.
- [ ] **Gestures & Shortcuts**: Verified keyboard shortcuts and NVDA input gestures.

## Add-on Manifest & Metadata Verification
- [ ] **`buildVars.py`**: Verified version strings, `minimumNVDAVersion`, and `lastTestedNVDAVersion`.
- [ ] **`changelog.md`**: Added a description of the change under the unreleased/current section.
- [ ] **i18n / Translatable Strings**: Ensured all user-visible strings use gettext (`_()`), and updated `.pot` file via `scons pot` if new strings were added.

## Local Quality Checks
- [ ] Ran `ruff check .` / `prek` cleanly.
- [ ] Ran `pytest` with 100% passing tests.
- [ ] Tested add-on bundle installation locally (`scons`).
