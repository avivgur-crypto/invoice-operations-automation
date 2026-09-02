# Security

This repository contains portfolio-safe sample data only.

## Credential handling

- Never commit API tokens, refresh tokens, service-account files, spreadsheet IDs, or production exports.
- Use environment variables locally and encrypted repository secrets in CI.
- Dry-run mode is the default; writes require the explicit `--apply` flag.
- Rotate any credential immediately if it appears in a commit, log, screenshot, or issue.

## Reporting a problem

Please do not open a public issue for a suspected secret exposure. Contact the repository owner privately through the profile contact details.
