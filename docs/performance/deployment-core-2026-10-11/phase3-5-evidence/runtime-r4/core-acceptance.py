import importlib.util
import json
import subprocess
import re
import ast
from datetime import UTC, datetime
from pathlib import Path

spec = importlib.util.spec_from_file_location('core_runner', Path(__file__).with_name('r4-runner.py'))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
core = json.loads((r.REPORT / 'runtime-core-r4.json').read_bytes())
assert core['boundary_acceptance']['status'] == 'passed'
assert core['resume']['active_run_id'] is None
assert 'role_acceptance' not in core, 'Do not repeat completed or terminal role probe'
r.verify_input()
r.preserve_auth()
before_host = r.ownership()
probe = r.SCRATCH / 'probes/core-role-probe-r4.mjs'
before = datetime.now(UTC).isoformat()
core['resume'].update({'active_probe_run_id': 'c-dc4-role01', 'next_action': 'One real role/native playback/continuity probe executing; no repeat or new lifecycle.'})
core['role_probe_input'] = {'path': str(probe), 'sha256': r.sha(probe.read_bytes()), 'started_at': before,
                            'performance_prompt_unchanged': True, 'continuity_turns': 2, 'continuity_fact': 'ordinary non-sensitive lunch; no acceptance marker', 'auth': 'Socket.IO auth.token from child environment; no secret persisted'}
r.write(r.REPORT / 'runtime-core-r4.json', core)
result = subprocess.run(['node', str(probe)], cwd=probe.parent, env=r.ENV, capture_output=True, timeout=450)
def sanitized(raw):
    for secret in r.SECRETS:
        if len(secret) >= 8:
            raw = raw.replace(secret.encode(), b'<redacted>')
    return raw
stdout, stderr = sanitized(result.stdout), sanitized(result.stderr)
raw_path = r.MEASURE / 'c-dc4-role01.json'
raw_path.write_bytes(stdout)
stderr_path = r.MEASURE / 'c-dc4-role01-stderr.log'
stderr_path.write_bytes(stderr)
value = json.loads(stdout)
assert r.ENV['ANIMETTA_ACCESS_TOKEN'].encode() not in stdout
after_host = r.ownership()
core = json.loads((r.REPORT / 'runtime-core-r4.json').read_bytes())
core['role_acceptance'] = {'raw': value, 'raw_path': str(raw_path), 'raw_sha256': r.sha(stdout), 'process_exit_code': result.returncode,
                           'host_before': before_host, 'host_after': after_host, 'browser_stderr_bytes': len(result.stderr)}
r.write(r.RECORD, core)
tasks = [value['command']['task_id']] + [x['command']['task_id'] for x in value.get('continuity', {}).get('rounds', [])]
stats = r.http('http://localhost/api/stats/live')['body']
turns = []
def walk(x):
    if isinstance(x, dict):
        if x.get('trace_id') in tasks:
            turns.append(x)
        else:
            for v in x.values():
                walk(v)
    elif isinstance(x, list):
        for v in x:
            walk(v)
