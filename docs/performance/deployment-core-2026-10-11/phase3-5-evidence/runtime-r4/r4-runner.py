import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

import psutil
from dotenv import dotenv_values

ROOT = Path(r'C:\Users\30262\Project\Anima')
SCRATCH = Path(__file__).parent
REPORT = SCRATCH
MEASURE = SCRATCH / 'measurements'
RECORD = SCRATCH / 'runtime-core-r4.json'
SOURCE = ROOT
BASE = json.loads((ROOT / 'docs/performance/deployment-core-2026-10-11/runtime-baseline.json').read_bytes())
OLD = json.loads((ROOT / 'docs/performance/deployment-core-2026-10-11/runtime-core-r3.json').read_bytes())
ENV = os.environ.copy()
ENV.update({k: v for k, v in dotenv_values(ROOT / '.env').items() if v is not None})
ENV.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1', BUILDKIT_PROGRESS='plain', COMPOSE_PROJECT_NAME='anima', COMPOSE_FILE=str(ROOT / 'docker-compose.yml'), COMPOSE_ENV_FILES=str(ROOT / '.env'), ANIMETTA_HTTP_PORT='80', ANIMETTA_PORT='12394', ANIMETTA_PROFILE='production')
for key in ('ANIMETTA_EARTH_ENABLED', 'ANIMETTA_MEDIA_ENABLED'):
    ENV.pop(key, None)
SECRETS = [v for k, v in ENV.items() if v and re.search(r'PASSWORD|TOKEN|SECRET|API_KEY|COOKIE', k, re.I)]
CANDIDATE = json.loads(RECORD.read_bytes())['frozen_input'] if RECORD.exists() else {}
if CANDIDATE:
    ENV['ANIMETTA_IMAGE'] = CANDIDATE['image']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    raw = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    for secret in SECRETS:
        if len(secret) >= 8:
            raw = raw.replace(secret, '<redacted>')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw.encode('utf-8'))
    if path == RECORD:
        state_path = ROOT / '.zcode/performance/deployment-core-20261011/finalization-state.json'
        state_raw = state_path.read_bytes()
        state = json.loads(state_raw)
        section = state.setdefault('runtime_final_r4', {})
        section.update(status=value['status'], updated_at=datetime.now(UTC).isoformat(), run_id=value['resume'].get('active_run_id'), active_probe_run_id=value['resume'].get('active_probe_run_id'), canonical_pid=value['resume'].get('canonical_pid'), completed_runs=value['resume']['completed_runs'], next_action=value['resume']['next_action'], record_path=str(RECORD), evidence_root=str(SCRATCH), image_tag=value['frozen_input']['image'])
        encoded = json.dumps(state, ensure_ascii=False, indent=2) + '\n'
        if b'\r\n' in state_raw:
            encoded = encoded.replace('\n', '\r\n')
        assert state_path.read_bytes() == state_raw, 'Parent state changed concurrently; do not overwrite'
        state_path.write_bytes(encoded.encode('utf-8'))


