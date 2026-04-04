# Proposal for Adding Automated Attribution Functionality

## Why
CodePi aims to streamline the contribution workflow for developers working locally.  At the moment
developers must manually add a `Co‑authored‑by` line in the commit message or set up a template
file on each repository.  This change will add a lightweight, zero‑configuration mechanism that
automatically creates a `.codepi.acknowledgement` file at repository startup.  The file will contain a
blank line followed by the standard `Co‑authored‑by:` tag, and the file will be added to the local
Git configuration as the commit message template.  The result is that any commit made after this
step will automatically include the attribution line, reducing friction and preventing accidental
omission.

## What Changes
- Create a `.codepi.acknowledgement` file in the repository root if it does not exist.
- Populate the file with a blank line and `Co‑authored-by: CodePi <codepi@users.noreply.github.com>`.
- Configure Git to use that file as the commit message template via `git config --local commit.template`.

## Capabilities
1. **auto-attribution** – Detects missing template file and creates it.
2. **git-configuration** – Sets the local Git config for commit templates.

## Impact
On every repository where CodePi is initialized, the above steps will be run automatically.
The only external dependency is a working Git installation.