walk(stats)
# Docker's backend log stream is stderr; capture both without persisting unrelated raw logs.
captured = subprocess.run(['docker', 'logs', '--since', before, '--tail', '500', 'anima-animetta-1'], cwd=r.SOURCE, env=r.ENV, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
lines = [re.sub(r'\x1b\[[0-9;]*m','',s) for s in (captured.stdout + captured.stderr).splitlines()]
selected = [line for line in lines if any(t in line for t in tasks) or any(x in line for x in ['graph:process_text', 'graph:_run_graph', 'nodes.llm', 'nodes.tts', 'nodes.response', 'nodes.output', '_run_graph', 'Processing text input', 'Registered nodes:', 'Tool config status:', 'self.enable_tools=', 'Tools disabled', '_load_tools_config', '_load_tools:'])]
graph = {'recorded_at': datetime.now(UTC).isoformat(), 'task_ids': tasks, 'live_role_turns': turns,
         'all_tasks_found': set(tasks) <= {x['trace_id'] for x in turns},
         'all_turn_outcomes_success': len(turns) == len(tasks) and all(x['outcome'] == 'success' for x in turns),
         'actual_conversation_ids': sorted({x['conversation_id'] for x in turns}),
         'same_effective_conversation': len({x['conversation_id'] for x in turns}) == 1,
         'actual_roles': sorted({x['actor_role'] for x in turns}), 'actual_sources': sorted({x['source'] for x in turns}),
         'actual_audiences': sorted({x['audience'] for x in turns}), 'selected_graph_log_lines': selected,
         'stats_metrics': stats.get('metrics'), 'long_term_memory_mode': 'off unchanged; no durable long-term write claim'}
r.write(r.MEASURE / 'c-dc4-role01-graph.json', graph)

socket = value.get('continuity', {}).get('socket_id')
starts=[s for s in lines if socket and socket in s and '_run_graph starting' in s]
ends=[s for s in lines if socket and socket in s and '_run_graph completed' in s]
window_start=[int(re.search(r'window_pairs=(\d+)',s)[1]) for s in starts]
window_end=[int(re.search(r'window_pairs=(\d+)',s)[1]) for s in ends]
graph.update({'actual_graph_thread_id':socket,'actual_channel_id':socket,
 'thread_identity_evidence':'Actual logs same session_id; actual-container orchestrator matches frozen source config thread_id=session_id; history_authority=conversation_registry.',
 'actual_same_graph_thread':len(starts)==3 and len(ends)==3 and window_start[2]==window_end[1] and window_start[2]>0,
 'window_pairs_start':window_start,'window_pairs_end':window_end})
node_lists=[ast.literal_eval(s.split('Registered nodes: ',1)[1]) for s in lines if 'Registered nodes: ' in s]
loader_lines=[s for s in lines if '_load_tools_config' in s or 'orchestrator:_load_tools:' in s]
tool_status=[s for s in lines if socket and socket in s and ('Tool config status:' in s or 'self.enable_tools=' in s)]
assert socket and node_lists, 'Need actual graph registration evidence'
assert all('tools' not in xs for xs in node_lists), 'Actual graph registered tools'
assert not loader_lines, 'Optional tool config/load path executed'
assert any('enable_tools=False, config_keys=[]' in s for s in tool_status), 'Actual session tools config was not false/empty'
probe_source="from pathlib import Path;import hashlib,json;ps=['src/animetta/orchestration/server/session.py','src/animetta/orchestration/graph/orchestrator.py'];print(json.dumps({p:hashlib.sha256(Path('/app',p).read_bytes()).hexdigest() for p in ps}))"
source_hashes=json.loads(r.command(['docker','exec','anima-animetta-1','python','-c',probe_source]))
assert all(r.sha((r.SOURCE/p).read_bytes())==h for p,h in source_hashes.items())
tools={'status':'passed','actual_enable_tools':False,'actual_config_keys':[], 'actual_registered_graph_nodes':node_lists,
 'tool_node_registered':False,'optional_tool_yaml_loader_executed':False,'tool_loading_logs':loader_lines,
 'actual_session_status_logs':tool_status,'actual_container_source_sha256':source_hashes,
 'proof_scope':'All stdout+stderr from real application over this sole-owner formal role/continuity interval; actual false/empty session log, registered graph node lists, no loader logs, and matching actual frozen guard source.',
 'r2_defect_retested_in_r4':True}
r.write(r.MEASURE/'c-dc4-role01-tools-boundary.json',tools)
core['tools_boundary_acceptance']=tools
r.write(r.MEASURE/'c-dc4-role01-graph.json',graph)
core['role_graph_evidence'] = graph

core['resume']['active_probe_run_id'] = None
core['resume']['next_action'] = 'Finalize raw metrics, comparison limits and byte-preserving evidence index; no lifecycle rerun.'
core['status'] = 'acceptance_passed' if value['status'] == 'passed' and value.get('continuity', {}).get('status') == 'passed' and graph['all_turn_outcomes_success'] and graph['actual_same_graph_thread'] and tools['status']=='passed' else 'acceptance_requires_diagnosis'
r.write(r.REPORT / 'runtime-core-r4.json', core)
with (r.REPORT / 'runtime-log.md').open('a', encoding='utf-8') as f:
    f.write(f"\n- Core real role probe `c-dc4-role01` finished {datetime.now(UTC).isoformat()}: {value['status']}; task `{tasks[0]}`, reply {value.get('first_reply_seconds')}s/native audio {value.get('first_native_audio_start_seconds')}s; persistent playback {value.get('live_persistent_playback')}, natural nonzero audio {value.get('native_nonzero_audio_completed')}; Live2D model runtime loaded {value.get('live2d_model_runtime_loaded')}/same-task mouth {value.get('live2d_real_task_mouth_applied')}; continuity {value.get('continuity', {}).get('status')}; graph task outcomes {graph['all_turn_outcomes_success']}. Qwen same identity/PID, RVC8769 unavailable. Raw JSON `{raw_path}` SHA256 `{r.sha(stdout)}`; no mock, no account/data edits.\n")
print(json.dumps({'status': core['status'], 'task_id': tasks[0], 'reply_seconds': value.get('first_reply_seconds'), 'native_audio_seconds': value.get('first_native_audio_start_seconds'),
                  'persistent_playback': value.get('live_persistent_playback'), 'natural_nonzero_audio': value.get('native_nonzero_audio_completed'),
                  'model_loaded': value.get('live2d_model_runtime_loaded'), 'mouth_task_applied': value.get('live2d_real_task_mouth_applied'),
                  'continuity_status': value.get('continuity', {}).get('status'), 'all_graph_tasks_success': graph['all_turn_outcomes_success']}, ensure_ascii=False))
