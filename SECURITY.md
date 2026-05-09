# Security policy

## Reporting a vulnerability

Please do **not** open a public GitHub issue for security problems.

Use GitHub's [private vulnerability reporting](https://github.com/socialpyre/postpit/security/advisories/new)
form instead. We aim to acknowledge reports within a few business days.

## Supported versions

postpit is pre-1.0 software. Only the latest released version receives security
fixes; we do not backport.

## Scope

postpit is a developer tool intended to run on a developer's local machine or in
CI. It is **not** designed to be exposed to the public internet. Issues that
require an attacker to already be on your local network or to have shell access
to the host are out of scope.

In-scope concerns include:

- Vulnerabilities in the request capture / mock-API layer that affect users
  running the tool locally as documented.
- Code that allows traversal outside of the configured `POSTPIT_DATABASE`
  directory.
- Template injection or XSS in the inbox UI.

Out of scope:

- Upstream vulnerabilities in dependencies (report those upstream).
- Findings that require modifying postpit's own code or configuration.
- Generic CSRF/XSS guidance not tied to a specific defect.
