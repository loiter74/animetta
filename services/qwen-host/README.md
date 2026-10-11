# Qwen 宿主服务依赖恢复

`requirements.lock` 固定当前 Windows x64 / CPython 3.13.14 环境的全部 35 个分发包，保留版本 local 后缀，包含 uv 从 PyPI 取得的 459 个制品 SHA256。独立验证环境已通过 `uv pip sync --require-hashes --strict` 和 `pip check`；所有分发包均来自该环境，未启用用户 site。当前工作的 Qwen 环境、进程、模型和声线保持原样。

`native-provenance.json` 保存解析和安装命令、各阶段原始日志 SHA256、依赖元数据、原生运行时及声线身份。原生仓库固定于 `0eb32e283ee46b86820c67843abb04cf12bc58d7`；既有 `llama-b9333-bin-win-vulkan-x64.zip` 的 SHA256 为 `0971a54893feafcc043b18d839dba9a42cb1038a5005030c18990e35fdc209d4`，30 个已部署 DLL 与对应 ZIP 成员逐项相同。声线仍为 `tosaka-rin-cn`。

## 在独立目录恢复

使用 Windows 的 `py -3.13` 创建新的 venv，再将 `uv pip sync services/qwen-host/requirements.lock --python <新venv的Scripts/python.exe> --require-hashes --strict --default-index https://pypi.org/simple --no-config` 的安装目标明确指定为这个新目录。随后用该解释器执行 `-m pip check`。

这些子进程须设置 `PYTHONNOUSERSITE=1`，移除继承的 `PYTHONHOME` 和 `PYTHONUSERBASE`，并将 `PYTHONPATH` 精确设为项目 `src` 与 Qwen 原生运行仓库根。不继承调用方的其他 Python 路径。服务启动由 `py -3.13 scripts/runtime_lifecycle.py host-tts-up` 管理；恢复环境本身不启动服务。

模型目录、参考音频及其哈希继续由 `config/host-tts.yaml` 管理。恢复原生运行时必须核对上述 commit、ZIP 和 DLL 哈希，以及该合同中的模型、量化、参考音频和声线身份。

## 验证边界

本次独立安装目标为任务目录中的 `qwen-lock-validation-venv`，只用于验证依赖恢复。没有将锁同步到当前工作的宿主 venv，也没有重启、导入模型或执行 GPU 推理。包安装通过不替代后续正式生命周期、合成和真实播放验收。清理任务验证环境前保留 provenance 引用的小型原始证据。
