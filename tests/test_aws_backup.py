import copy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import Mock
from vendor_assurance.aws_backup import collect, review, timestamp
from vendor_assurance.core import digest

ROOT=Path(__file__).resolve().parents[1]/'examples/aws-backup'
NOW=timestamp('2026-09-08T12:00:00Z')


class AWSBackupTests(unittest.TestCase):
    def setUp(self):
        self.grant=json.loads((ROOT/'grant.json').read_text())
        self.capture=json.loads((ROOT/'capture.json').read_text())
        self.app=json.loads((ROOT/'application.json').read_text())

    def review(self): return review(self.grant,self.capture,self.app,'synthetic-bank',NOW)
    def rehash(self): self.capture['response_sha256']=digest(self.capture['response'])

    def clients(self):
        self.grant['mode']='authorized'
        sts=Mock()
        sts.get_caller_identity.return_value={'Account':self.grant['account'],'Arn':self.grant['caller_arn'],'UserId':'synthetic'}
        backup=Mock()
        backup.describe_restore_job.return_value=self.capture['response']
        return sts,backup

    def test_full_fixture_eligible_but_not_accepted(self):
        result=self.review()
        self.assertEqual(result['status'],'eligible_for_human_review')
        self.assertEqual(result['human_acceptance'],'pending')
        self.assertEqual(result['recovery_seconds'],720)
        self.assertEqual(result['recovered_data_age_seconds'],60)

    def test_no_application_means_unverified(self):
        self.app=None
        self.assertIn('application_evidence_missing',self.review()['reasons'])

    def test_aws_states_independent(self):
        for field in ('Status','ValidationStatus','DeletionStatus'):
            with self.subTest(field=field):
                original=self.capture['response'][field]
                self.capture['response'][field]='FAILED'
                self.rehash()
                self.assertEqual(self.review()['status'],'unverified')
                self.capture['response'][field]=original
        self.rehash()

    def test_wrong_account_denied(self):
        self.capture['response']['AccountId']='111111111111'
        self.rehash()
        with self.assertRaises(PermissionError): self.review()

    def test_wrong_job_denied(self):
        self.capture['response']['RestoreJobId']='other'
        self.rehash()
        with self.assertRaises(PermissionError): self.review()

    def test_wrong_recovery_point_denied(self):
        self.capture['response']['RecoveryPointArn']='other'
        self.rehash()
        with self.assertRaises(PermissionError): self.review()

    def test_wrong_target_blocks_application(self):
        self.app['created_resource_arn']='other'
        self.assertEqual(self.review()['status'],'unverified')

    def test_composite_job_rejected(self):
        self.capture['response']['IsParent']=True
        self.rehash()
        with self.assertRaises(ValueError): self.review()

    def test_source_type_rejected(self):
        self.capture['response']['ResourceType']='Aurora'
        self.rehash()
        with self.assertRaises(ValueError): self.review()

    def test_tenant_denied(self):
        with self.assertRaises(PermissionError): review(self.grant,self.capture,self.app,'other',NOW)

    def test_tampered_response(self):
        self.capture['response']['Status']='FAILED'
        with self.assertRaises(ValueError): self.review()

    def test_future_capture_unverified(self):
        self.capture['collected_at']='2026-09-08T13:00:00Z'
        self.assertIn('stale_or_future_capture',self.review()['reasons'])

    def test_job_time_is_not_application_time(self):
        self.app['validation_completed_at']='2026-09-08T10:09:00Z'
        self.assertIn('invalid_application_timeline',self.review()['reasons'])

    def test_recovery_point_date_not_transaction_age(self):
        del self.app['latest_recovered_transaction_at']
        self.assertIsNone(self.review()['recovered_data_age_seconds'])
        self.assertEqual(self.review()['status'],'unverified')

    def test_app_check_must_be_boolean(self):
        self.app['checks']['committed_write']='true'
        self.assertEqual(self.review()['status'],'unverified')

    def test_wrong_application_recipe(self):
        self.app['application_test_sha256']='2'*64
        self.assertEqual(self.review()['status'],'unverified')

    def test_expiry_before_network(self):
        sts,backup=self.clients()
        self.grant['expires_at']='2026-09-08T11:00:00Z'
        with self.assertRaises(PermissionError): collect(lambda:self.grant,sts,backup,lambda:NOW)
        sts.get_caller_identity.assert_not_called()
        backup.describe_restore_job.assert_not_called()

    def test_wrong_aws_identity_before_backup_read(self):
        sts,backup=self.clients()
        sts.get_caller_identity.return_value['Arn']='other'
        with self.assertRaises(PermissionError): collect(lambda:self.grant,sts,backup,lambda:NOW)
        backup.describe_restore_job.assert_not_called()

    def test_revocation_during_collection(self):
        sts,backup=self.clients()
        revoked=copy.deepcopy(self.grant)
        revoked['revoked']=True
        loader=Mock(side_effect=[self.grant,revoked])
        with self.assertRaises(PermissionError): collect(loader,sts,backup,lambda:NOW)
        backup.describe_restore_job.assert_not_called()

    def test_only_named_read_operation(self):
        sts,backup=self.clients()
        result=collect(lambda:self.grant,sts,backup,lambda:NOW)
        self.assertEqual(backup.method_calls,[unittest.mock.call.describe_restore_job(RestoreJobId=self.grant['restore_job_id'])])
        self.assertEqual(result['transport'],'boto3')

    def test_synthetic_grant_blocks_collection(self):
        sts,backup=Mock(),Mock()
        with self.assertRaises(PermissionError): collect(lambda:self.grant,sts,backup,lambda:NOW)
        sts.get_caller_identity.assert_not_called()

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError): timestamp('2026-09-08T00:00:00')

    @unittest.skipUnless(importlib.util.find_spec('boto3'),'optional AWS SDK')
    def test_official_sdk_stubber_roundtrip(self):
        import boto3
        from botocore.stub import Stubber
        from botocore.config import Config
        self.grant['mode']='authorized'
        session=boto3.Session(aws_access_key_id='synthetic',aws_secret_access_key='synthetic',region_name='eu-west-1')
        config=Config(ignore_configured_endpoint_urls=True)
        sts=session.client('sts',config=config)
        backup=session.client('backup',config=config)
        job=copy.deepcopy(self.capture['response'])
        for key in ('CreationDate','CompletionDate','RecoveryPointCreationDate'):
            job[key]=datetime.fromtimestamp(timestamp(job[key]),timezone.utc)
        with Stubber(sts) as s, Stubber(backup) as b:
            s.add_response('get_caller_identity',{'Account':self.grant['account'],'Arn':self.grant['caller_arn'],'UserId':'synthetic'}, {})
            b.add_response('describe_restore_job',job,{'RestoreJobId':self.grant['restore_job_id']})
            result=collect(lambda:self.grant,sts,backup,lambda:NOW)
            self.assertEqual(result['response']['Status'],'COMPLETED')
            s.assert_no_pending_responses()
            b.assert_no_pending_responses()
