# Phase 3S — protected read-only API and deployment procedure

## Scope and defaults

The API is still read-only. An administrator credential grants access to research,
model and operational **views**, not training, promotion, acquisition or execution.
There are no administrative write/job/backup endpoints or broker routes.

- `/health` and `/health/live` are minimal public liveness checks: no journal,
  model, source, path or credential details.
- `/health/ready` requires administrator authentication. It checks API storage
  readability, not quantitative/model readiness or host uptime.
- Existing forecast/level/auction/market/shadow-history views require reader or
  administrator authentication. Research/model status, operational/data health,
  revisions/reconciliations and verification views require administrator access.
- Unconfigured credentials fail closed (503) for protected paths; invalid/missing
  credentials get 401, insufficient roles 403. OpenAPI/docs HTTP endpoints are
  disabled. New/unlisted paths default to administrator authorization.
- HTTP mutation methods are rejected. Forecasts, immutable records, source snapshots
  and models are never changed by a GET or by possessing an API credential.

Route names and successful response contracts are preserved except the intentional
`/health` split. Existing HTTP clients must now send a credential; detailed health
moves to protected `/health/ready`. Direct Python service interfaces remain usable.
`SecurityPolicy.internal()` is an explicit embedded/test compatibility option,
restricted to loopback peers; the CLI/environment never enables that bypass.

## Configure secrets without logging them

Create separate random reader/admin token files in an operator-approved private
location, outside public Git. Use `secrets.token_urlsafe(32)` and exclusive file
creation, not a password copied into a command argument. Do not print the values
or send them in chat. Tokens must be 32–128 URL-safe characters and must differ.

Set only file paths in the service environment:

```powershell
$env:NOCTURNE_API_READER_TOKEN_FILE = '<private-reader-token-file>'
$env:NOCTURNE_API_ADMIN_TOKEN_FILE = '<private-administrator-token-file>'
$env:NOCTURNE_API_ALLOWED_HOSTS = 'localhost,127.0.0.1,[::1]'
```

The server stores SHA-256 digests, compares them in constant time and never logs
tokens/headers. POSIX token files must be owner-only; Windows owner/service-account
ACLs must be reviewed by the operator. No ACL, password, account or host security
policy was modified here. Rotation requires replacement files and controlled API
restart; use separate administrative credentials and avoid sharing them broadly.
Do not confuse these API access credentials with `DATABENTO_API_KEY`.

Clients send `Authorization: Bearer <token>` over TLS. Do not put tokens in URLs,
query parameters, source control, task arguments, plain logs or screenshots.

## TLS and network binding

With an operator-provided certificate chain and protected private key:

```powershell
./deploy/serve-local-tls.ps1 -Python <locked-venv-python> -CertificateFile <server-chain.pem> -PrivateKeyFile <private-key.pem> -Port 8443
```

This launcher binds loopback only. The CLI refuses non-loopback binding unless
explicit `--allow-remote`, configured authentication and both TLS files are supplied.
That flag is an operator deployment capability, not approval granted by this phase.
No public listener or paid resource was activated. Do not expose a raw `uvicorn`
import outside this reviewed profile or enable arbitrary trusted forwarded headers.

The isolated TLS test creates an ephemeral certificate, verifies hostname and trust
using an explicit CA file, negotiates TLS 1.2/1.3, checks authenticated/unauthenticated
responses, rejects plaintext access and closes its loopback listener. It never
installs a CA into the OS trust store or disables verification. Test certificates
are not production certificates. Production issuance, renewal, revocation and
network/firewall approval remain operator responsibilities.

CLI transport: one worker, proxy headers disabled, access logs disabled, concurrency
32, keep-alive 5s, bounded graceful shutdown 5s and incomplete HTTP-event limit 16KiB.
The server-side SSL context uses modern TLS defaults and ECDHE AEAD ciphers. This
is not a TLS-flood/OS resource-isolation or high-availability certification.

## Request protection and audit policy

`api/security.py` implements a pure-ASGI perimeter:
- Host allowlist, 2KiB path / 4KiB query limits, 100 headers / 16KiB header budget.
- 64KiB body budget by both declared and observed bytes; duplicate/ambiguous length,
  length mismatch, excess fragments and total body-read timeout (5s) are rejected.
- Instrument/session validation rejects path traversal and overlong values.
- Default 120 requests/minute per peer and 60/minute per accepted credential role;
  no X-Forwarded-For trust. Peer tracking is bounded (1,024 entries); a full active
  table rejects new entries, rather than growing indefinitely or evicting limits.
