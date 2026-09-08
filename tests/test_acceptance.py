import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from vendor_assurance import acceptance as a


def grant():
    now = datetime.now(timezone.utc)
    return dict(schema_version=1, mode='synthetic', tenant='test', package=a.PACKAGE,
                package_sha256=a.package_digest(), revoked=False,
                purpose='local_synthetic_acceptance', authorization_reference='synthetic-test-only',
                requester='requester', approver='approver',
                valid_from=(now-timedelta(seconds=1)).isoformat(),
                expires_at=(now+timedelta(minutes=10)).isoformat())


def report():
    return dict(status='exercise_passed_pending_human_review', synthetic=True,
                cleanup={'verified': True}, application_checks={'restored_records': True, 'committed_write': True})


class AcceptanceTests(unittest.TestCase):
    def test_reject_scope_before_execution(self):
        for field, value in [('tenant', 'other'), ('mode', 'live'), ('revoked', True),
                             ('package_sha256', 'bad'), ('approver', 'requester'),
                             ('purpose', 'restore'), ('expires_at', '2000-01-01T00:00:00Z')]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp)/'grant.json'
                data = grant(); data[field] = value
                path.write_text(json.dumps(data))
                with patch.object(a.recovery, 'run') as runner:
                    with self.assertRaises(ValueError):
                        a.execute(path, 'test', Path(tmp)/'result')
                    runner.assert_not_called()

    def test_binding_and_missing_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'grant.json'; path.write_text(json.dumps(grant()))
            with patch.object(a.recovery, 'run', return_value=report()):
                receipt = a.execute(path, 'test', Path(tmp)/'result')
            self.assertTrue(a.verify(receipt, 'test'))
            self.assertFalse(a.verify(receipt, 'other'))
            changed = copy.deepcopy(receipt); changed['report']['cleanup']['verified'] = False
            self.assertFalse(a.verify(changed, 'test'))
            for field in ['cleanup', 'application_checks', 'status']:
                bad = report(); del bad[field]
                self.assertFalse(a.eligible(bad))

    def test_revocation_after_adapter_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'grant.json'; data = grant(); path.write_text(json.dumps(data))
            def revoke(*args, **kwargs):
                data['revoked'] = True; path.write_text(json.dumps(data))
                return report()
            with patch.object(a.recovery, 'run', side_effect=revoke):
                receipt = a.execute(path, 'test', Path(tmp)/'result')
            self.assertFalse(receipt['eligible_for_review'])
            self.assertFalse(a.verify(receipt, 'test'))

    def test_grant_lifetime_and_timezone(self):
        data = grant(); data['expires_at'] = '2099-01-01T00:00:00Z'
        with self.assertRaises(ValueError):
            a.authorize(data, 'test', datetime.now(timezone.utc))
        data = grant(); data['valid_from'] = '2020-01-01T00:00:00'
        with self.assertRaises(ValueError):
            a.authorize(data, 'test', datetime.now(timezone.utc))
