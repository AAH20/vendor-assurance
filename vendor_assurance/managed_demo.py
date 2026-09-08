"""Run the authenticated HTTP control workflow with a real synthetic restore.

Demo role credentials are held by this one process. Review is simulated, not an actual human approval.
"""
import argparse
import json
from pathlib import Path
import tempfile
import threading
from .managed import provision, make_server, request
from .recovery import run


def demo(output):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='a2z-managed-') as temporary:
        root=Path(temporary)/'state'
        provision(root)
        tokens={r:(root/(r+'.token')).read_text() for r in ('requester','approver','runner','reviewer')}
        with make_server(root,0) as server:
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            def api(role,action,body): return request(server.server_port,tokens[role],action,body)
            try:
                job=api('requester','create',{'adapter':'local-postgres-synthetic-v1'})
                body={'id':job['id']}
                denied=[]
                for role,action in [('requester','approve'),('runner','claim')]:
                    try: api(role,action,body)
                    except RuntimeError: denied.append(role+':'+action)
                    else: raise AssertionError('unauthorized action succeeded')
                api('approver','approve',body)
                claimed=api('runner','claim',body)
                result=run(output/'runner',control_check=lambda:api('runner','check',body))
                submitted=api('runner','submit',{**body,'result':result,'execution_scope':{k:claimed[k] for k in ('id','tenant','execution_id','package_sha256')}})
                try: api('runner','accept',{**body,'result_sha256':submitted['result_sha256'],'rationale':'attempt'})
                except RuntimeError: denied.append('runner:accept')
                else: raise AssertionError('runner accepted its own evidence')
                reviewed=api('reviewer','accept',{**body,'result_sha256':submitted['result_sha256'],'rationale':'SIMULATED reviewer: real human acceptance is still required for a pilot.'})
                artifact=dict(synthetic=True,review_simulated=True,denied_actions=denied,job=reviewed)
                (output/'managed-demo.json').write_text(json.dumps(artifact,indent=2)+'\n')
            finally:
                server.shutdown()
                thread.join(timeout=5)
    return artifact


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=demo(args.output)
    print(json.dumps({'status':result['job']['status'],'review_simulated':True,'denied_actions':result['denied_actions']}))
