## 1. Setup
- [x] Verify prerequisite: Python 3.8+ and Git installed.
- [x] Add new file `addons/attribution.py` to the CodePi source.

## 2. Core Implementation
- [x] 2.1 Implement function to check for `.codepi.acknowledgement` existence.
- [x] 2.2 If missing, create file with proper content.
- [x] 2.3 Execute `git config --local commit.template .codepi.acknowledgement`.
- [x] 2.4 Integrate this function into CodePi’s startup routine.

## 3. Testing
- [x] 3.1 Unit tests: file creation, idempotence.
- [x] 3.2 Integration test: Git config command executed.
- [x] 3.3 Windows path handling test.

## 4. Documentation
- [ ] 4.1 Update README to mention automatic attribution.
- [ ] 4.2 Add section in `docs/usage.md`.
