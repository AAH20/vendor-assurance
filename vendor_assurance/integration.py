"""Built-in local PostgreSQL adapter. No speculative cloud-vendor integration."""
import argparse
import hashlib
import json
from pathlib import Path
from .benchmark import envelope, validate_manifest, compare, write_comparison, WORKLOAD
from .recovery import run


def execute(manifest, output):
    validate_manifest(manifest)
    if manifest['application'] != 'synthetic-orders-postgresql':
        raise ValueError('adapter supports only the synthetic orders application')
    if manifest['workload_sha256'] != hashlib.sha256(WORKLOAD.encode()).hexdigest():
        raise ValueError('manifest does not describe the executable workload')
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    raw=run(output/'raw',rto_seconds=manifest['rto_seconds'],rpo_seconds=manifest['rpo_seconds'])
    candidate=envelope(raw,manifest,'healthy-orders','candidate','candidate-local-1')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'runs.json').write_text(json.dumps([candidate],indent=2)+'\n')
    write_comparison(output/'comparison',compare(manifest,[candidate]))
    return candidate


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    result=execute(json.loads(args.manifest.read_text()),args.output)
    print(json.dumps({'run_id':result['run_id'],'status':result['report']['status'],'baseline':'not supplied'}))
    raise SystemExit(0 if result['report']['status']=='exercise_passed_pending_human_review' else 1)
