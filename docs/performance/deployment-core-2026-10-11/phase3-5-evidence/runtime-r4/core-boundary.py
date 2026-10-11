import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path

spec = importlib.util.spec_from_file_location('core_runner', Path(__file__).with_name('r4-runner.py'))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
core = json.loads((r.REPORT / 'runtime-core-r4.json').read_bytes())
assert len(core['samples']['application_cold']) == 3
assert len(core['samples']['application_restart_qwen_reused']) == 3
assert core['resume']['active_run_id'] is None
probe = '''import importlib.metadata as m, importlib.util as u, json, sys, shutil; from pathlib import Path
names=['bilibili-api-python','langchain-community','torch','transformers','chromadb','demucs','torchaudio','faiss-cpu']
versions={}
for name in names:
 try: versions[name]=m.version(name)
 except m.PackageNotFoundError: versions[name]=None
modules={name:u.find_spec(name) is not None for name in ['bilibili_api','langchain_community','torch','transformers','chromadb','demucs','torchaudio']}
print(json.dumps({'python':sys.version,'executable':sys.executable,'distribution_versions':versions,'module_discoverability':modules,'installed_package_count':len(list(m.distributions())), 'ffmpeg_executable':shutil.which('ffmpeg'), 'cesium_paths':[str(p) for p in Path('/app/frontend/dist').rglob('*') if 'cesium' in p.name.lower()]}))
'''
packages = json.loads(r.command(['docker', 'exec', 'anima-animetta-1', 'python', '-c', probe]))
assert all(v is None for v in packages['distribution_versions'].values())
assert all(v is False for v in packages['module_discoverability'].values())
assert packages['ffmpeg_executable'] is None and not packages['cesium_paths']
ready = r.http('http://localhost/ready')
components = ready['body']['components']
assert ready['body']['ready'] is True
for name in ['asr', 'vad']:
    assert components[name]['state'] == 'disabled' and components[name]['required'] is False
assert components['memory_runtime']['state'] == 'ready' and components['memory_runtime']['ready'] is True
assert components['checkpoint']['state'] == 'ready' and components['checkpoint']['ready'] is True
assert components['tts']['resolved']['provider'] == 'qwen3-tts-gguf-host'
assert components['tts']['resolved']['voice'] == 'tosaka-rin-cn'
config_probe = '''import json,sqlite3;from pathlib import Path
from animetta.config.manifest import load_effective_config
c=load_effective_config(profile='production')
p=Path('/app/memory_db/living_memory.sqlite');con=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
fts=[x[0] for x in con.execute("select name from sqlite_master where type='table' and lower(sql) like '%using fts5%'")];con.close()
print(json.dumps({'capabilities':c.runtime.capabilities.model_dump(),'enable_tools':c.runtime.enable_tools,'required_services':list(c.runtime.required_services),'memory_retrieval_mode':c.runtime.memory_retrieval_mode,'long_term_memory_mode':c.runtime.long_term_memory_mode,'actual_readonly_memory_path':str(p),'fts5_virtual_tables':fts,'database_open_mode':'ro'}))
'''
config_raw = r.command(['docker','exec','anima-animetta-1','python','-c',config_probe])
config = json.loads(config_raw.strip().splitlines()[-1])
assert all(v is False for v in config['capabilities'].values())
assert config['enable_tools'] is False and config['memory_retrieval_mode']=='fts'
assert config['long_term_memory_mode']=='off' and config['fts5_virtual_tables']
identity = r.ownership()
image = r.command(['docker', 'inspect', '--format', '{{.Image}}', 'anima-animetta-1']).strip()
assert image == core['samples']['application_cold'][0]['container']['image']
surfaces = {ep: r.http('http://localhost' + ep) for ep in ['/dashboard', '/live.html']}
resources = []
for value in surfaces.values():
    for asset in value['assets']:
        response = r.http('http://localhost' + asset)
        resources.append({'url': 'http://localhost' + asset, 'sha256': response['sha256'], 'bytes': response['bytes'], 'status': response['status']})
boundary = {'recorded_at': datetime.now(UTC).isoformat(), 'status': 'passed', 'image_id': image, 'image_tag': r.CANDIDATE['image'],
            'container_id': r.command(['docker', 'inspect', '--format', '{{.Id}}', 'anima-animetta-1']).strip(),
            'installed_distribution_and_module_probe': packages, 'actual_core_config_and_fts5': config, 'ready': ready, 'same_public_surfaces': surfaces, 'actual_resource_fingerprints': resources,
            'host_ownership': identity, 'memory_v2_runtime_ready': True, 'long_term_memory_mode': 'off (frozen production unchanged)',
            'user_database_or_data_manually_written': False, 'rvc_lifecycle_steps_across_samples': [], 'rvc_8769_unavailable': True}
r.write(r.MEASURE / 'core-boundary.json', boundary)
core['boundary_acceptance'] = boundary
core['resume']['next_action'] = 'Run one supported role/live probe with native natural playback and two same-session continuity turns.'
r.write(r.REPORT / 'runtime-core-r4.json', core)
print(json.dumps({'boundary': 'passed', 'image': image, 'absent_distributions': list(packages['distribution_versions']), 'asr_vad': 'disabled/required=false', 'memory_v2': 'ready', 'rvc': 'unavailable', 'next': 'real role/live probe'}))

containers=json.loads(r.command(['docker','inspect','anima-animetta-1','anima-redis-1']))
labels=[];mounts=[]
for container in containers:
    ls=container['Config']['Labels']
    assert ls['com.docker.compose.project']=='anima'
    assert Path(ls['com.docker.compose.project.working_dir']).resolve()==r.ROOT.resolve()
    assert Path(ls['com.docker.compose.project.config_files']).resolve()==r.ROOT/'docker-compose.yml'
    assert all(m['Type']=='volume' for m in container['Mounts'])
    labels.append({'name':container['Name'],'working_dir':ls['com.docker.compose.project.working_dir'],'config_files':ls['com.docker.compose.project.config_files']})
    mounts.extend({'name':m['Name'],'destination':m['Destination']} for m in container['Mounts'])
assert {m['name'] for m in mounts}=={'anima_animetta-data','anima_animetta-memory-db','anima_animetta-redis'}
assert r.command(['docker','image','inspect','--format','{{.Id}}',r.CANDIDATE['old_r3_tag']]).strip()==r.CANDIDATE['old_r3_image']
boundary['stable_ROOT_labels']=labels;boundary['preserved_named_volumes']=mounts;boundary['old_r3_image_preserved']=True
r.write(r.MEASURE/'core-boundary.json',boundary);core['boundary_acceptance']=boundary;r.write(r.RECORD,core)
