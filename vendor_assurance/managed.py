"""Loopback pilot control plane. Bearer credentials identify preprovisioned principals.

No cloud adapters or production hosting. Administrator controls the local state directory.
"""
import argparse
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import math
import os
from pathlib import Path
import secrets
import sqlite3
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import uuid
from .core import digest
from .recovery import run


@contextmanager
def connect(root):
    db=sqlite3.connect(Path(root)/'control.db',timeout=10)
    db.row_factory=sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()


def provision(root):
    root=Path(root)
    root.mkdir(mode=0o700,parents=True,exist_ok=False)
    with connect(root) as db:
        db.executescript('CREATE TABLE principals(token_hash TEXT PRIMARY KEY, actor TEXT, tenant TEXT, role TEXT, revoked INTEGER DEFAULT 0); CREATE TABLE jobs(id TEXT PRIMARY KEY, tenant TEXT, data TEXT); CREATE TABLE events(id INTEGER PRIMARY KEY, at REAL, actor TEXT, tenant TEXT, action TEXT, job TEXT);')
        for role in ('requester','approver','runner','reviewer'):
            token=secrets.token_urlsafe(32)
            db.execute('INSERT INTO principals(token_hash,actor,tenant,role) VALUES(?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),role+'-demo','synthetic-bank',role))
            file=root/(role+'.token')
            fd=os.open(file,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as handle: handle.write(token)
    os.chmod(root/'control.db',0o600)


def disable_credential(root, token):
    """Local state owner operation; never exposed through the HTTP API."""
    with connect(root) as db:
        result=db.execute('UPDATE principals SET revoked=1 WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),))
        if not result.rowcount: raise ValueError('unknown credential')


def dispatch(root, token, action, body, now=None):
    now=time.time() if now is None else now
    with connect(root) as db:
        db.execute('BEGIN IMMEDIATE')
        principal=db.execute('SELECT * FROM principals WHERE token_hash=? AND revoked=0',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
        if principal is None: raise PermissionError('invalid or revoked credential')
        permissions={'create':'requester','approve':'approver','revoke':'approver','claim':'runner','check':'runner','submit':'runner','accept':'reviewer','reject':'reviewer'}
        if action not in (*permissions,'read'):
            raise ValueError('unknown action')
        if action in permissions and principal['role']!=permissions[action]:
            raise PermissionError('role denied')
        if action=='create':
            if body != {'adapter':'local-postgres-synthetic-v1'}:
                raise ValueError('only the fixed synthetic adapter is permitted')
            identifier=str(uuid.uuid4())
            job=dict(id=identifier,tenant=principal['tenant'],status='pending_approval',adapter=body['adapter'],created_by=principal['actor'],created_at=now,
                     expires_at=now+900,max_runtime_seconds=120,max_concurrent_clusters=2,cloud_spend_permitted=False,rto_seconds=60,rpo_seconds=300)
            db.execute('INSERT INTO jobs VALUES(?,?,?)',(identifier,principal['tenant'],json.dumps(job)))
        else:
            identifier=body.get('id')
            row=db.execute('SELECT data FROM jobs WHERE id=? AND tenant=?',(identifier,principal['tenant'])).fetchone()
            if row is None: raise PermissionError('job not accessible')
            job=json.loads(row['data'])
            if action=='read':
                if job['status'] in ('pending_approval','approved','running') and (now>=job['expires_at'] or (job['status']=='running' and now-job['started_at']>=job['max_runtime_seconds'])):
                    job['effective_status']='authorization_or_runtime_expired'
                return job
            if action=='revoke':
                if job['status'] in ('accepted','rejected'): raise ValueError('final review is immutable')
                job.update(status='revoked',revoked_by=principal['actor'],revoked_at=now)
            else:
                if job['status']=='revoked': raise PermissionError('job revoked')
                if action in ('approve','claim','check','submit') and now>=job['expires_at']:
                    raise PermissionError('authorization expired')
                if action=='approve':
                    if job['status']!='pending_approval': raise ValueError('not pending approval')
                    if principal['actor']==job['created_by']: raise PermissionError('separate approver required')
                    job.update(status='approved',approved_by=principal['actor'],approved_at=now)
                elif action=='claim':
                    if job['status']!='approved': raise ValueError('job already claimed or not approved')
                    job.update(status='running',runner=principal['actor'],started_at=now)
                elif action in ('check','submit'):
                    if job['status']!='running' or job['runner']!=principal['actor']: raise PermissionError('runner does not own active job')
                    if action=='check':
                        if now-job['started_at']>=job['max_runtime_seconds']: raise PermissionError('runtime budget exhausted')
                        return job
                    result=body['result']
                    if not isinstance(result,dict) or result.get('synthetic') is not True:
                        raise ValueError('synthetic report required')
                    good=(result.get('status')=='exercise_passed_pending_human_review' and result.get('cleanup',{}).get('verified') is True and result.get('application_checks')=={'restored_records':True,'committed_write':True})
                    for metric,limit in (('recovery_seconds',job['rto_seconds']),('measured_data_age_seconds',job['rpo_seconds'])):
                        value=result.get(metric)
                        if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=limit: good=False
                    if result.get('scenario')!='healthy': good=False
                    if now-job['started_at']>=job['max_runtime_seconds']: good=False
                    job.update(status='awaiting_review' if good else 'failed',result=result,result_sha256=digest(result),finished_at=now)
                elif action in ('accept','reject'):
                    if job['status']!='awaiting_review': raise ValueError('successful evidence required for review')
                    if principal['actor'] in (job['runner'],job['approved_by'],job['created_by']): raise PermissionError('independent reviewer required')
                    if body.get('result_sha256')!=job['result_sha256']: raise ValueError('review must bind exact evidence')
                    rationale=body.get('rationale')
                    if not isinstance(rationale,str) or not rationale.strip(): raise ValueError('review rationale required')
                    job.update(status='accepted' if action=='accept' else 'rejected',reviewed_by=principal['actor'],reviewed_at=now,rationale=rationale)
            db.execute('UPDATE jobs SET data=? WHERE id=?',(json.dumps(job),identifier))
        db.execute('INSERT INTO events(at,actor,tenant,action,job) VALUES(?,?,?,?,?)',(now,principal['actor'],principal['tenant'],action,identifier))
        return job


def make_server(root, port):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)
        def log_message(self,*args): pass
        def do_POST(self):
            status=200
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=65536: raise ValueError('body size must be 1–65536 bytes')
                if self.headers.get('Origin'): raise PermissionError('browser requests disabled')
                auth=self.headers.get('Authorization','')
                if not auth.startswith('Bearer '): raise PermissionError('bearer credential required')
                result=dispatch(root,auth[7:],self.path.removeprefix('/'),json.loads(self.rfile.read(length)))
            except PermissionError as exc:
                status,result=403,{'error':str(exc)}
            except (ValueError,KeyError,TypeError) as exc:
                status,result=400,{'error':str(exc)}
            payload=json.dumps(result).encode()
            self.send_response(status)
            self.send_header('Content-Type','application/json')
            self.send_header('Cache-Control','no-store')
            self.send_header('Content-Length',str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
    return HTTPServer(('127.0.0.1',port),Handler)


def serve(root, port):
    with make_server(root,port) as server:
        server.serve_forever()


def request(port, token, action, body):
    req=Request(f'http://127.0.0.1:{port}/{action}',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    try:
        with urlopen(req,timeout=10) as response: return json.load(response)
    except HTTPError as exc:
        with exc:
            raise RuntimeError(f'control plane denied request ({exc.code})') from None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['init','serve','disable-credential','create','approve','revoke','read','accept','reject','execute'])
    parser.add_argument('--state',type=Path)
    parser.add_argument('--port',type=int,default=8766)
    parser.add_argument('--token-file',type=Path)
    parser.add_argument('--id')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--rationale')
    parser.add_argument('--result-sha256')
    args=parser.parse_args()
    if args.action in ('init','serve','disable-credential') and args.state is None: parser.error('--state required')
    if args.action not in ('init','serve') and args.token_file is None: parser.error('--token-file required')
    if args.action=='init': provision(args.state); return
    if args.action=='serve': serve(args.state,args.port); return
    token=args.token_file.read_text().strip()
    if args.action=='disable-credential': disable_credential(args.state,token); return
    if args.action=='execute':
        if not args.output or args.output.exists(): raise ValueError('new output directory required')
        job=request(args.port,token,'claim',{'id':args.id})
        def guard(): request(args.port,token,'check',{'id':args.id})
        result=run(args.output,control_check=guard,rto_seconds=job['rto_seconds'],rpo_seconds=job['rpo_seconds'])
        result=request(args.port,token,'submit',{'id':args.id,'result':result})
    else:
        body={'adapter':'local-postgres-synthetic-v1'} if args.action=='create' else {'id':args.id}
        if args.action in ('accept','reject'): body.update(rationale=args.rationale,result_sha256=args.result_sha256)
        result=request(args.port,token,args.action,body)
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
