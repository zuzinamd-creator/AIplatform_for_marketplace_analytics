# SMTP go-live checklist (Mail.ru / production)

Password reset (`POST /api/v1/auth/forgot-password`) returns **503** until SMTP is fully configured.

## Required `.env` variables

| Variable | Example | Notes |
|----------|---------|-------|
| `SMTP_HOST` | `smtp.mail.ru` | Already set |
| `SMTP_PORT` | `587` | STARTTLS |
| `SMTP_USE_TLS` | `true` | |
| `SMTP_USE_SSL` | `false` | |
| `SMTP_USER` | `your-mailbox@mail.ru` | Full mailbox login |
| `SMTP_PASSWORD` | *(app password)* | **Not** the web login password |
| `SMTP_FROM` | `your-mailbox@mail.ru` | Must match authorized sender |
| `APP_PUBLIC_URL` | `https://321997.fornex.cloud` | Used in reset links |

Optional (E2E email fetch): `IMAP_HOST=imap.mail.ru`, `IMAP_USER`, `IMAP_PASSWORD` (same app password).

## Mail.ru app password

1. Log in at [mail.ru](https://mail.ru) → **Settings → Security → App passwords**.
2. Create password for **External app** / SMTP.
3. Copy into `.env` as `SMTP_PASSWORD` (never commit to git).

## Secure credentials file (recommended on VPS)

```bash
install -m 600 /dev/null /root/.marketplace_smtp_credentials
# Edit: SMTP_USER=… SMTP_PASSWORD=… SMTP_FROM=…
bash scripts/smtp_apply_credentials.sh
systemctl restart marketplace-backend
```

## Verification steps

```bash
# 1. Config probe (no email sent)
python scripts/smtp_verify.py --check-only

# 2. Send test message
python scripts/smtp_verify.py --to your-mailbox@mail.ru

# 3. API forgot-password (dedicated test user only)
curl -sk -X POST "$APP_PUBLIC_URL/api/v1/auth/forgot-password" \
  -H 'Content-Type: application/json' \
  -d '{"email":"mvp-e2e-test@mail.ru"}'

# 4. Full E2E (IMAP fetch + reset + login)
python scripts/smtp_e2e_reset_password.py

# 5. Token edge cases
python scripts/password_recovery_validation.py

# 6. Browser: /forgot-password → email → /reset-password?token=… → login → /app/dashboard
```

## Post-go-live

- [ ] `scripts/ops_readiness_checks.sh` — no SMTP warning
- [ ] Rotate Mail.ru app password if exposed during setup
- [ ] Remove plaintext passwords from shell history / chat logs

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 503 on forgot-password | `SMTP_FROM` empty or `smtp_configured()` false | Set all four: HOST, USER, PASSWORD, FROM |
| 503 after 200 attempt | SMTP auth / network failure | Run `smtp_verify.py`, check Mail.ru app password |
| Link points to localhost | Wrong `APP_PUBLIC_URL` | Set to public HTTPS URL, restart backend |
| Email in spam | New sender | Mark as not spam; align `SMTP_FROM` with mailbox |
