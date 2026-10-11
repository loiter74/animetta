import importlib.util
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from statistics import median

spec=importlib.util.spec_from_file_location('r4',Path(__file__).with_name('r4-runner.py'))
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
d=json.loads(r.RECORD.read_bytes())
assert d['status']=='acceptance_passed'
assert d['formal_permissions']['status']=='passed'
assert d['boundary_acceptance']['status']=='passed'
assert not d['resume']['active_run_id'] and not d['resume']['active_probe_run_id']
r.verify_input();r.preserve_auth()
host=r.ownership()
actual=json.loads(r.command(['docker','inspect','anima-animetta-1','anima-redis-1']))
app=actual[0]
assert app['Id']==d['boundary_acceptance']['container_id']
assert app['Image']==d['boundary_acceptance']['image_id']
assert app['Config']['Image']==r.CANDIDATE['image']
assert r.command(['docker','image','inspect','--format','{{.Id}}',r.CANDIDATE['old_r3_tag']]).strip()==r.CANDIDATE['old_r3_image']
for container in actual:
    labels=container['Config']['Labels']
    assert Path(labels['com.docker.compose.project.working_dir']).resolve()==r.ROOT
    assert Path(labels['com.docker.compose.project.config_files']).resolve()==r.ROOT/'docker-compose.yml'
    assert labels['com.docker.compose.project']=='anima'
    assert all(m['Type']=='volume' for m in container['Mounts'])
assert {m['Name'] for c in actual for m in c['Mounts']}=={'anima_animetta-data','anima_animetta-memory-db','anima_animetta-redis'}
raw_build=r.MEASURE/'c-dc4-app01-build-receipt.json'
assert raw_build.read_bytes()==(r.ROOT/'artifacts/iteration-plans/c-dc4-app01/animetta-build-receipt.json').read_bytes()

summary={}
for name,samples in d['samples'].items():
    assert len(samples)==3
    assert all(all(x['steps'][step]['status']=='passed' for step in ['animetta-start','animetta-health','animetta-ready','frontend-readiness','default-log-check']) for x in samples)
    for sample in samples:
        assert r.sha(Path(sample['raw_metrics_path']).read_bytes())==sample['raw_metrics_sha256']
        assert r.sha(Path(sample['surface_evidence_path']).read_bytes())==sample['surface_evidence_sha256']
    summary[name]={'n_http_startup_samples':3,'run_ids':[x['run_id'] for x in samples],'metrics':{}}
    for key in ['application_start_to_http_ready_seconds','container_start_to_http_ready_seconds','backend_rss_mib','image_size_bytes']:
        values=[next(p['image']['size_bytes'] for p in d['resource_profiles'] if p['image']['id']==x['container']['image']) if key=='image_size_bytes' else x[key] for x in samples]
        summary[name]['metrics'][key]={'raw':values,'median':median(values),'minimum':min(values),'maximum':max(values)}

v=d['role_acceptance']['raw']
first=d['role_graph_operation_details'][0]
tts=[x for x in first['activities'] if x['name']=='tts.synthesize']
assert len(tts)==1 and tts[0]['provider']=='qwen3-tts-gguf-host' and tts[0]['status']=='success'
media=[x for x in v['live_observations']['media_starts'] if x['task_id']==v['command']['task_id'] and x.get('ended') and x.get('pcm',{}).get('rms',0)>0]
assert len(media)==1
m=media[0]
ttstimes=[]
for turn in d['role_graph_operation_details']:
    operation=next(x for x in turn['activities'] if x['name']=='tts.synthesize')
    ttstimes.append({'task_id':turn['task_id'],'duration_seconds':operation['duration_ms']/1000,'status':operation['status'],'provider':operation['provider'],'raw_path':turn['raw_path'],'raw_sha256':turn['raw_sha256']})
