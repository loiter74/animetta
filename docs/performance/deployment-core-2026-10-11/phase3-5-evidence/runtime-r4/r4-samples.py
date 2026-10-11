import importlib.util
import json
import subprocess
import sys
from pathlib import Path

folder = Path(__file__).parent
spec = importlib.util.spec_from_file_location('r4_runner', folder / 'r4-runner.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
r.preserve_auth()
groups = [('app01', 'application_cold'), ('app02', 'application_cold'), ('app03', 'application_cold'), ('re01', 'application_restart_qwen_reused'), ('re02', 'application_restart_qwen_reused'), ('re03', 'application_restart_qwen_reused')]
for suffix, group in groups:
    run_id = 'c-dc4-' + suffix
    current = json.loads(r.RECORD.read_bytes())
    if any(x['run_id']==run_id for x in current['samples'][group]):
        continue
    for operation, identifier in [('anima-down', run_id + '-down'), ('anima-up', run_id)]:
        if identifier in json.loads(r.RECORD.read_bytes())['resume']['completed_runs']:
            continue
        code = r.lifecycle(operation, identifier)
        if code:
            sys.exit(code)
    output = r.MEASURE / (run_id + '-surfaces.json')
    snapshot = {'schema_version':1,'status':'passed','run_id':run_id+'-http-surfaces','evidence_scope':'Authenticated HTTP/page/resource fingerprint only; real native browser playback accepted separately once after final sample','http':{ep:r.http('http://localhost'+ep) for ep in ['/health','/ready','/dashboard','/live.html','/api/auth/session']}}
    r.write(output,snapshot)
    result = subprocess.run(['py', '-3.13', str(folder / 'collect-core.py'), run_id, group], cwd=r.ROOT, env=r.ENV)
    if result.returncode:
        sys.exit(result.returncode)
print(json.dumps({'status': 'six_samples_complete'}), flush=True)
