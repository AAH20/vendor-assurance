# Security

The optional managed pilot module adds authenticated loopback HTTP job operations using provisioned bearer credentials. Its limits are documented in [managed-pilot.md](docs/managed-pilot.md): no TLS/public hosting, no enterprise human identity, no independent runner attestation, and no hard compute quotas. Keep generated `*.token` files and `control.db` private; the demo's acceptance is simulated. This module does not turn the older trusted-local APIs below into authenticated services.

This is an offline trusted-operator reference. Do not expose its Python functions or CLI to remote callers as an authenticated service. Tenant and human-role arguments are assertions by the local operator. Use only synthetic or explicitly authorized records in a suitably protected local environment. Generated HTML escapes source text and has no scripts; exports still contain confidential source material when real bundles are used.

Report vulnerabilities privately using GitHub private vulnerability reporting where enabled. Do not attach customer evidence, credentials or personal information to public issues. Security fixes should include regression coverage for the violated boundary. No claim of production readiness, regulatory certification or immutable audit logging is made.
