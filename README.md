# Journal Status Monitor

Python + GitHub Actions tool for monitoring manuscript statuses in journal submission systems and sending email notifications when statuses change.

## Current capabilities

- IEEE ScholarOne monitoring with browser automation.
- Generic Elsevier Editorial Manager login and table parsing support.
- Manual run modes: `normal`, `test`, and `daily_report`.
- Email notification with SMTP auto-detection for common providers.
- Persistent status comparison in `data/manuscripts.json`.
- Debug screenshots/HTML generation when parsing fails.

## Important privacy note

`data/manuscripts.json` may contain manuscript titles, IDs, statuses, and submission-system URLs. Use a private repository for real submissions, or disable committing that data if the repository must remain public.

## Required GitHub Secrets

Configure at least one platform account:

| Secret | Description |
| --- | --- |
| `IEEE_EMAIL` | IEEE ScholarOne login email |
| `IEEE_PASSWORD` | IEEE ScholarOne password |
| `IEEE_URL` | Journal-specific ScholarOne URL |
| `ELSEVIER_EMAIL` | Elsevier / Editorial Manager login email |
| `ELSEVIER_PASSWORD` | Elsevier / Editorial Manager password |
| `ELSEVIER_URL` | Journal-specific Editorial Manager URL |

Email notification secrets:

| Secret | Description |
| --- | --- |
| `EMAIL_SENDER` | Sender email address |
| `EMAIL_PASSWORD` | SMTP authorization code or app password |
| `EMAIL_RECEIVER` | Recipient email address. Comma-separated values are supported. |
| `SMTP_SERVER` or `SMTP_HOST` | Optional SMTP host override |
| `SMTP_PORT` | Optional SMTP port override, usually `465` or `587` |

## Run modes

- `test`: sends a test email only.
- `normal`: fetches statuses, updates storage, and sends email only when status changes.
- `daily_report`: fetches statuses, updates storage, and sends all current manuscript statuses.

Manual test:

1. Open the repository Actions tab.
2. Select `Journal Status Monitor`.
3. Click `Run workflow`.
4. Select `test` first to verify email.
5. Then run `normal`.

## Local usage

```bash
pip install -r requirements.txt
python monitor.py --mode test
python monitor.py --mode normal
python monitor.py --mode daily_report
```

Set environment variables from `.env.example` before local use.

## Reliability limits

Publisher submission systems change their page structure and may require MFA, CAPTCHA, or institution login. If a run fails, inspect debug screenshots and HTML snapshots for troubleshooting.