d['final_metrics']={
    'startup':summary,
    'build':{'run_id':'c-dc4-app01','elapsed_seconds':d['runs'][1]['raw_metrics']['build']['elapsed_seconds'],'raw_receipt_path':str(raw_build),'raw_receipt_sha256':r.sha(raw_build.read_bytes()),'cache':'existing normal image/OS/uv/BuildKit caches retained; not fully cold','phase_seconds_are_not_added':'BuildKit phases may overlap'},
    'final_image_size_bytes':summary['application_cold']['metrics']['image_size_bytes']['median'],
    'role':{'run_id':'c-dc4-role01','task_id':v['command']['task_id'],'first_reply_seconds':v['first_reply_seconds'],'qwen_provider_synthesize_seconds':tts[0]['duration_ms']/1000,'qwen_provider_synthesize_scope':'Actual instrumented tts.synthesize span includes provider HTTP transport and native synthesis; excludes browser playback; host kernel-only time not separately measured','first_native_playing_seconds':v['first_native_audio_start_seconds'],'natural_native_playing_to_ended_seconds':(m['ended_epoch_ms']-m['playing_epoch_ms'])/1000,'actual_wav_duration_seconds':m['pcm']['duration_seconds'],'actual_wav_sha256':m['blob_sha256'],'actual_wav_rms':m['pcm']['rms'],'actual_wav_nonzero_samples':m['pcm']['nonzero_samples'],'actual_wav_sample_count':m['pcm']['sample_count'],'same_task_persistent_playback_count':v['live_after']['playbackCount'],'same_task_persistent_playback_state':v['live_after']['playbackState'],'same_task_lip_sync_applied_count':v['live_after']['lipSyncAppliedCount'],'same_task_lip_sync_peak':v['live_after']['lipSyncPeak'],'tts_spans_all_real_turns':ttstimes},
    'sample_scope':'All 6 canonical lifecycle HTTP-ready startup timings passed. The original app01 browser/API surface probe has zero successful samples and is excluded from successful surface acceptance; it is not retroactively marked passed. App02..re03 surface snapshots are HTTP/resource checks, not browser playback proofs. Final role01 is the actual browser playback/continuity proof.'
}
d['final_recheck']={'recorded_at':datetime.now(UTC).isoformat(),'same_final_container_id':app['Id'],'same_final_image_id':app['Image'],'same_final_unique_tag':app['Config']['Image'],'stable_ROOT_compose_labels':True,'same_three_named_volumes':True,'old_r3_tag_and_image_preserved':True,'frozen_root_files_and_private_env_hash_unchanged':True,'host':host,'new_lifecycle_actions':0}
d['limits']=[
    'Original app01 formal BrowserContext auth/session GET timed out at 30s. Current 80/12394 API/Nginx/backend/Redis and same BrowserContext diagnostics passed. Original mechanism remains unresolved because its container/logs were already removed by the distinct authorized next sample; no product fix claimed. Original failure preserved with 0 successful browser samples.',
    'Instrumented diagnostic03 outer subprocess timed out at 25s, before stage instrumentation existed; diagnostic04 retained each stage and passed. No model/lifecycle retry was used for browser diagnosis.',
    'Dashboard account login and authenticated Dashboard chat UI not accepted: this task has no account password. Existing machine token API/Socket role and unauthenticated permission boundaries accepted; no account reset.',
    'Baseline startup samples overlapped parent quality CPU load. r4 samples had no quality/install overlap. No clean startup acceleration percentage or build-cache benefit is claimed.',
    'Application-cold and reused-Qwen groups both retain image/OS caches, named volumes and loaded same-PID Qwen. These are new application-process cycles, not machine/model cold starts.',
    'app03 canonical protocol terminal was recovered from its original receipts after its outer wrapper was interrupted for diagnosis; wrapper elapsed is unavailable, canonical application/container timestamps are measured.',
    'Qwen synthesis timing is the actual provider span including HTTP/native work, not isolated GPU kernel timing. Natural native playback is shown in real headless Chromium; physical speaker sound was not independently measured.',
    'Ordinary fact continuity proves short-term same graph thread only; production long_term_memory_mode remains off. No manual data/database write or long-term persistence claim.',
    'RVC and other optional features stayed off; no RVC start/preflight, optional service/GPU/install acceptance was added.'
]
d['efficiency_retrospective']={'waste_path':'Browser timeout initially lacked incremental stage output, requiring a second instrumented bounded diagnostic. One generic CodeGraph query returned unrelated implementations before a precise stats symbol query.', 'root':'Insufficient stage evidence in the one-off browser driver and ambiguous symbol search; original transient timeout itself was not proven.', 'persistence':'Task-local diagnostic04 emits dated stages; task-local acceptance sanitizes known secret values before persisting stdout/stderr. Product/Skill inputs remain frozen.', 'next_path':'Exact current formal API and same-context bounded stage diagnostic, preserve original failure, then one real native role probe; no successful lifecycle/sample repetition.'}
d['simplify_review']={'reuse':'Existing validated canonical CLI driver, original sample definitions and corrected NativeHTML/ordinary-fact probe retained. One final record and byte index reference small raw evidence instead of copying full lifecycle feedback plans.', 'scope':'No product/framework changes, no broader tests or probes added at finalization.'}

