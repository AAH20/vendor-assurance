import copy
import json
from pathlib import Path
import tempfile
import unittest
from vendor_assurance.benchmark import compare, envelope, evaluate, write_comparison
from vendor_assurance.core import digest
from vendor_assurance.integration import execute

ROOT=Path(__file__).resolve().parents[1]


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.manifest=json.loads((ROOT/'examples/acceptance-manifest.json').read_text())
        self.report=json.loads((ROOT/'evidence/recovery-local.json').read_text())
        self.candidate=envelope(self.report,self.manifest,'case1','candidate','run1')
        self.baseline=envelope(self.report,self.manifest,'case1','baseline','run2')

    def test_candidate_only_does_not_invent_savings(self):
        result=compare(self.manifest,[self.candidate])
        self.assertEqual(result['paired_cases'],0)
        self.assertIsNone(result['active_effort_reduction_fraction'])
        self.assertEqual(result['unmatched_cases'],['case1'])

    def test_paired_elapsed_time_not_labor(self):
        result=compare(self.manifest,[self.candidate,self.baseline])
        self.assertEqual(result['paired_cases'],1)
        self.assertEqual(result['effort_measured_pairs'],0)

    def test_effort_arithmetic(self):
        self.baseline['active_minutes']=10
        self.candidate['active_minutes']=7
        result=compare(self.manifest,[self.candidate,self.baseline])
        self.assertAlmostEqual(result['active_effort_reduction_fraction'],0.3)
        self.assertEqual(result['independent_accuracy'],'not_measured')

    def test_zero_baseline_undefined(self):
        self.baseline['active_minutes']=0
        self.candidate['active_minutes']=0
        self.assertIsNone(compare(self.manifest,[self.candidate,self.baseline])['active_effort_reduction_fraction'])

    def test_duplicate_run_rejected(self):
        self.baseline['run_id']='run1'
        with self.assertRaises(ValueError): compare(self.manifest,[self.baseline,self.candidate])

    def test_duplicate_case_workflow_rejected(self):
        other=copy.deepcopy(self.candidate)
        other['run_id']='another'
        with self.assertRaises(ValueError): compare(self.manifest,[self.candidate,other])

    def test_tenant_denied(self):
        self.candidate['tenant']='other'
        with self.assertRaises(PermissionError): evaluate(self.candidate,self.manifest)

    def test_timing_mismatch(self):
        self.candidate['timing_boundary']='restore_only'
        with self.assertRaises(ValueError): evaluate(self.candidate,self.manifest)

    def test_workload_mismatch(self):
        self.candidate['workload_sha256']='1'*64
        with self.assertRaises(ValueError): evaluate(self.candidate,self.manifest)

    def test_manifest_change(self):
        self.manifest['rto_seconds']=1
        with self.assertRaises(ValueError): evaluate(self.candidate,self.manifest)

    def test_report_modified(self):
        self.candidate['report']['recovery_seconds']=0
        with self.assertRaises(ValueError): evaluate(self.candidate,self.manifest)

    def test_missing_probe_blocks_eligibility(self):
        self.report['application_checks'].pop('committed_write')
        run=envelope(self.report,self.manifest,'case1','candidate','new')
        self.assertFalse(evaluate(run,self.manifest)['eligible'])

    def test_failed_cleanup_blocks_eligibility(self):
        self.report['cleanup']['verified']=False
        run=envelope(self.report,self.manifest,'case1','candidate','new')
        self.assertFalse(evaluate(run,self.manifest)['eligible'])

    def test_rpo_objective_enforced(self):
        self.report['measured_data_age_seconds']=301
        run=envelope(self.report,self.manifest,'case1','candidate','new')
        self.assertIn('objective_exceeded:measured_data_age_seconds',evaluate(run,self.manifest)['reasons'])

    def test_ineligible_pair_not_used_for_savings(self):
        self.report['status']='failed'
        failed=envelope(self.report,self.manifest,'case1','candidate','failed',1)
        self.baseline['active_minutes']=10
        result=compare(self.manifest,[failed,self.baseline])
        self.assertEqual(result['quality_disagreements'],['case1'])
        self.assertIsNone(result['active_effort_reduction_fraction'])

    def test_different_scenarios_not_paired(self):
        self.report['scenario']='stale_data'
        different=envelope(self.report,self.manifest,'case1','candidate','different')
        with self.assertRaises(ValueError): compare(self.manifest,[different,self.baseline])

    def test_invalid_effort(self):
        for value in (-1,float('inf'),True):
            with self.subTest(value=value):
                self.candidate['active_minutes']=value
                with self.assertRaises(ValueError): evaluate(self.candidate,self.manifest)

    def test_unknown_manifest_version(self):
        self.manifest['schema_version']=2
        with self.assertRaises(ValueError): compare(self.manifest,[])

    def test_export_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary)/'report'
            write_comparison(output,compare(self.manifest,[self.candidate]))
            self.assertTrue((output/'benchmark.html').exists())
            with self.assertRaises(FileExistsError): write_comparison(output,{})

    def test_real_customer_report_not_silently_supported(self):
        self.report['synthetic']=False
        with self.assertRaises(ValueError): envelope(self.report,self.manifest,'case1','candidate','new')

    def test_adapter_rejects_unimplemented_workload(self):
        self.manifest['workload_sha256']='1'*64
        with self.assertRaises(ValueError): execute(self.manifest,'unused-output')
