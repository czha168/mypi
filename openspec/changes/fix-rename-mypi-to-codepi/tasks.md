# Tasks: Rename mypi to codepi

## 1. Setup
- [ ] 1.1 Verify current strings (welcome message) in codebase

## 2. Branding Update
- [ ] 2.1 Update CLI welcome message string from "mypi" to "codepi"
- [ ] 2.2 Update any other identifiable "mypi" strings in user-facing outputs

## 3. Config Path Migration
- [ ] 3.1 Update configuration path module to use `~/.codepi` by default
- [ ] 3.2 Implement migration logic: check for `~/.mypi` and move to `~/.codepi`
- [ ] 3.3 Verify the migration logic works as expected

## 4. Verification
- [ ] 4.1 Test CLI with new welcome message
- [ ] 4.2 Test config path update and migration functionality