failed=r.MEASURE/'c-dc4-browser-api-diagnostic03-result.json'
assert not failed.exists()
r.write(failed,{'run_id':'c-dc4-browser-api-diagnostic03','status':'blocked','exit_code':1,'outer_timeout_seconds':25,'exec_session':93524,'source':'Historical outer tool TimeoutExpired receipt; reconstructed summary, not a raw child result','child_output_available':False,'exact_failure_stage':'not recorded','counts_as_success':False,'terminal_preserved_no_retry':True})
d['status']='complete_with_recorded_limits';d['finished_at']=datetime.now(UTC).isoformat()
d['resume'].update(active_run_id=None,active_probe_run_id=None,canonical_pid=None,next_action='Parent archive small r4 evidence and final metadata; cleanup/commit remain parent actions. No lifecycle/probe pending.')
r.write(r.RECORD,d)
with (r.REPORT/'runtime-log.md').open('a',encoding='utf-8') as log:
    log.write('\n- Final ROOT r4 acceptance complete. Cold app-to-ready seconds: 37.086711, 23.942956, 23.345424; reused-Qwen: 23.939391, 22.778336, 24.191220. Image 614348725 bytes; build 247.7564864s with retained normal caches. No clean speedup attribution.\n')
    log.write(f"- Real role01 reply {v['first_reply_seconds']}s, Qwen provider synthesize {tts[0]['duration_ms']/1000}s, native playing {v['first_native_audio_start_seconds']}s; WAV RMS {m['pcm']['rms']}, duration {m['pcm']['duration_seconds']}s, natural ended. Same graph thread has history windows 0→1→2→3, ordinary exact fact recall passed; tools false/empty, no tool graph node, no optional loader path, FTS5/ASR-VAD readiness accepted.\n")
    log.write('- Original app01 30s auth-session timeout and diagnostic03 25s timeout remain failed/blocked evidence. Current exact BrowserContext/auth/Nginx/backend/Redis and final 20 permission/API checks passed; original timeout mechanism unresolved, no product repair claimed. Dashboard account-login UI and physical speaker measurement not accepted.\n')
    log.write('- Final container/unique image unchanged, Compose labels stable ROOT, original three volumes and old r3 image retained; Qwen14240/16104 identity/creation/voice preserved, RVC8769 unavailable. No cleanup, commit, push, or additional lifecycle performed.\n')

# Scan only this task's small files. Never touch automatic artifacts or parent evidence.
files=[]
for root,dirs,names in os.walk(r.SCRATCH,followlinks=False):
    dirs[:]=[x for x in dirs if x not in ['node_modules','__pycache__']]
    for name in names:
        path=Path(root)/name
        if name not in ['evidence-index.json','secret-scan.json']:files.append(path)
