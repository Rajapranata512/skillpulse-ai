# Privacy Policy for the SkillPulse AI Portfolio Demo

## Data handled

The local demo accepts CV text and job-description text pasted by the user. It returns
structured entities, an explainable match score, matched/missing evidence, and learning
priorities.

## Local retention

- Submitted text is processed in memory by the local API.
- The application does not write submitted CV/job text to files or a database.
- UI file upload is disabled.
- API access logs are disabled by the packaged launch command.
- Optional extraction feedback is generated only after explicit review as a browser download.
  It contains canonical labels and verdicts, not submitted text, matched text, source spans,
  or user identity; the application does not upload or persist it.
- Closing the local processes ends the application session.

Users should still use synthetic or redacted text for demonstrations. Do not paste names,
addresses, phone numbers, email addresses, identification numbers, credentials, or other
unnecessary personal information.

## Public repository data

The public repository must not contain:

- raw third-party job descriptions;
- real CVs or user-submitted text;
- human annotation working files or annotator-identifying notes;
- AI challenger workbooks or row-level processed datasets;
- credentials, environment files, private keys, local user paths, or academic/private
  documents outside the SkillPulse product scope.

Only attributed aggregate evidence, taxonomy/configuration, synthetic examples, and the
public-safe synthetic relevance candidate set are approved for publication.

## Scoring and protected attributes

SkillPulse scores explicit job requirements against explicit CV evidence. It does not use
protected attributes and must not be used for automatic hiring, rejection, or candidate
ranking. Outputs are decision support and include limitations and explanations.

## Public-deployment boundary

The approved target is one Render Free container in Singapore. Render terminates managed TLS;
Streamlit is public and FastAPI remains loopback-only. No database, persistent disk, secret,
feedback endpoint, or application-level retention is configured. API access logging and
Streamlit usage telemetry are disabled. Input length limits and a process-wide 30-analysis/minute
budget provide bounded abuse control without collecting IP addresses or identifiers.

Render remains a third-party processor for network and platform operational metadata under the
owner's workspace terms. The application does not intentionally put submitted text in logs.
The public URL must not be advertised until authenticated provisioning, log inspection, public
smoke verification, and rollback evidence pass according to the deployment runbook.
