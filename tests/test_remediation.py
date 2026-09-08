import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from vendor_assurance.remediation import assess, close, CHECKS

ROOT = Path(__file__).resolve().parents[1]
NOW = '2026-09-08T13:00:00Z'


class RemediationTests(unittest.TestCase):
    def setUp(self):
        self.bundle = json.loads((ROOT/'examples/remediation.json').read_text())

    def assess(self):
        return assess(self.bundle, 'synthetic-bank', NOW)

    def close(self, report=None, **kwargs):
        fields = dict(actor='Reviewer', role='human_closure_reviewer', rationale='Verified evidence')
        fields.update(kwargs)
        return close(self.bundle, report or self.assess(), 'synthetic-bank', NOW, **fields)

    def assertBlocked(self, reason):
        report = self.assess()
        self.assertEqual(report['status'], 'unverified')
        self.assertIn(reason, report['reasons'])
        with self.assertRaises(ValueError): self.close(report)

    def test_three_supported_checks(self):
        for check in CHECKS:
            with self.subTest(check=check):
                self.bundle['finding']['check']=check
                self.assertEqual(self.assess()['status'], 'eligible_for_human_closure')

    def test_human_closure_is_local(self):
        self.assertEqual(self.close()['status'], 'locally_reviewed_resolved')
        self.assertFalse(self.close()['external_action'])

    def test_tenant_denied(self):
        with self.assertRaises(PermissionError): assess(self.bundle, 'other', NOW)

    def test_agent_denied(self):
        with self.assertRaises(PermissionError): self.close(role='agent')

    def test_no_verification(self):
        self.bundle['observations'].pop()
        self.assertBlocked('missing_verification')

    def test_no_baseline(self):
        self.bundle['observations'].pop(0)
        self.assertBlocked('missing_baseline')

    def test_baseline_must_fail(self):
        self.bundle['observations'][0]['status']='pass'
        self.assertBlocked('invalid_baseline')

    def test_wrong_resource_fields(self):
        for field in self.bundle['finding']['identity']:
            with self.subTest(field=field):
                original=self.bundle['observations'][1]['identity'][field]
                self.bundle['observations'][1]['identity'][field]='different'
                self.assertBlocked('observation_identity_mismatch')
                self.bundle['observations'][1]['identity'][field]=original

    def test_wrong_definition_fields(self):
        for field in self.bundle['finding']['definition']:
            with self.subTest(field=field):
                original=self.bundle['observations'][1]['definition'][field]
                self.bundle['observations'][1]['definition'][field]='different'
                self.assertBlocked('check_definition_mismatch')
                self.bundle['observations'][1]['definition'][field]=original

    def test_nonpass_states(self):
        for status in ('fail','error','excluded','not_observed'):
            with self.subTest(status=status):
                self.bundle['observations'][1]['status']=status
                self.assertBlocked('verification_'+status)

    def test_predeployment_verification(self):
        self.bundle['observations'][1]['collected_at']='2026-09-08T10:30:00Z'
        self.assertBlocked('verification_not_after_deployment')

    def test_stale_verification(self):
        report=assess(self.bundle,'synthetic-bank','2026-09-10T13:00:00Z')
        self.assertIn('stale_verification',report['reasons'])

    def test_future_verification(self):
        self.bundle['observations'][1]['collected_at']='2026-09-09T12:00:00Z'
        self.assertBlocked('future_observation')

    def test_recurrence_overrides_pass(self):
        latest=copy.deepcopy(self.bundle['observations'][1])
        latest.update(id='recurrence',collected_at='2026-09-08T12:30:00Z',status='fail')
        self.bundle['observations'].append(latest)
        self.assertBlocked('verification_fail')

    def test_ambiguous_latest(self):
        latest=copy.deepcopy(self.bundle['observations'][1])
        latest['id']='ambiguous'
        self.bundle['observations'].append(latest)
        self.assertBlocked('ambiguous_latest_observation')

    def test_deployment_revision_mismatch(self):
        self.bundle['change']['deployment']['revision']='other'
        self.assertBlocked('deployment_revision_mismatch')

    def test_approval_revision_mismatch(self):
        self.bundle['change']['approval']['revision']='other'
        self.assertBlocked('approval_revision_mismatch')

    def test_failed_deployment(self):
        self.bundle['change']['deployment']['status']='failed'
        self.assertBlocked('deployment_not_successful')

    def test_agent_change_approval(self):
        self.bundle['change']['approval']['role']='agent'
        self.assertBlocked('change_not_human_approved')

    def test_postdeployment_approval(self):
        self.bundle['change']['approval']['at']='2026-09-08T11:30:00Z'
        self.assertBlocked('invalid_change_chronology')

    def test_report_tampering(self):
        report=self.assess()
        report['scope']='Everything secure'
        with self.assertRaises(ValueError): self.close(report)

    def test_bundle_change_invalidates_report(self):
        report=self.assess()
        self.bundle['finding']['owner']='new owner'
        with self.assertRaises(ValueError): self.close(report)

    def test_timezone_required(self):
        with self.assertRaises(ValueError): assess(self.bundle,'synthetic-bank','2026-09-08T13:00:00')

    def test_invalid_freshness_policy(self):
        for hours in (0,169,True):
            with self.subTest(hours=hours):
                with self.assertRaises(ValueError): assess(self.bundle,'synthetic-bank',NOW,hours)

    def test_duplicate_observation_rejected(self):
        self.bundle['observations'].append(copy.deepcopy(self.bundle['observations'][1]))
        with self.assertRaises(ValueError): self.assess()

    def test_cli_exports_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'closure'
            command=[sys.executable,'-m','vendor_assurance.remediation',str(ROOT/'examples/remediation.json'),'--tenant','synthetic-bank','--as-of',NOW,'--decision',str(ROOT/'examples/closure-reviewer.json'),'--output',str(output)]
            subprocess.run(command,cwd=ROOT,check=True,capture_output=True)
            package=json.loads((output/'closure.json').read_text())
            self.assertEqual(package['bundle'],self.bundle)
            self.assertFalse(package['decision']['external_action'])
            self.assertNotEqual(subprocess.run(command,cwd=ROOT,capture_output=True).returncode,0)


if __name__ == '__main__': unittest.main()
