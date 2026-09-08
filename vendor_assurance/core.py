"""Deterministic evidence review. Callers are trusted local operators, not authenticated users."""
from datetime import date
from hashlib import sha256
import json


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def required_text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('nonempty text required')
    return value


def validate(bundle):
    for key in ('tenant', 'vendor', 'service'):
        required_text(bundle[key])
    date.fromisoformat(bundle['renewal_date'])
    docs = {}
    for doc in bundle['documents']:
        identifier = required_text(doc['id'])
        if identifier in docs:
            raise ValueError('duplicate document id')
        required_text(doc['family'])
        required_text(doc['text'])
        if doc['kind'] not in ('contract', 'questionnaire', 'evidence'):
            raise ValueError('unsupported document kind')
        if type(doc['version']) is not int or doc['version'] < 1:
            raise ValueError('invalid version')
        date.fromisoformat(doc['valid_until'])
        if any(d['family'] == doc['family'] and d['version'] == doc['version'] for d in docs.values()):
            raise ValueError('duplicate family version')
        docs[identifier] = doc
    ids = set()
    for claim in bundle['claims']:
        if claim['id'] in ids:
            raise ValueError('duplicate claim id')
        ids.add(required_text(claim['id']))
        required_text(claim['key'])
        required_text(claim['value'])
        doc = docs[claim['document']]
        start, end = claim['start'], claim['end']
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(doc['text']):
            raise ValueError('invalid source span')
        if doc['text'][start:end] != claim['quote'] or claim['value'] not in claim['quote']:
            raise ValueError('unsupported source quotation')
    for obligation in bundle['obligations']:
        required_text(obligation['key'])
        required_text(obligation['owner'])
    for action in bundle['actions']:
        required_text(action['id'])
        required_text(action['owner'])
        date.fromisoformat(action['due'])
        if action['status'] not in ('open', 'closed'):
            raise ValueError('invalid action status')
    return docs


def review(bundle, tenant, as_of):
    if tenant != bundle['tenant']:
        raise PermissionError('tenant scope denied')
    today = date.fromisoformat(as_of)
    docs = validate(bundle)
    latest = {d['family']: max(x['version'] for x in docs.values() if x['family'] == d['family']) for d in docs.values()}
    findings = []
    def add(kind, key, citations, detail):
        findings.append(dict(id=f'F{len(findings)+1}', kind=kind, key=key, citations=citations, detail=detail))
    def cite(claim):
        doc = docs[claim['document']]
        return dict(document=doc['id'], version=doc['version'], sha256=sha256(doc['text'].encode()).hexdigest(), start=claim['start'], end=claim['end'], quote=claim['quote'])
    current = []
    for claim in bundle['claims']:
        doc = docs[claim['document']]
        if doc['version'] != latest[doc['family']]:
            add('superseded', claim['key'], [cite(claim)], 'A newer document version requires reassessment.')
        elif date.fromisoformat(doc['valid_until']) < today:
            add('expired', claim['key'], [cite(claim)], 'Source validity has expired.')
        else:
            current.append(claim)
    for key in sorted({c['key'] for c in current}):
        claims = [c for c in current if c['key'] == key]
        if len({c['value'] for c in claims}) > 1:
            add('conflict', key, [cite(c) for c in claims], 'Different structured values require human reconciliation; no legal precedence inferred.')
    for obligation in bundle['obligations']:
        if not any(c['key'] == obligation['key'] and docs[c['document']]['kind'] == 'evidence' for c in current):
            add('missing_evidence', obligation['key'], [], f"No current evidence claim supplied. Owner: {obligation['owner']}")
    for action in bundle['actions']:
        if action['status'] == 'open' and date.fromisoformat(action['due']) < today:
            add('overdue', action['id'], [], f"Action overdue since {action['due']}. Owner: {action['owner']}")
    return dict(schema_version=1, tenant=tenant, vendor=bundle['vendor'], service=bundle['service'], as_of=as_of,
                renewal_date=bundle['renewal_date'], days_to_renewal=(date.fromisoformat(bundle['renewal_date'])-today).days,
                bundle_sha256=digest(bundle), findings=findings, status='human_review_required',
                limitations=['Structured claims are operator supplied; quotation matching does not prove semantic truth.',
                             'No assessment of unseen documents, legal compliance, or real supplier security.'])


def decide(bundle, report, tenant, actor, role, outcome, rationale, acknowledgements, today):
    """Record an advisory decision; never execute a renewal or risk acceptance externally."""
    if tenant != bundle['tenant'] or tenant != report['tenant']:
        raise PermissionError('tenant scope denied')
    if role != 'human_reviewer':
        raise PermissionError('human reviewer required')
    required_text(actor)
    required_text(rationale)
    if outcome not in ('defer', 'recommend_renewal', 'recommend_nonrenewal'):
        raise ValueError('invalid advisory outcome')
    if report != review(bundle, tenant, today):
        raise ValueError('stale or modified report; rerun review')
    if set(acknowledgements) != {f['id'] for f in report['findings']}:
        raise ValueError('every finding requires explicit acknowledgement')
    return dict(tenant=tenant, actor=actor, role=role, outcome=outcome, rationale=rationale,
                acknowledged_findings=sorted(acknowledgements), as_of=today, report_sha256=digest(report),
                bundle_sha256=digest(bundle), external_action=False)
