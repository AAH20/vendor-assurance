"""Read-only AWS Backup DescribeRestoreJob adapter and offline evidence review."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import time
from .core import digest, required_text


def timestamp(value):
    if isinstance(value, datetime):
        if value.tzinfo is None: raise ValueError('timezone required')
        return value.timestamp()
    if isinstance(value,str):
        return timestamp(datetime.fromisoformat(value.replace('Z','+00:00')))
    if type(value) not in (int,float) or not math.isfinite(value) or value<0:
        raise ValueError('valid timestamp required')
    return value


def json_ready(value):
    if isinstance(value,datetime):
        timestamp(value)
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value,dict): return {k:json_ready(v) for k,v in value.items()}
    if isinstance(value,list): return [json_ready(v) for v in value]
    return value


def grant_check(grant, now):
    if grant['schema_version']!=1 or grant['purpose']!='read_restore_evidence': raise ValueError('unsupported grant')
    if grant['revoked'] is not False or not timestamp(grant['not_before'])<=now<timestamp(grant['expires_at']):
        raise PermissionError('grant revoked or outside validity window')
    if not re.fullmatch(r'[0-9]{12}',grant['account']): raise ValueError('invalid account')
    if not re.fullmatch(r'[a-z]{2}-[a-z]+-\d',grant['region']): raise ValueError('commercial AWS region required')
    for field in ('tenant','restore_job_id','caller_arn','source_resource_arn','recovery_point_arn','application_test_sha256','authorization_reference'):
        required_text(grant[field])
    if not re.fullmatch('[0-9a-f]{64}',grant['application_test_sha256']): raise ValueError('test digest required')
    for field in ('source_resource_arn','recovery_point_arn'):
        parts=grant[field].split(':',5)
        if len(parts)!=6 or parts[0:2]!=['arn','aws'] or parts[3:5]!=[grant['region'],grant['account']]:
            raise ValueError('resource ARN outside grant account/region')
    if not grant['source_resource_arn'].startswith(f"arn:aws:rds:{grant['region']}:{grant['account']}:db:"):
        raise ValueError('only RDS instance restore evidence supported')


def collect(grant_loader, sts, backup, clock=time.time):
    """Exactly two read operations, with local grant rechecks. Does not assume roles."""
    grant=grant_loader()
    grant_check(grant,clock())
    if grant.get('mode')!='authorized': raise PermissionError('live collection requires authorized-mode grant')
    identity=sts.get_caller_identity()
    if identity['Account']!=grant['account'] or identity['Arn']!=grant['caller_arn']:
        raise PermissionError('AWS caller outside exact grant identity')
    if grant_loader()!=grant: raise PermissionError('grant changed during collection')
    grant_check(grant,clock())
    job=backup.describe_restore_job(RestoreJobId=grant['restore_job_id'])
    if grant_loader()!=grant: raise PermissionError('grant changed during collection')
    now=clock()
    grant_check(grant,now)
    check_job_scope(grant,job)
    return dict(schema_version=1,adapter='aws-backup-describe-restore-job/1',tenant=grant['tenant'],
                collected_at=now,grant_sha256=digest(grant),transport='boto3',
                caller=json_ready(identity),response=json_ready(job),response_sha256=digest(json_ready(job)))


def check_job_scope(grant,job):
    expected={'AccountId':grant['account'],'RestoreJobId':grant['restore_job_id'],
              'SourceResourceArn':grant['source_resource_arn'],'RecoveryPointArn':grant['recovery_point_arn']}
    if any(job.get(k)!=v for k,v in expected.items()): raise PermissionError('restore response outside grant scope')
    if job.get('ResourceType')!='RDS' or job.get('IsParent') is True or job.get('ParentJobId'):
        raise ValueError('only individual RDS restore jobs supported')
    target=job.get('CreatedResourceArn')
    if target is not None and not target.startswith(f"arn:aws:rds:{grant['region']}:{grant['account']}:db:"):
        raise PermissionError('restored target outside grant scope')


def review(grant, capture, application, tenant, as_of, rto=3600, rpo=300, max_age=86400):
    now=timestamp(as_of)
    if any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 for x in (rto,rpo,max_age)):
        raise ValueError('positive finite objectives required')
    if tenant!=grant['tenant'] or tenant!=capture['tenant']: raise PermissionError('tenant mismatch')
    grant_check(grant,now)
    if capture['grant_sha256']!=digest(grant): raise ValueError('grant digest mismatch')
    job=capture['response']
    if capture['response_sha256']!=digest(job): raise ValueError('response digest mismatch')
    check_job_scope(grant,job)
    reasons=[]
    def missing(reason):
        if reason not in reasons: reasons.append(reason)
    collected=timestamp(capture['collected_at'])
    if collected>now or now-collected>max_age: missing('stale_or_future_capture')
    if job.get('Status')!='COMPLETED': missing('restore_not_completed')
    if job.get('ValidationStatus')!='SUCCESSFUL': missing('aws_validation_not_successful')
    if job.get('DeletionStatus')!='SUCCESSFUL': missing('aws_cleanup_not_successful')
    started=timestamp(job['CreationDate']) if 'CreationDate' in job else None
    finished=timestamp(job['CompletionDate']) if 'CompletionDate' in job else None
    if started is None or finished is None or not started<=finished<=collected:
        missing('invalid_or_missing_restore_timeline')
    duration=data_age=None
    if application is None:
        missing('application_evidence_missing')
    else:
        for key,expected in (('tenant',tenant),('restore_job_id',grant['restore_job_id']),('created_resource_arn',job.get('CreatedResourceArn')),('application_test_sha256',grant['application_test_sha256'])):
            if not expected or application.get(key)!=expected: missing('application_scope_mismatch:'+key)
        if application.get('engine')!='postgresql': missing('postgresql_application_not_established')
        for key in ('restored_records','committed_write'):
            if application.get('checks',{}).get(key) is not True: missing('application_check_missing_or_failed:'+key)
        if application.get('extra_resources_removed') is not True: missing('application_cleanup_unverified')
        for key in ('evidence_reference','reviewer'):
            if not isinstance(application.get(key),str) or not application[key].strip(): missing('application_provenance_missing:'+key)
        required_times=('validation_started_at','validation_completed_at','latest_recovered_transaction_at')
        if any(k not in application for k in required_times):
            missing('application_timestamps_missing')
        elif started is not None and finished is not None:
            va,ve,latest=(timestamp(application[k]) for k in required_times)
            if not finished<=va<=ve<=collected or latest>started: missing('invalid_application_timeline')
            else:
                duration=ve-started
                data_age=started-latest
                if duration>rto: missing('recovery_time_exceeded')
                if data_age>rpo: missing('recovered_data_age_exceeded')
    return dict(adapter='aws-backup-review/1',tenant=tenant,restore_job_id=grant['restore_job_id'],
                status='eligible_for_human_review' if not reasons else 'unverified',reasons=reasons,
                recovery_seconds=duration,recovered_data_age_seconds=data_age,
                timing_boundary='aws_restore_job_creation_to_application_validation_complete',
                rto_seconds=rto,rpo_seconds=rpo,grant_sha256=digest(grant),capture_sha256=digest(capture),
                application_sha256=digest(application) if application else None,
                human_acceptance='pending',external_action=False,
                limitations=['Export hashes are not signatures or AWS attestation.',
                             'Application checks and cleanup receipt are externally supplied, not executed by this adapter.',
                             'RecoveryPointCreationDate is not used as proof of recovered transaction age.',
                             'Timing excludes outage detection and human mobilization; do not compare directly to the local runner timing boundary.'])


def write_private(path,value):
    import os
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as handle: json.dump(value,handle,indent=2); handle.write('\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['collect','review'])
    parser.add_argument('--grant',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--profile')
    parser.add_argument('--capture',type=Path)
    parser.add_argument('--application',type=Path)
    parser.add_argument('--tenant')
    parser.add_argument('--as-of')
    args=parser.parse_args()
    load=lambda:json.loads(args.grant.read_text())
    grant=load()
    if args.output.exists(): parser.error('output must be a new file')
    if args.action=='collect':
        if not args.profile: parser.error('explicit AWS profile required')
        grant_check(grant,time.time())
        if grant.get('mode')!='authorized': parser.error('authorized-mode grant required; examples are synthetic')
        import boto3
        from botocore.config import Config
        config=Config(region_name=grant['region'],connect_timeout=5,read_timeout=10,retries={'max_attempts':1},ignore_configured_endpoint_urls=True)
        session=boto3.Session(profile_name=args.profile,region_name=grant['region'])
        result=collect(load,session.client('sts',config=config),session.client('backup',config=config))
    else:
        if not all((args.capture,args.tenant,args.as_of)): parser.error('--capture, --tenant and --as-of required')
        capture=json.loads(args.capture.read_text())
        app=json.loads(args.application.read_text()) if args.application else None
        result=dict(grant=grant,capture=capture,application=app,review=review(grant,capture,app,args.tenant,args.as_of))
    write_private(args.output,result)
    print(json.dumps({'output':str(args.output),'action':args.action}))


if __name__=='__main__': main()