def command(argv, timeout=30):
    result = subprocess.run(argv, cwd=ROOT, env=ENV, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
    assert result.returncode == 0, f'Read-only command failed: {argv[:3]}'
    return result.stdout


def http(url, key='ANIMETTA_ACCESS_TOKEN'):
    with urlopen(Request(url, headers={'Authorization': 'Bearer ' + ENV[key]}), timeout=20) as response:
        raw = response.read()
        return {'status': response.status, 'bytes': len(raw), 'sha256': sha(raw), 'body': json.loads(raw) if raw.startswith(b'{') else None,
                'assets': re.findall(r'(?:src|href)=[\"\']([^\"\']+\.(?:js|css)[^\"\']*)', raw.decode('utf-8', 'replace'))}


def process(p):
    return {'pid': p.pid, 'creation_time': p.create_time(), 'command_line': p.cmdline(), 'rss_bytes': p.memory_info().rss}


def ownership():
    processes = []
    for expected in OLD['preflight']['qwen_processes']:
        p = psutil.Process(expected['pid'])
        assert abs(p.create_time() - expected['creation_time']) < 0.01
        assert p.cmdline() == expected['command_line']
        processes.append(process(p))
    competing = []
    allowed_parents = set()
    for parent in psutil.Process().parents():
        try:
            if any(Path(x).resolve() == SCRATCH / 'r4-samples.py' for x in parent.cmdline() if x.endswith('.py')):
                allowed_parents.add(parent.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    for p in psutil.process_iter(['name', 'cmdline']):
        try:
            if p.pid == os.getpid() or p.pid in allowed_parents:
                continue
            a = p.info['cmdline'] or []
            n = (p.info['name'] or '').lower()
            module = a[a.index('-m') + 1] if '-m' in a and len(a) > a.index('-m') + 1 else ''
            script = next((Path(x).name for x in a[1:] if x.endswith('.py')), '')
            lifecycle = n.startswith('python') and script in {'runtime_lifecycle.py', 'benchmark_startup.py', 'r4-runner.py', 'r4-samples.py'}
            quality = n.startswith('python') and module in {'tooling.quality', 'pytest', 'mypy', 'pip'}
            install = n in {'uv.exe', 'pnpm.exe'} and any(x in a for x in ['sync', 'install', 'test'])
            frontend = n == 'node.exe' and any(('vitest' in x or 'vue-tsc' in x) for x in a)
            training = n.startswith('python') and bool(re.match(r'(train|training).*\.py$', script, re.I))
            if lifecycle or quality or install or frontend or training:
                competing.append(process(p))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    assert not competing, 'Competing process detected; preserve current run'
    with socket.socket() as s:
        s.settimeout(2)
        assert s.connect_ex(('127.0.0.1', 8769)) != 0
    identity = {ep: http('http://127.0.0.1:8767' + ep, 'QWEN_TTS_API_KEY')['body'] for ep in ['/ready', '/v1/identity']}
    assert identity == BASE['qwen_ready_identity']
    return {'qwen_processes': processes, 'qwen_identity': identity, 'rvc_port_8769_unavailable': True, 'competing_processes': competing}


def verify_input():
    manifest = json.loads((SCRATCH / 'frozen-root-input.json').read_bytes())
    assert all(sha((ROOT / path).read_bytes()) == value for path, value in manifest['files'].items()), 'Frozen ROOT input changed'
    assert sha((ROOT / '.env').read_bytes()) == manifest['env_sha256'], 'Private env changed'


def preserve_auth():
    containers = json.loads(command(['docker', 'inspect', 'anima-animetta-1']))
    actual = dict(x.split('=', 1) for x in containers[0]['Config']['Env'] if '=' in x)
    result = {}
    for key in ('ANIMETTA_ACCESS_TOKEN', 'QWEN_TTS_API_KEY', 'ANIMETTA_AUTH_USERNAME', 'ANIMETTA_AUTH_PASSWORD_HASH'):
        expected = ENV.get(key)
        if expected:
            assert expected == actual.get(key), f'Identity/credential changed: {key}'
        elif actual.get(key):
            ENV[key] = actual[key]
            if len(actual[key]) >= 8:
                SECRETS.append(actual[key])
        result[key] = {'present': bool(actual.get(key)), 'continuous': True}
    return result


def preflight():
    global CANDIDATE
    assert not RECORD.exists(), 'Read existing r4 record; never reset'
    assert sys.version_info >= (3, 13)
    gate_path = ROOT / '.zcode/performance/deployment-core-20261011/phase3-5-quality-r4/summary.json'
    gate = json.loads(gate_path.read_bytes())
    assert gate['status'] == 'passed' and gate['plan_hash'] == '54eb7ff41bcdf4c7c8a59475018bff43d4451a903061e2ebfc4e750626a914b5'
    assert all(not gate[k] for k in ('failed_groups', 'blocked_groups', 'missing_groups', 'cancelled_groups'))
    plan = json.loads((ROOT / '.zcode/performance/deployment-core-20261011/phase3-5-final-r4-plan.json').read_bytes())
    assert plan['plan_hash'] == gate['plan_hash'] and not plan['unmapped_paths']
    action = next(x for x in gate['docker_actions'] if x['scope_id'] == 'animetta')
    files = sorted({p.relative_to(ROOT).as_posix() for pattern in action['input_patterns'] for p in ROOT.glob(pattern) if p.is_file()})
    files += ['docker-compose.yml', 'scripts/runtime_lifecycle.py', 'scripts/benchmark_startup.py', 'frontend/scripts/benchmark-startup.mjs']
    mapping = {p: sha((ROOT / p).read_bytes()) for p in sorted(set(files))}
    manifest = {'schema_version': 1, 'recorded_at': datetime.now(UTC).isoformat(), 'source_root': str(ROOT), 'files': mapping, 'env_sha256': sha((ROOT / '.env').read_bytes()), 'training_songs_user_data_excluded_from_docker_copy': True, 'dockerignore_sha256': mapping['.dockerignore']}
    write(SCRATCH / 'frozen-root-input.json', manifest)
    tag = 'animetta:deployment-core-core-r4-' + action['input_fingerprint'][:12] + '-' + uuid.uuid4().hex[:8]
    ENV['ANIMETTA_IMAGE'] = tag
    old_image = command(['docker', 'inspect', '--format', '{{.Image}}', 'anima-animetta-1']).strip()
    old_tag = command(['docker', 'inspect', '--format', '{{.Config.Image}}', 'anima-animetta-1']).strip()
    exists = subprocess.run(['docker', 'image', 'inspect', tag], cwd=ROOT, env=ENV, capture_output=True)
    assert exists.returncode != 0
    auth = preserve_auth()
    owned = ownership()
    command(['docker', 'compose', 'config', '--quiet'])
    CANDIDATE = {'source_root': str(ROOT), 'image': tag, 'input_fingerprint': action['input_fingerprint'], 'manifest_path': str(SCRATCH / 'frozen-root-input.json'), 'manifest_sha256': sha((SCRATCH / 'frozen-root-input.json').read_bytes()), 'file_count': len(mapping), 'old_r3_image': old_image, 'old_r3_tag': old_tag, 'compose_project': 'anima', 'compose_file': str(ROOT / 'docker-compose.yml'), 'profile': 'production', 'ports': {'http': 80, 'backend': 12394}}
    record = {'schema_version': 1, 'revision': 'core-r4-final-root', 'status': 'preflight_passed', 'started_at': datetime.now(UTC).isoformat(), 'frozen_input': CANDIDATE, 'authorization': {'gate_status': 'passed', 'plan_hash': gate['plan_hash'], 'summary_path': str(gate_path), 'summary_sha256': sha(gate_path.read_bytes()), 'executed_groups': len(gate['executed_groups']), 'unmapped_paths': []}, 'preflight': {**owned, 'auth_identity_continuity': auth, 'compose_config_quiet_exit_code': 0}, 'sample_definitions': OLD['sample_definitions'], 'runs': [], 'samples': {'application_cold': [], 'application_restart_qwen_reused': []}, 'resource_profiles': [], 'comparability': {'quality_install_overlap': False, 'baseline_quality_cpu_overlap': True, 'hardware_disk_cache_cold': False, 'build_cache_retained': True, 'clean_start_speedup_claim_supported': False, 'timing_driver': 'Canonical CLI; same lifecycle feedback step timestamps as r3 for application/container-to-ready; wrapper wall clock is separate'}, 'resume': {'scratch_root': str(SCRATCH), 'completed_runs': [], 'active_run_id': None, 'active_probe_run_id': None, 'next_action': 'c-dc4-down01 then c-dc4-app01; canonical ROOT CLI; never repeat terminal run'}}
    write(RECORD, record)
    print(json.dumps({'status': 'preflight_passed', 'image': tag, 'frozen_files': len(mapping), 'qwen_pids': [x['pid'] for x in owned['qwen_processes']]}))


def lifecycle(operation, run_id):
    verify_input()
    ownership()
    if operation == 'anima-down':
        preserve_auth()
    core = json.loads(RECORD.read_bytes())
    existing = next((x for x in core['runs'] if x['run_id'] == run_id), None)
    if existing:
        assert 'exit_code' not in existing and not core['resume'].get('canonical_pid') and not (ROOT / 'artifacts/iteration-plans' / run_id).exists(), 'Never repeat launched run'
    else:
        assert not core['resume']['active_run_id'], 'Another run is active'
    MEASURE.mkdir(parents=True, exist_ok=True)
    argv = ['py', '-3.13', 'scripts/runtime_lifecycle.py', operation, '--run-id', run_id, '--wait', '--artifacts-root', str(ROOT / 'artifacts/iteration-plans')]
    entry = {'run_id': run_id, 'operation': operation, 'command': argv, 'cwd': str(ROOT), 'started_at': datetime.now(UTC).isoformat(), 'quality_install_overlap': False, 'output': str(MEASURE / (run_id + '.json')), 'outer_log': str(MEASURE / (run_id + '.log'))}
    if existing:
        entry['prelaunch_driver_recovery'] = 'Outer log directory missing; confirmed canonical subprocess/artifact never launched, resume same original ID after mkdir'
        core['runs'][-1] = entry
    else:
        core['runs'].append(entry)
    core['status'] = 'running'
    core['resume'].update(active_run_id=run_id, next_action='Read this same run receipt while canonical CLI handles bounded continuations; never create competing run')
    write(RECORD, core)
    started = time.perf_counter()
    with Path(entry['outer_log']).open('wb') as log:
        child = subprocess.Popen(argv, cwd=ROOT, env=ENV, stdout=log, stderr=subprocess.STDOUT)
        core['resume']['canonical_pid'] = child.pid
        write(RECORD, core)
        exit_code = child.wait()
    raw = {'schema_version': 1, 'run_id': run_id, 'operation': operation, 'exit_code': exit_code, 'elapsed_seconds': time.perf_counter() - started, 'feedback_windows': None, 'continuation_wait_seconds': None, 'observations': [], 'error': None, 'build': None, 'measurement_driver': 'actual canonical ROOT CLI; step receipts collected without replacing protocol'}
    artifact = ROOT / 'artifacts/iteration-plans' / run_id
    receipt = artifact / 'animetta-build-receipt.json'
    if receipt.exists():
        build = json.loads(receipt.read_bytes())
        write(MEASURE / (run_id + '-build-receipt.json'), build)
        raw['build_receipt_path'] = str(MEASURE / (run_id + '-build-receipt.json'))
    write(Path(entry['output']), raw)
    entry.update(finished_at=datetime.now(UTC).isoformat(), exit_code=exit_code, raw_metrics=raw, status='passed' if exit_code == 0 else 'failed')
    core = json.loads(RECORD.read_bytes())
    core['runs'][-1] = entry
    core['status'] = entry['status']
    core['resume']['active_run_id'] = None
    core['resume']['canonical_pid'] = None
    if exit_code == 0:
        core['resume']['completed_runs'].append(run_id)
    core['resume']['next_action'] = 'Collect completed receipts before next sample' if exit_code == 0 else 'Diagnose original terminal run; no retry'
    write(RECORD, core)
    ownership()
    print(json.dumps({'run_id': run_id, 'status': entry['status'], 'exit_code': exit_code, 'elapsed_seconds': raw['elapsed_seconds']}), flush=True)
    return exit_code


if __name__ == '__main__':
    if sys.argv[1] == 'preflight':
        preflight()
    elif sys.argv[1] == 'lifecycle':
        sys.exit(lifecycle(sys.argv[2], sys.argv[3]))
