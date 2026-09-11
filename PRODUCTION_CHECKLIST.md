# Production Deployment Checklist (Prompt 17)

This checklist outlines the mandatory security, reliability, and architectural requirements for deploying the **Vision-Based Defect Detection** industrial quality inspection platform into production.

---

## 1. Security & Cryptographic Hardening
- [ ] **Generate a Strong `SECRET_KEY`**: Never use the development default string. Generate a high-entropy 256-bit or 512-bit key using OpenSSL or Python:
  ```bash
  python3 -c "import secrets; print(secrets.token_hex(32))"
  ```
  Set this value in production `.env` as `SECRET_KEY=<generated_value>`.
- [ ] **Disable Flask Debug Mode**: Ensure `DEBUG=False` (default in production Gunicorn entrypoint). Never expose the Werkzeug interactive debugger in a reachable environment.
- [ ] **Enforce HTTPS / TLS 1.3**: Terminate TLS at the reverse proxy (Nginx / Cloud Run / AWS ALB) with valid certificates (Let's Encrypt / DigiCert). Redirect all HTTP traffic to HTTPS.
- [ ] **Strict CORS Whitelist**: Configure `ALLOWED_ORIGINS` in `.env` to match only trusted plant intranet domains (e.g. `https://inspection.factory.local`), avoiding wildcard `*` headers.
- [ ] **Session Cookie Attributes**: Ensure session cookies have `HttpOnly=True`, `Secure=True`, and `SameSite=Lax`.

---

## 2. Database Migration & Durability
- [ ] **Switch from SQLite to Managed PostgreSQL**:
  - In `.env`, set `DATABASE_TYPE=postgres`.
  - Set `DATABASE_URL=postgresql://defect_user:<password>@<db-host>:5432/defect_detection`.
  - Use connection pooling (e.g. PgBouncer or SQLAlchemy queue pool) to support concurrent line workers.
- [ ] **Automated Database Backups**:
  - Configure daily automated snapshots and WAL point-in-time recovery (PITR) with at least 30 days retention.
  - Test test-restore procedures quarterly to verify backup integrity.
- [ ] **Data Retention Policies**:
  - Archive inspections older than 180 days to cold object storage (S3 / GCS) to maintain high table indexing speed.

---

## 3. Web Server & Process Management
- [ ] **Production WSGI Application Server**: Run via Gunicorn with 4–8 worker processes:
  ```bash
  gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 --access-logfile - --error-logfile - src.app:app
  ```
- [ ] **Reverse Proxy (Nginx / Cloud Gateway)**:
  - Configure client body max size: `client_max_body_size 15M;` (matching `MAX_UPLOAD_SIZE=10485760`).
  - Configure upstream proxy timeouts (`proxy_read_timeout 120s;`) to accommodate batch image inferences.
  - Enable gzip/brotli compression for static CSS and JavaScript bundles.
- [ ] **Rate Limiting Protection**:
  - Verify Flask-Limiter is enforcing limits (`20 per minute` on `/analyze`, `/ai-scan`, `/login`).
  - Prevent Denial of Service (DoS) from misconfigured camera sensors or brute-force credential attacks.

---

## 4. Storage & Logging Operations
- [ ] **Upload Disk Space Quota & Cleanup**:
  - Mount persistent volume to `/app/uploads`.
  - Schedule a cron job or systemd timer to purge temporary upload directories older than 48 hours:
    ```bash
    find /app/uploads -type f -mtime +2 -delete
    ```
- [ ] **Log Rotation & Monitoring**:
  - RotatingFileHandler configured to rotate every 10 MB with 5 backups (`logs/app.log`).
  - Ship structured JSON logs to a centralized aggregator (Datadog, Grafana Loki, or Google Cloud Logging).
- [ ] **Automated Health Monitoring**:
  - Wire infrastructure alerts to `GET /health` every 30 seconds.
  - Alert on HTTP 5xx responses, model loading status, or disk space free falling below 15%.

---

## 5. Multimodal AI Scan & Model Integrity
- [ ] **Protect AI Provider Secrets**:
  - Store `GEMINI_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY` in secure secret managers (GCP Secret Manager / AWS Secrets Manager / Vault), never in code repositories.
- [ ] **Model Weight Verification**:
  - Verify SHA-256 checksums of trained PyTorch model checkpoints in `models/` prior to container deployment.
  - Maintain version traceability with `GET /version`.