matches=[]
for path in files:
    raw=path.read_bytes()
    for secret in r.SECRETS:
        if len(secret)>=8 and secret.encode() in raw:
            matches.append(str(path.relative_to(r.SCRATCH)))
            break
scan={'recorded_at':datetime.now(UTC).isoformat(),'status':'passed' if not matches else 'blocked','known_secret_value_scan':'Current ROOT dotenv, inherited secret-named values, retained actual auth password hash; values length >=8; no values printed','scanned_files':len(files),'matches_paths_only':matches,'original_app01_secret_exception_redaction':'Original private bytes not retained; redacted raw and redaction receipt preserved','automatic_artifacts_edited':False}
r.write(r.SCRATCH/'secret-scan.json',scan)
assert not matches,'Secret scan blocked handoff; filenames only in secret-scan.json'
files.append(r.SCRATCH/'secret-scan.json')

# Keep full feedback JSON logs in local run folders, outside small delivery index.
excluded={f'measurements/{x["run_id"]}.log' for x in d['runs']}
index_files=[p for p in files if p.relative_to(r.SCRATCH).as_posix() not in excluded]
index={'schema_version':1,'frozen_at':datetime.now(UTC).isoformat(),'status':'frozen','root':str(r.SCRATCH),'record':'runtime-core-r4.json','source_root':str(r.ROOT),'image_tag':r.CANDIDATE['image'],'files':[{'path':p.relative_to(r.SCRATCH).as_posix(),'bytes':p.stat().st_size,'sha256':r.sha(p.read_bytes())} for p in sorted(index_files)],'excluded_full_lifecycle_feedback_logs':sorted(excluded),'self_sha256_omitted':True,'raw_policy':'Existing raw bytes retained exactly; build receipt verified equal to automatic original. App01 secret-bearing exception is explicitly redacted with original/private hash in receipt. No normalization, .env/source archive/image/automatic feedback plan copy.'}
r.write(r.SCRATCH/'evidence-index.json',index)
for x in index['files']:assert r.sha((r.SCRATCH/x['path']).read_bytes())==x['sha256']
state_path=r.ROOT/'.zcode/performance/deployment-core-20261011/finalization-state.json'
state_raw=state_path.read_bytes();state=json.loads(state_raw)
state['runtime_final_r4'].update(active_session=None,active_step='done; byte-frozen small evidence ready for parent archive',updated_at=datetime.now(UTC).isoformat(),acceptance_status='passed_with_recorded_limits',index_path=str(r.SCRATCH/'evidence-index.json'),index_sha256=r.sha((r.SCRATCH/'evidence-index.json').read_bytes()),record_sha256=r.sha(r.RECORD.read_bytes()),raw_secret_scan_status='passed',sample_counts={k:3 for k in d['samples']},final_image_size_bytes=614348725,original_api_timeout_root_cause='unresolved; original failure retained, current formal exact-context chain passed')
encoded=json.dumps(state,ensure_ascii=False,indent=2)+'\n'
if b'\r\n' in state_raw:encoded=encoded.replace('\n','\r\n')
assert state_path.read_bytes()==state_raw
state_path.write_bytes(encoded.encode())
print(json.dumps({'status':d['status'],'index_files':len(index['files']),'index_bytes':sum(x['bytes'] for x in index['files']),'record_sha256':r.sha(r.RECORD.read_bytes()),'index_sha256':r.sha((r.SCRATCH/'evidence-index.json').read_bytes()),'app_cold_median_seconds':summary['application_cold']['metrics']['application_start_to_http_ready_seconds']['median'],'qwen_reuse_median_seconds':summary['application_restart_qwen_reused']['metrics']['application_start_to_http_ready_seconds']['median'],'qwen_first_provider_synthesize_seconds':tts[0]['duration_ms']/1000,'secret_scan':scan['status']},ensure_ascii=False))
