"""Print a short-lived LOCAL SYNTHETIC grant. This is not customer authorization."""
from datetime import datetime, timedelta, timezone
import json
from vendor_assurance.acceptance import PACKAGE, package_digest
now = datetime.now(timezone.utc)
print(json.dumps(dict(schema_version=1, mode='synthetic', tenant='synthetic-bank',
    package=PACKAGE, package_sha256=package_digest(), revoked=False,
    purpose='local_synthetic_acceptance', authorization_reference='local-synthetic-demo',
    requester='simulated-requester', approver='simulated-approver',
    valid_from=now.isoformat(), expires_at=(now+timedelta(minutes=10)).isoformat()), indent=2))
