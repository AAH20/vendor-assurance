import os
from pathlib import Path
import tempfile
import unittest
from vendor_assurance.recovery import run


class RecoveryInputTests(unittest.TestCase):
    def test_invalid_objectives(self):
        for limit in (0,-1,float('nan'),float('inf')):
            with self.subTest(limit=limit):
                with self.assertRaises(ValueError): run('unused-output',rto_seconds=limit)


@unittest.skipUnless(os.environ.get('A2Z_RECOVERY_INTEGRATION')=='1','opt-in real PostgreSQL integration')
class RecoveryIntegrationTests(unittest.TestCase):
    def exercise(self,scenario):
        with tempfile.TemporaryDirectory() as temporary:
            report=run(Path(temporary)/'evidence',scenario)
            self.assertTrue(report['cleanup']['verified'],report)
            self.assertEqual(report['human_acceptance'],'pending')
            return report

    def test_real_restore_and_transaction(self):
        report=self.exercise('healthy')
        self.assertEqual(report['status'],'exercise_passed_pending_human_review',report)
        self.assertTrue(report['application_checks']['committed_write'])

    def test_corrupt_backup_blocked(self):
        report=self.exercise('corrupt_backup')
        self.assertEqual(report['status'],'failed')
        self.assertIn('integrity',report['failure'])

    def test_missing_database_blocks_success(self):
        report=self.exercise('missing_dependency')
        self.assertEqual(report['status'],'failed')
        self.assertIn('503',report['failure'])

    def test_wrong_application_schema_blocks_success(self):
        report=self.exercise('invalid_application')
        self.assertEqual(report['status'],'failed')
        self.assertIn('503',report['failure'])

    def test_stale_recovery_point_blocks_success(self):
        report=self.exercise('stale_data')
        self.assertEqual(report['status'],'failed')
        self.assertIn('recovery-point',report['failure'])

    def test_missed_rto_blocks_success(self):
        report=self.exercise('rto_exceeded')
        self.assertEqual(report['status'],'failed')
        self.assertIn('recovery time',report['failure'])

    def test_control_revocation_stops_and_cleans(self):
        calls=0
        def guard():
            nonlocal calls
            calls+=1
            if calls>=4: raise PermissionError('authorization revoked')
        with tempfile.TemporaryDirectory() as temporary:
            report=run(Path(temporary)/'evidence',control_check=guard)
            self.assertEqual(report['status'],'failed')
            self.assertIn('revoked',report['failure'])
            self.assertTrue(report['cleanup']['verified'])