- This limiter is **per process**, not a distributed/global gateway. One worker is
  the supported profile. A future multi-instance deployment needs a reviewed shared
  limiter and network-level connection controls; load/security review remains open.
- Responses are no-store, nosniff, no-referrer and CSP-restricted; HTTPS includes HSTS.

Each response is gated on an append/fsync audit event. Only generated request ID,
timestamp, known route template (or UNMATCHED), bounded method, role and status are
recorded. No IP, query, raw unknown path, header, body, token or secret is logged.
Default private path: ignored `data/security/api-audit.jsonl`. A failed audit write
never releases protected response data. Audit capacity is bounded at 8MiB; at
capacity the API fails closed until an operator archives/rotates the log. No audit
history is deleted automatically. Monitor capacity and authenticated readiness.

Current evidence is functional/isolated testing, not penetration testing, independent
security approval, distributed denial-of-service protection or a production SLA.

## Windows and future always-on profiles

`deploy/local-windows.json` and `deploy/always-on.json` describe intended operating
conditions and activate nothing. Existing console-free pythonw scheduling remains.
Both installers support Interactive mode and explicitly credentialed Password mode;
Password mode includes startup plus repeating triggers, Limited principal and
existing retry/time budgets. Neither installer overwrites an existing task.

Dry-run only (no credential required or persisted):

```powershell
./scripts/install_shadow_task.ps1 -TaskName Nocturne-Shadow-Review -LogonMode Password -WhatIf
./scripts/install_research_task.ps1 -TaskName Nocturne-Research-Review -LogonMode Password -WhatIf
```

Actual unattended registration requires operator approval and a `PSCredential`
supplied interactively, never a plaintext password argument. Windows Task Scheduler
protects the submitted credential. No service account was created, no existing
task principal/security setting changed, and reboot/logoff operation was not tested.
Current deployed tasks remain Interactive/awake/logged-in only. Hard memory
isolation, independent paging, long soak and separate-host cutover remain partial.

## Encrypted backup and recovery

Capture using existing coherent snapshot/deadline admission first. Then use the
new packaging CLI; it never captures mutable live files itself:

```powershell
python scripts/phase3s_backup.py keygen --key-file <new-private-key-outside-repository>
python scripts/phase3s_backup.py pack --snapshot <verified-snapshot> --output <new-private-ciphertext.nct> --key-file <separate-key-file> --report <pack-report.json>
python scripts/phase3s_backup.py restore --archive <trusted-ciphertext.nct> --destination <new-private-restore-root> --key-file <separate-key-file> --report <restore-report.json>
```

Packaging uses AES-256-GCM, fresh 96-bit nonces, authenticated schema/cipher/header
and original manifest binding. It streams in bounded chunks, retains original
snapshot bytes and refuses existing outputs. Wrong key, modified ciphertext or
header and truncation cannot create a final restored directory. GCM authentication
finishes before archive extraction; temporary plaintext staging is confined to the
chosen private parent and removed afterward. Unsafe paths, links, duplicate or
unexpected members and size/count limits are checked before final restoration.

The existing allowlisted snapshot scope excludes configuration/secrets directories.
Packaging additionally rejects secret-file names, private-key markers and supplied
known values (configured provider keys, API token-file values and the backup key),
including values spanning chunks. This is tested exclusion, **not exhaustive DLP**
for unknown/encoded secrets. Review licensed-data permissions and unknown contents
before any off-host transfer. Key material is not logged, packaged or committed.
The CLI key generator refuses repository paths; protect Windows ACLs and keep
independent key custody. Losing the key prevents recovery.

The real drill used a new local demo key, separate from the ignored encrypted
snapshot. It is evidence of local packaging/restoration, not production key custody
or a durable off-host backup. Existing plaintext source/snapshot copies are not
deleted or retroactively encrypted by this tool. Full-volume protections and
retention are operator responsibilities.

Proposed RPO 30m/RTO 60m remain unapproved off-host objectives. Local elapsed times
exclude host provisioning, transfer, secrets, scheduler registration and cutover.
Status stays **OFF_HOST_VERIFICATION_REQUIRED** until an authorized independent
destination, encryption/key-custody policy and genuine restore drill are supplied.
Use the existing 3Q/3R runbooks for path-compatible state resumption and rollback;
do not activate the isolated restored issuer alongside the live one.
