import importlib.util
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

spec=importlib.util.spec_from_file_location('r4',Path(__file__).with_name('r4-runner.py'))
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
run_id='c-dc4-permissions01'
path=r.MEASURE/(run_id+'.json')
assert not path.exists(),'Preserve terminal permissions probe; no blind retry'
r.verify_input();r.ownership();r.preserve_auth()
record=json.loads(r.RECORD.read_bytes())
record['resume'].update(active_probe_run_id=run_id,next_action='Readonly formal API/auth/Origin/invalid Socket token boundary; no lifecycle action')
r.write(r.RECORD,record)
evidence={'run_id':run_id,'started_at':datetime.now(UTC).isoformat(),'requests':[],'status':'running','account_or_credentials_changed':False}
try:
    for port in (80,12394):
        for authenticated,endpoints in ((True,['/health','/ready','/api/auth/session','/api/stats/live','/metrics']),(False,['/health','/ready','/api/auth/session','/api/stats/live','/metrics'])):
            for ep in endpoints:
                url=f'http://localhost{":"+str(port) if port!=80 else ""}{ep}'
                headers={'Authorization':'Bearer '+r.ENV['ANIMETTA_ACCESS_TOKEN']} if authenticated else {}
                start=time.perf_counter()
                try:response=urlopen(Request(url,headers=headers),timeout=8)
                except HTTPError as exc:response=exc
                with response:
                    raw=response.read();status=response.status;content_type=response.headers.get('Content-Type','')
                body=json.loads(raw) if 'json' in content_type else {}
                entry={'url':url,'authenticated_request':authenticated,'status':status,'elapsed_seconds':time.perf_counter()-start,'bytes':len(raw),'sha256':r.sha(raw),'content_type':content_type,'response_is_spa_html':'text/html' in content_type}
                for key in ['authenticated','source','ready','status']:
                    if key in body:entry[key]=body[key]
                if isinstance(body.get('error'),dict):entry['error_code']=body['error'].get('code')
                evidence['requests'].append(entry);r.write(path,evidence)
                expected=200 if authenticated or ep=='/health' else 401
                assert status==expected and not entry['response_is_spa_html'],f'Actual {ep} permission/proxy response mismatched'
                if ep=='/api/auth/session' and authenticated:assert body.get('authenticated') is True and body.get('source')=='bearer'
    request=Request('http://localhost/socket.io/?EIO=4&transport=polling',headers={'Origin':'https://invalid-r4.example'})
    try:response=urlopen(request,timeout=8)
    except HTTPError as exc:response=exc
    with response:raw=response.read();status=response.status
    evidence['invalid_origin_engine_handshake']={'status':status,'sha256':r.sha(raw),'bytes':len(raw)}
    assert status==400,'Actual invalid Origin accepted'
    child=subprocess.run(['node',str(r.SCRATCH/'probes/permissions-r4.mjs')],cwd=r.SCRATCH/'probes',env=r.ENV,capture_output=True,timeout=15)
    evidence['invalid_socket_token']=json.loads(child.stdout)
    assert child.returncode==0 and evidence['invalid_socket_token']['status']=='passed'
    evidence['status']='passed'
except Exception as exc:
    evidence['status']='blocked';evidence['error_type']=type(exc).__name__;evidence['error']=str(exc)
finally:
    evidence['finished_at']=datetime.now(UTC).isoformat();r.write(path,evidence)
    record=json.loads(r.RECORD.read_bytes());record['formal_permissions']=evidence
    record['resume'].update(active_probe_run_id=None,next_action='One real role/live natural playback and same-thread continuity probe' if evidence['status']=='passed' else 'Diagnose this original permissions probe; no retry/lifecycle')
    r.write(r.RECORD,record)
print(json.dumps({'run_id':run_id,'status':evidence['status'],'HTTP_checks':len(evidence['requests']),'socket_invalid_token':evidence.get('invalid_socket_token'),'origin':evidence.get('invalid_origin_engine_handshake')},ensure_ascii=False))
raise SystemExit(0 if evidence['status']=='passed' else 1)
