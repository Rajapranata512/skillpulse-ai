# Security Policy

## Supported version

Security fixes apply to the latest commit on the public `main` branch. SkillPulse AI is a
portfolio demonstration and is not currently offered as a production hiring service.

## Reporting a vulnerability

Do not disclose vulnerabilities, credentials, personal data, or exploitable details in a
public issue. Use GitHub's private vulnerability-reporting or Security Advisory feature for
the repository. If private reporting is unavailable, contact the repository owner through
their GitHub profile without including sensitive payloads in the first message.

Include:

- affected component and commit;
- minimal reproduction steps;
- expected impact;
- whether credentials or personal data may be involved;
- a safe remediation suggestion, if available.

## Security boundaries

- API v1 is stateless and does not persist submitted CV or job text.
- Access logging is disabled by the packaged API command.
- Inputs are strict-schema validated and capped at 50,000 characters.
- The container runs as a non-root user and excludes raw data, annotations, reports,
  notebooks, CSV, and XLSX files from its build context.
- Protected personal attributes are not accepted as scoring features.

A future public deployment still requires TLS, rate limiting, allowed-origin policy,
abuse controls, dependency monitoring, secret management, retention verification,
observability, and rollback procedures.

## Publication controls

Every commit pushed by the project workflow must pass `scripts/publication_guard.py`. The
guard audits the exact staged/committed snapshot, denies raw and human-annotation data,
blocks academic/private artifacts and high-risk file types, and scans text for common
credentials, local user paths, email addresses, and Indonesian mobile numbers. Binary files
remain denied except three reviewed PNG paths pinned to exact SHA-256 values; the guard also
rejects tampering and embedded PNG text/EXIF metadata.

The guard is defense in depth, not a guarantee. Agents must still inspect the staged file
list and diff before every push. Force-pushes and bypassing the hook are prohibited by the
repository operating policy.
