import json
import shutil
from pathlib import Path

repo = Path.cwd()
target = repo / ".zcode/performance/deployment-core-20261011/node-core-install/source"
assert not target.exists(), "Reuse existing probe state explicitly; never overwrite a prior run"
frontend = target / "frontend"
frontend.mkdir(parents=True)
for folder in ("src", "public", "scripts", "optional"):
    shutil.copytree(repo / "frontend" / folder, frontend / folder,
        ignore=shutil.ignore_patterns("node_modules", "dist", "__pycache__"))
for path in (repo / "frontend").iterdir():
    if path.is_file() and (path.suffix in {".html", ".json", ".ts", ".yaml"}):
        shutil.copy2(path, frontend / path.name)
(target / "config").mkdir()
shutil.copy2(repo / "config/socket-events.json", target / "config/socket-events.json")
print(json.dumps({"source": str(frontend), "copied_env": False, "copied_node_modules": False}))
