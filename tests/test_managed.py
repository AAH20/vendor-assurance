import copy
import hashlib
import json
import tempfile
from pathlib import Path
import unittest
from vendor_assurance.managed import provision, connect, dispatch


class ManagedTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)/'state'
        provision(self.root)
        self.tokens={r:(self.root/(r+'.token')).read_text() for r in ('requester','approver','runner','reviewer')}
        self.now=1000
        self.job=self.call('requester','create',{'adapter':'local-postgres-synthetic-v1'})

    def tearDown(self): self.temp.cleanup()

    def call(self,role,action,body=None):
        return dispatch(self.root,self.tokens[role],action,body or {'id':self.job['id']},self.now)

    def running(self):
        self.call('approver','approve')
        return self.call('runner','claim')

    def submitted(self,changes=None):
        self.running()
        result=dict(status='exercise_passed_pending_human_review',synthetic=True,scenario='healthy',cleanup={'verified':True},application_checks={'restored_records':True,'committed_write':True},recovery_seconds=1,measured_data_age_seconds=1)
        result.update(changes or {})
        return self.call('runner','submit',{'id':self.job['id'],'result':result})

    def test_unknown_credential(self):
        with self.assertRaises(PermissionError): dispatch(self.root,'wrong','read',{'id':self.job['id']},self.now)

    def test_revoke_credential(self):
        with connect(self.root) as db: db.execute('UPDATE principals SET revoked=1 WHERE role=?',('requester',))
        with self.assertRaises(PermissionError): self.call('requester','read')

    def test_cross_tenant_read_denied(self):
        with connect(self.root) as db: db.execute('UPDATE principals SET tenant=? WHERE role=?',('other','reviewer'))
        with self.assertRaises(PermissionError): self.call('reviewer','read')

    def test_requester_cannot_approve(self):
        with self.assertRaises(PermissionError): self.call('requester','approve')

    def test_cannot_claim_before_approval(self):
        with self.assertRaises(ValueError): self.call('runner','claim')

    def test_duplicate_claim_denied(self):
        self.running()
        with self.assertRaises(ValueError): self.call('runner','claim')

    def test_expired_authorization(self):
        self.now=1900
        with self.assertRaises(PermissionError): self.call('approver','approve')

    def test_runtime_budget(self):
        self.running()
        self.now+=120
        with self.assertRaises(PermissionError): self.call('runner','check')
        self.assertEqual(self.call('reviewer','read')['effective_status'],'authorization_or_runtime_expired')

    def test_revoked_job_blocks_runner(self):
        self.running()
        self.call('approver','revoke')
        with self.assertRaises(PermissionError): self.call('runner','check')

    def test_failed_cleanup_cannot_accept(self):
        report=self.submitted({'cleanup':{'verified':False}})
        self.assertEqual(report['status'],'failed')
        with self.assertRaises(ValueError): self.call('reviewer','accept',{'id':report['id'],'result_sha256':report['result_sha256'],'rationale':'attempt'})

    def test_metrics_cannot_exceed_policy(self):
        report=self.submitted({'recovery_seconds':61})
        self.assertEqual(report['status'],'failed')

    def test_nan_metric_rejected(self):
        with self.assertRaises(ValueError): self.submitted({'recovery_seconds':float('nan')})

    def test_runner_cannot_accept(self):
        report=self.submitted()
        with self.assertRaises(PermissionError): self.call('runner','accept',{'id':report['id'],'result_sha256':report['result_sha256'],'rationale':'attempt'})

    def test_wrong_evidence_hash_denied(self):
        self.submitted()
        with self.assertRaises(ValueError): self.call('reviewer','accept',{'id':self.job['id'],'result_sha256':'wrong','rationale':'attempt'})

    def test_acceptance_and_no_replay(self):
        report=self.submitted()
        body={'id':report['id'],'result_sha256':report['result_sha256'],'rationale':'Reviewed scoped evidence'}
        self.assertEqual(self.call('reviewer','accept',body)['status'],'accepted')
        with self.assertRaises(ValueError): self.call('reviewer','accept',body)

    def test_custom_adapter_denied(self):
        with self.assertRaises(ValueError): self.call('requester','create',{'adapter':'shell','command':'anything'})

    def test_actor_cannot_self_approve(self):
        with connect(self.root) as db: db.execute('UPDATE principals SET actor=? WHERE role=?',('requester-demo','approver'))
        with self.assertRaises(PermissionError): self.call('approver','approve')

    def test_review_rationale_required(self):
        report=self.submitted()
        with self.assertRaises(ValueError): self.call('reviewer','accept',{'id':report['id'],'result_sha256':report['result_sha256'],'rationale':' '})
