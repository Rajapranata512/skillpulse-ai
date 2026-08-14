# SkillPulse AI public deployment — Render Free

This runbook freezes the first public deployment target. It is a portfolio demonstration,
not a production hiring system.

## Approved boundary

- Target: one Render Web Service using `deploy/render/Dockerfile` and `render.yaml`.
- Region: Singapore.
- Cost ceiling: Free instance only; do not add a payment method or upgrade automatically.
- Public surface: Streamlit on Render's managed HTTPS endpoint.
- Private surface: FastAPI binds only to `127.0.0.1:8000` inside the same container.
- Storage: no database, persistent disk, object storage, feedback endpoint, or raw-text retention.
- Logs: Uvicorn access logging and Streamlit usage telemetry are disabled. Application code does
  not log request bodies; platform operational metadata remains governed by the Render workspace plan.
- Abuse control: 50,000-character contract limit plus a process-wide 30 analysis requests/minute
  budget. The limiter collects no IP address or user identifier.
- Deployment trigger: only after linked GitHub checks pass.

Render Free is appropriate for a portfolio preview, not production. It has 512 MB memory, a single
instance, an ephemeral filesystem, and spins down after 15 idle minutes; a cold start can take about
one minute. The workspace receives 750 free instance-hours monthly. These limitations must remain
visible to reviewers.

## Provisioning

1. Confirm `main` is green and the publication guard passed.
2. Sign in to Render using the repository owner's account.
3. Open the [Render Blueprint flow](https://render.com/deploy?repo=https://github.com/Rajapranata512/skillpulse-ai).
4. Confirm the Blueprint creates exactly one Free web service in Singapore with no database/disk.
5. Do not add secrets: this deployment requires none.
6. Wait for `/_stcore/health` to pass, then record the assigned HTTPS URL privately first.

Provisioning changes external infrastructure and requires the authenticated owner session. Never put
Render API keys, workspace identifiers, private logs, or dashboard URLs in Git.

## Verification

Run the public-safe smoke test without submitting CV or job text:

```powershell
skillpulse-deployment-smoke https://<assigned-service>.onrender.com
```

The check requires HTTPS, a healthy Streamlit endpoint, a rendered landing shell, and confirms that
the FastAPI metadata endpoint is not directly exposed. Then complete one browser journey using only
the built-in synthetic examples and verify no request content appears in application logs.

## Monitoring

- Render health path: `/_stcore/health`.
- Internal dependency health: `http://127.0.0.1:8000/health`, checked by the runtime before UI start.
- GitHub Actions remains the release gate for tests, dependency audit, publication guard, browser QA,
  and CodeQL.
- Free-tier uptime is not an SLO. Record cold-start or availability limitations; do not market this as
  a production service.

## Rollback

1. In Render, open the service's **Deploys** page.
2. Select the most recent known-good deploy and choose **Rollback**.
3. Render Free retains rollback access only to the two most recent previous deploys.
4. Confirm `/_stcore/health`, rerun `skillpulse-deployment-smoke`, and inspect application logs for
   operational errors only.
5. Keep auto-deploy disabled after rollback until the faulty commit is corrected and CI is green;
   then re-enable the checks-passed trigger.

If privacy, rate limiting, health, or loopback isolation cannot be verified, suspend the service rather
than accepting a degraded public boundary.
