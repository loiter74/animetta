import importlib.util
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

spec = importlib.util.spec_from_file_location('core_runner', Path(__file__).with_name('r4-runner.py'))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
run_id, group = sys.argv[1:3]
core = json.loads((r.REPORT / 'runtime-core-r4.json').read_bytes())
entry = next(x for x in core['runs'] if x['run_id'] == run_id)
assert entry['status'] == 'passed'
assert not any(x['run_id'] == run_id for x in core['samples'][group])
raw = entry['raw_metrics']
artifact_root = r.ROOT / 'artifacts/iteration-plans' / run_id
receipt_path = artifact_root / 'animetta-build-receipt.json'
if receipt_path.exists():
    receipt_bytes = receipt_path.read_bytes()
    receipt = json.loads(receipt_bytes)
    copied = r.MEASURE / (run_id + '-build-receipt.json')
    copied.write_bytes(receipt_bytes)
    raw['build'] = receipt
    raw['build_receipt_sha256'] = r.sha(receipt_bytes)
    build_log = artifact_root / 'animetta-build.log'
    spec_build = importlib.util.spec_from_file_location('existing_build_phases', r.ROOT / 'scripts/benchmark_startup.py')
    build_module = importlib.util.module_from_spec(spec_build)
    spec_build.loader.exec_module(build_module)
    raw['build']['phases'] = build_module.build_phases(build_log.read_text(encoding='utf-8', errors='replace'))
else:
    raw['build'] = None
    raw['build_reused_existing_image'] = True
r.write(Path(entry['output']), raw)
entry['raw_metrics'] = raw
artifact = r.ROOT / 'artifacts/iteration-plans' / run_id
plan = json.loads((artifact / 'plan.json').read_bytes())
step_ids = [x['id'] for x in plan['steps']]
assert not any('rvc' in x for x in step_ids)
assert not any('rvc' in str(x.get('target', '')).lower() for x in raw['observations'])
steps = {}
for name in ['animetta-start', 'animetta-health', 'animetta-ready', 'frontend-readiness', 'default-log-check']:
    results = sorted((artifact / 'steps' / name / 'windows').glob('*/result.json'))
    passed = [(p, json.loads(p.read_bytes())) for p in results if json.loads(p.read_bytes())['status'] == 'passed']
    assert passed, name
    path, value = passed[-1]
    steps[name] = {'started_at': value['started_at'], 'finished_at': value['feedback_at'], 'elapsed_seconds': value['elapsed_seconds'], 'status': value['status'], 'result_path': str(path)}
state = json.loads(r.command(['docker', 'inspect', '--format', '{{json .State}}', 'anima-animetta-1']))
image = r.command(['docker', 'inspect', '--format', '{{.Image}}', 'anima-animetta-1']).strip()
container_id = r.command(['docker', 'inspect', '--format', '{{.Id}}', 'anima-animetta-1']).strip()
image_size = int(r.command(['docker', 'image', 'inspect', '--format', '{{.Size}}', image]).strip())
image_tag_id = r.command(['docker', 'image', 'inspect', '--format', '{{.Id}}', r.CANDIDATE['image']]).strip()
assert image == image_tag_id
owned = r.ownership()
top = r.command(['docker', 'top', 'anima-animetta-1', '-eo', 'pid,ppid,rss,args'])
backend = next(line for line in top.splitlines() if '-m animetta.core.socketio_server' in line)
rss_kib = int(backend.split(None, 3)[2])
ready = r.http('http://localhost/ready')
health = r.http('http://localhost/health')
gpu = r.command(['nvidia-smi', '--query-gpu=name,memory.total,memory.used,memory.free', '--format=csv,noheader,nounits']).strip()
apps = r.command(['nvidia-smi', '--query-compute-apps=pid,process_name,used_memory', '--format=csv,noheader,nounits']).strip()
profile = {'recorded_at': datetime.now(UTC).isoformat(), 'phase': run_id, 'backend_rss_kib': rss_kib, 'backend_rss_mib': rss_kib / 1024,
           'app_top_rss_kib': top, 'image': {'id': image, 'tag': r.CANDIDATE['image'], 'size_bytes': image_size},
           'docker_stats': r.command(['docker', 'stats', '--no-stream', '--format', 'json', 'anima-animetta-1', 'anima-redis-1']),
           'gpu': gpu, 'gpu_compute_apps': apps, 'host_services': owned['qwen_processes'], 'http': {'ready': ready, 'health': health}}
surfaces_path = r.MEASURE / (run_id + '-surfaces.json')
surface = json.loads(surfaces_path.read_bytes())
parse = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00'))
ready_at = parse(steps['animetta-ready']['finished_at'])
sample = {'run_id': run_id, 'raw_metrics_path': entry['output'], 'raw_metrics_sha256': r.sha(Path(entry['output']).read_bytes()),
          'worker_elapsed_seconds': raw['elapsed_seconds'], 'worker_exit_code': raw['exit_code'], 'build_seconds': raw['build']['elapsed_seconds'] if raw['build'] else None,
          'feedback_windows': raw['feedback_windows'], 'phase_observations': raw['observations'], 'steps': steps,
          'application_start_to_http_ready_seconds': (ready_at - parse(steps['animetta-start']['started_at'])).total_seconds(),
          'container': {'id': container_id, 'image': image, 'started_at': state['StartedAt']},
          'container_start_to_http_ready_seconds': (ready_at - parse(state['StartedAt'])).total_seconds(),
          'qwen_host_processes': owned['qwen_processes'], 'qwen_identity': owned['qwen_identity'], 'gpu': gpu, 'backend_rss_mib': rss_kib / 1024,
          'surface_evidence': surface, 'surface_evidence_path': str(surfaces_path), 'surface_evidence_sha256': r.sha(surfaces_path.read_bytes()),
          'quality_install_overlap': False, 'rvc_plan_steps': [], 'rvc_observation_targets': [], 'rvc_8769_unavailable': True,
          'baseline_clean_performance_comparable': False, 'limit': 'Baseline samples overlapped quality CPU work; caches/model/volumes retained in both groups.'}
r.write(r.MEASURE / (run_id + '-resources.json'), profile)
core['samples'][group].append(sample)
core['resource_profiles'].append(profile)
core['resume']['next_action'] = 'Continue next distinct requested sample; preserve Qwen and collect each original result.'
r.write(r.REPORT / 'runtime-core-r4.json', core)
with (r.REPORT / 'runtime-log.md').open('a', encoding='utf-8') as f:
    f.write(f"\n- Core `{run_id}` {group}: passed; application start→HTTP ready {sample['application_start_to_http_ready_seconds']:.6f}s; container start→ready {sample['container_start_to_http_ready_seconds']:.6f}s; backend RSS {rss_kib/1024:.3f}MiB; image {image} ({image_size} bytes). Same Qwen14240/16104/identity; no RVC step/probe,8769 unavailable; no quality/install overlap. Baseline CPU overlap prevents clean-start speedup attribution.\n")
print(json.dumps({'run_id': run_id, 'app_ready_seconds': sample['application_start_to_http_ready_seconds'], 'container_ready_seconds': sample['container_start_to_http_ready_seconds'], 'build_seconds': sample['build_seconds'], 'backend_rss_mib': rss_kib / 1024, 'image_size_bytes': image_size, 'surface_status': surface.get('status'), 'rvc_steps': []}))
