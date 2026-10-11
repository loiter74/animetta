# RVC 宿主服务独立依赖恢复

原始运行记录中的绝对路径表示采集位置。临时目录清理后，可通过 [归档索引](../../docs/performance/deployment-core-2026-10-11/phase3-5-evidence/index.json) 的 `source`、`file` 与 SHA256 查找字节一致的日志、解析输入和安装记录。

`requirements.lock` 固定 Windows x64 / CPython 3.13.14 的 72 个运行分发包。转换所需闭包为 60 包，Demucs 分离所需闭包为 30 包，合并后为 72 包；没有复制原环境借用的 325 个用户 site 包。Torch 和 Torchaudio 保留 `2.11.0+cu128`，锁含 PyPI 与 PyTorch CUDA 12.8 索引的 1179 个制品 SHA256。

`dependency-provenance.json` 保存实际 Windows 解析、哈希校验安装、`pip check`、包位置隔离证据及原始日志哈希。独立安装 run `host-lock-rvc-install03` 已通过；72 个运行包与引导包 pip 26.1.2 全部来自新 venv，18 个转换/分离顶层模块的位置核对也通过，未执行这些模块。原全局环境的 FunASR、Kokoro、ZhipuAI 共 13 项依赖冲突不属于本服务闭包，未修复或带入新环境。

## 恢复与启动

永久服务环境为 `C:\Users\30262\RVC20240604Nvidia\.venv-animetta`，不能作为任务临时目录清理。转换和分离均使用其 `Scripts\python.exe`。首次恢复用 `py -3.13 -m venv <新环境目录>` 创建独立 venv，确认 `pyvenv.cfg` 的 `include-system-site-packages = false`，然后执行：

```powershell
uv pip sync services/rvc-host/requirements.lock --python <新环境的Scripts/python.exe> --require-hashes --strict --no-config --default-index https://pypi.org/simple --index https://download.pytorch.org/whl/cu128 --index-strategy unsafe-best-match
<新环境的Scripts/python.exe> -m pip check
```

所有这些子进程与正式启动使用相同隔离条件：`PYTHONNOUSERSITE=1`；移除继承的 `PYTHONHOME`、`PYTHONUSERBASE`；`PYTHONPATH` 只包含项目 `src` 与 RVC 外部运行仓库根。不能借用调用方的 Python 路径。新 venv 的引导包 pip 单独记于 provenance，不计入 72 包运行闭包。

安装验证成功后，`config/host-rvc.yaml` 中 `runtime.python` 和 `separation.python` 指向同一永久环境。启停只通过 `py -3.13 scripts/runtime_lifecycle.py host-rvc-up` 与 `host-rvc-stop`；安装、解析和元数据检查本身不启动服务。

原转换解释器 `C:\Users\30262\RVC20240604Nvidia\runtime\Scripts\python.exe` 与分离解释器 `C:\Users\30262\miniconda3\python.exe` 均保留，原合同记录在 provenance 的 `contract_before` 中。它们是回退来源，但原环境依赖用户 site，不能在干净启动条件下未经验证自动回退。

## 模型、声线与验证边界

声线仍为 `tosaka-rin-cn`，转换模型、索引、HuBERT、RMVPE 的路径和 SHA256，以及 Demucs `htdemucs`、CUDA 设备和精度均保持原合同值。模型、FFmpeg 可执行文件和系统驱动不属于 Python 包锁；没有迁移或下载这些资产。

闭包来自选定 CUDA 路径的源码导入根与分发依赖元数据。Fairseq 由已有 HuBERT shim 提供，未使用的 Intel、DirectML 和 JIT 路径不纳入闭包。实际 `platform_machine` 是 `AMD64`；交叉指定 `x86_64` 会激活 Hugging Face Hub 的另一 marker 分支并额外引入 hf-xet，不能将该结果冒充原环境闭包。

`antlr4-python3-runtime`、`demucs`、`dora-search`、`julius` 的哈希固定下载的源码包，并由 uv 构建纯 Python wheel。本锁固定运行依赖，未声明构建后的 wheel 字节可复现。包安装、`pip check` 和不执行模块的路径检查不替代原生 ABI、模型加载、分离、转换或 GPU 验收；本次锁验证没有导入模型或调用 GPU。
