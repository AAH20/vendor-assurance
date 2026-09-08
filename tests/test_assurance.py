import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from vendor_assurance.core import review, decide

ROOT = Path(__file__).resolve().parents[1]


class AssuranceTests(unittest.TestCase):
    def setUp(self):
        self.bundle = json.loads((ROOT/'examples/synthetic.json').read_text())
        self.tenant = 'synthetic-bank'
        self.today = '2026-09-08'

    def run_review(self):
        return review(self.bundle, self.tenant, self.today)

    def decision(self, report=None, **changes):
        fields = dict(actor='Reviewer', role='human_reviewer', outcome='defer', rationale='Needs evidence', acknowledgements=['F1','F2','F3','F4','F5'])
        fields.update(changes)
        return decide(self.bundle, report or self.run_review(), self.tenant, today=self.today, **fields)

    def test_expected_findings(self):
        self.assertCountEqual([f['kind'] for f in self.run_review()['findings']], ['expired','superseded','conflict','missing_evidence','overdue'])

    def test_conflict_preserves_both_sources(self):
        finding = next(f for f in self.run_review()['findings'] if f['kind']=='conflict')
        self.assertEqual({c['quote'] for c in finding['citations']}, {'Recovery objective: 4 hours.', 'Recovery objective: 1 hour.'})

    def test_unrelated_tenant_denied(self):
        with self.assertRaises(PermissionError): review(self.bundle, 'other', self.today)

    def test_fabricated_quote_denied(self):
        self.bundle['claims'][0]['quote']='Everything compliant'
        with self.assertRaises(ValueError): self.run_review()

    def test_out_of_range_span_denied(self):
        for start,end in [(-1,5),(0,999),(3,2),(False,5)]:
            with self.subTest(start=start,end=end):
                self.bundle['claims'][0].update(start=start,end=end)
                with self.assertRaises(ValueError): self.run_review()

    def test_duplicate_document_denied(self):
        self.bundle['documents'].append(copy.deepcopy(self.bundle['documents'][0]))
        with self.assertRaises(ValueError): self.run_review()

    def test_duplicate_version_denied(self):
        self.bundle['documents'][4]['version']=1
        with self.assertRaises(ValueError): self.run_review()

    def test_agent_cannot_decide(self):
        with self.assertRaises(PermissionError): self.decision(role='agent')

    def test_missing_acknowledgement_denied(self):
        with self.assertRaises(ValueError): self.decision(acknowledgements=['F1'])

    def test_extra_acknowledgement_denied(self):
        with self.assertRaises(ValueError): self.decision(acknowledgements=['F1','F2','F3','F4','F5','F6'])

    def test_human_decision_is_advisory(self):
        result=self.decision()
        self.assertEqual(result['outcome'],'defer')
        self.assertFalse(result['external_action'])

    def test_changed_bundle_invalidates_decision(self):
        report=self.run_review()
        self.bundle['renewal_date']='2026-11-01'
        with self.assertRaises(ValueError): self.decision(report)

    def test_modified_report_denied(self):
        report=self.run_review()
        report['findings']=[]
        with self.assertRaises(ValueError): self.decision(report,acknowledgements=[])

    def test_stale_date_denied(self):
        report=self.run_review()
        self.today='2026-09-09'
        with self.assertRaises(ValueError): self.decision(report)

    def test_invalid_outcome_denied(self):
        with self.assertRaises(ValueError): self.decision(outcome='execute_contract')

    def test_empty_rationale_denied(self):
        with self.assertRaises(ValueError): self.decision(rationale=' ')

    def test_expiry_boundary(self):
        self.bundle['documents'][2]['valid_until']=self.today
        self.assertNotIn('expired',[f['kind'] for f in self.run_review()['findings']])
        self.assertNotIn('missing_evidence',[f['kind'] for f in self.run_review()['findings']])

    def test_closed_action_not_overdue(self):
        self.bundle['actions'][0]['status']='closed'
        self.assertNotIn('overdue',[f['kind'] for f in self.run_review()['findings']])

    def test_no_false_conflict_between_superseded_versions(self):
        self.assertFalse(any(f['kind']=='conflict' and f['key']=='audit' for f in self.run_review()['findings']))

    def test_export_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'review'
            command=[sys.executable,'-m','vendor_assurance',str(ROOT/'examples/synthetic.json'),'--tenant',self.tenant,'--as-of',self.today,'--decision',str(ROOT/'examples/human-decision.json'),'--output',str(output)]
            subprocess.run(command,cwd=ROOT,check=True,capture_output=True)
            package=json.loads((output/'review.json').read_text())
            self.assertEqual(package['decision']['outcome'],'defer')
            self.assertIn('Recovery objective: 4 hours.',(output/'review.html').read_text())
            self.assertNotEqual(subprocess.run(command,cwd=ROOT,capture_output=True).returncode,0)


if __name__ == '__main__': unittest.main()
