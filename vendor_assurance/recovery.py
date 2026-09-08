"""Real synthetic PostgreSQL recovery drill. Never connects to an existing database."""
import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
from urllib.request import urlopen
from urllib.error import HTTPError

SCENARIOS = ('healthy', 'corrupt_backup', 'missing_dependency', 'stale_data', 'invalid_application', 'rto_exceeded')


def run(output, scenario='healthy', rto_seconds=60, rpo_seconds=300):
    if scenario not in SCENARIOS or not all(math.isfinite(x) and x > 0 for x in (rto_seconds,rpo_seconds)):
        raise ValueError('invalid scenario or recovery objectives')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    # Ignore ambient PG* settings; this drill must never target a configured service.
    env = {k:v for k,v in os.environ.items() if not k.startswith('PG')}
    bindir = Path(subprocess.check_output(['pg_config','--bindir'],env=env,text=True).strip())
    workspace = Path(tempfile.mkdtemp(prefix='a2zr-', dir='/tmp'))
    os.chmod(workspace, 0o700)
    started = []
    server = None
    server_thread = None
    events = []
    report = dict(schema_version=1, scenario=scenario, status='failed', synthetic=True,
                  rto_objective_seconds=rto_seconds, rpo_objective_seconds=rpo_seconds,
                  human_acceptance='pending', events=events,
                  scope='One local PostgreSQL application; not production or malware-free recovery assurance.')
    def command(tool, *args, timeout=30):
        result = subprocess.run([str(bindir/tool), *map(str,args)],env=env,text=True,capture_output=True,timeout=timeout)
        if result.returncode:
            raise RuntimeError(f'{tool} failed: {result.stderr[-1200:]}')
        return result.stdout.strip()
    def event(name, **fields):
        events.append(dict(event=name, at=datetime.now(timezone.utc).isoformat(), **fields))
    def cluster(name):
        data = workspace/name
        socket = workspace/(name+'s')
        socket.mkdir(mode=0o700)
        command('initdb','-D',data,'-U','drill','-A','trust','--no-locale')
        # No TCP listener; socket lives under a private mode-0700 directory.
        with (data/'postgresql.conf').open('a') as handle:
            handle.write(f"\nlisten_addresses = ''\nunix_socket_directories = '{socket}'\n")
        # Register before startup so failure cleanup can still stop a partial start.
        started.append(data)
        command('pg_ctl','-D',data,'-l',workspace/(name+'.log'),'-w','start')
        return socket
    def sql(socket, statement):
        return command('psql','-X','-h',socket,'-U','drill','-d','postgres','-v','ON_ERROR_STOP=1','-At','-c',statement)
    recovery_started = None
    try:
        report['postgres_version'] = command('postgres','--version')
        source = cluster('source')
        age = 3600 if scenario == 'stale_data' else 0
        sql(source, f"CREATE TABLE orders(id integer PRIMARY KEY, amount integer NOT NULL CHECK(amount>0), committed_at timestamptz NOT NULL); INSERT INTO orders SELECT n, n*10, clock_timestamp() - interval '{age} seconds' FROM generate_series(1,3) n;")
        expected = sql(source,"SELECT json_build_object('count',count(*),'total',sum(amount),'latest',extract(epoch from max(committed_at))) FROM orders")
        backup = workspace/'backup.dump'
        command('pg_dump','-h',source,'-U','drill','-d','postgres','-Fc','-f',backup)
        report['backup_sha256'] = hashlib.sha256(backup.read_bytes()).hexdigest()
        report['expected'] = json.loads(expected)
        event('backup_created', sha256=report['backup_sha256'])
        # Stop source: the application validation cannot accidentally use it.
        command('pg_ctl','-D',workspace/'source','-m','fast','-w','stop')
        recovery_started = time.monotonic()
        reference_epoch = time.time()
        event('recovery_started')
        if scenario == 'corrupt_backup':
            backup.write_bytes(b'corrupted synthetic backup')
        report['restored_artifact_sha256'] = hashlib.sha256(backup.read_bytes()).hexdigest()
        if report['restored_artifact_sha256'] != report['backup_sha256']:
            raise RuntimeError('backup integrity mismatch')
        target = cluster('target')
        command('pg_restore','-h',target,'-U','drill','-d','postgres','--exit-on-error',backup)
        event('restore_completed')
        if scenario == 'missing_dependency':
            command('pg_ctl','-D',workspace/'target','-m','fast','-w','stop')
        if scenario == 'invalid_application':
            sql(target,'ALTER TABLE orders RENAME TO unavailable_orders')

        class API(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path != '/orders':
                    self.send_error(404)
                    return
                try:
                    body = sql(target,"SELECT json_build_object('count',count(*),'total',sum(amount),'latest',extract(epoch from max(committed_at))) FROM orders")
                    self.send_response(200)
                    self.send_header('Content-Type','application/json')
                    self.end_headers()
                    self.wfile.write(body.encode())
                except Exception:
                    self.send_error(503, 'Database or application unavailable')

            def do_POST(self):
                if self.path != '/probe':
                    self.send_error(404)
                    return
                try:
                    # Fixed synthetic transaction; never executes caller-supplied SQL.
                    sql(target,"BEGIN; INSERT INTO orders VALUES(4,40,clock_timestamp()); COMMIT;")
                    self.send_response(201)
                    self.end_headers()
                except Exception:
                    self.send_error(503, 'Transaction failed')

        server = ThreadingHTTPServer(('127.0.0.1',0),API)
        server_thread = threading.Thread(target=server.serve_forever,daemon=True)
        server_thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        with urlopen(base+'/orders',timeout=10) as response:
            recovered = json.load(response)
        if recovered != report['expected']:
            raise RuntimeError('recovered data does not match source')
        report['measured_data_age_seconds'] = max(0,reference_epoch-recovered['latest'])
        with urlopen(base+'/probe',data=b'',timeout=10) as response:
            if response.status != 201:
                raise RuntimeError('application write probe failed')
        with urlopen(base+'/orders',timeout=10) as response:
            after = json.load(response)
        if after['count'] != 4 or after['total'] != 100:
            raise RuntimeError('committed application transaction missing')
        report['application_checks'] = dict(restored_records=True, committed_write=True)
        report['recovery_seconds'] = time.monotonic()-recovery_started
        event('application_validated')
        if report['measured_data_age_seconds'] > rpo_seconds:
            raise RuntimeError('data age exceeds recovery-point objective')
        # This scenario exercises a deliberately tight objective without sleeping.
        effective_rto = 0.000001 if scenario == 'rto_exceeded' else rto_seconds
        report['effective_rto_seconds'] = effective_rto
        if report['recovery_seconds'] > effective_rto:
            raise RuntimeError('recovery time exceeds objective')
        report['status'] = 'exercise_passed_pending_human_review'
    except Exception as exc:
        report['failure'] = str(exc).replace(str(workspace),'[disposable-workspace]')
        if isinstance(exc, HTTPError):
            exc.close()
        event('exercise_failed', reason=report['failure'])
    finally:
        if recovery_started and 'recovery_seconds' not in report:
            report['elapsed_to_failure_seconds'] = time.monotonic()-recovery_started
        cleanup_errors = []
        if server:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=5)
        for data in reversed(started):
            try:
                if (data/'postmaster.pid').exists():
                    command('pg_ctl','-D',data,'-m','immediate','-w','stop')
                if (data/'postmaster.pid').exists():
                    raise RuntimeError('database still running')
            except Exception as exc:
                cleanup_errors.append(str(exc).replace(str(workspace),'[disposable-workspace]'))
        # Preserve logs as evidence before deleting disposable databases/backups.
        for log in workspace.glob('*.log'):
            (output/log.name).write_text(log.read_text().replace(str(workspace),'[disposable-workspace]'))
        if not cleanup_errors:
            try:
                shutil.rmtree(workspace)
            except OSError as exc:
                cleanup_errors.append(str(exc).replace(str(workspace),'[disposable-workspace]'))
        report['cleanup'] = dict(verified=not workspace.exists() and not cleanup_errors, errors=cleanup_errors)
        if not report['cleanup']['verified']:
            report['status']='failed'
            report['cleanup']['remaining_workspace']=str(workspace)
        event('cleanup_checked', verified=report['cleanup']['verified'])
        (output/'recovery.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--scenario',choices=SCENARIOS,default='healthy')
    parser.add_argument('--rto-seconds',type=float,default=60)
    parser.add_argument('--rpo-seconds',type=float,default=300)
    args=parser.parse_args()
    result=run(args.output,args.scenario,args.rto_seconds,args.rpo_seconds)
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['status']=='exercise_passed_pending_human_review' else 1)


if __name__=='__main__': main()
