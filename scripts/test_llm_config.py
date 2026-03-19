#!/usr/bin/env python3
"""
LLM 配置测试脚本
验证 GLM API Key 是否正确加载和 LLM 是否能正确初始化
"""

import os
import sys
from pathlib import Path

# 添加 src 到 Python 路径
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    env_path = current_dir.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)
        print(f"[OK] 已加载 .env 文件: {env_path}")
    else:
        print(f"[WARN] .env 文件不存在: {env_path}")
except ImportError:
    print("[WARN] python-dotenv 未安装")

# 检查环境变量
glm_key = os.getenv("GLM_API_KEY")
if glm_key:
    print(f"[OK] GLM_API_KEY 已设置: {glm_key[:20]}... (长度: {len(glm_key)})")
else:
    print("[ERROR] GLM_API_KEY 未设置！")
    sys.exit(1)

# 导入项目模块
from anima.config import AppConfig
from anima.services.llm import LLMFactory

# 加载配置
print("\n[TEST] 加载配置文件...")
config = AppConfig.load()
print(f"[OK] 配置加载完成")
print(f"[INFO] Agent LLM 类型: {config.agent.llm_config.type}")
print(f"[INFO] Agent LLM 模型: {config.agent.llm_config.model}")

# 检查 API Key 是否正确展开
if hasattr(config.agent.llm_config, 'api_key'):
    api_key = config.agent.llm_config.api_key
    if api_key and api_key.startswith("${"):
        print(f"[ERROR] API Key 未展开！当前值: {api_key}")
        sys.exit(1)
    elif api_key:
        print(f"[OK] API Key 已展开: {api_key[:20]}... (长度: {len(api_key)})")
    else:
        print("[ERROR] API Key 为空！")
        sys.exit(1)

# 测试 LLM 创建
print("\n[TEST] 尝试创建 LLM 服务...")
try:
    system_prompt = "You are a helpful assistant."
    llm = LLMFactory.create_from_config(
        config=config.agent.llm_config,
        system_prompt=system_prompt
    )
    print(f"[OK] LLM 创建成功: {type(llm).__name__}")

    # 验证不是 MockLLM
    if type(llm).__name__ == "MockLLM":
        print("[ERROR] LLM 降级到了 MockLLM！请检查错误日志")
        sys.exit(1)
    elif type(llm).__name__ == "GLMLLM":
        print("[SUCCESS] GLM LLM 创建成功！")
    else:
        print(f"[WARN] LLM 类型不是 GLMLLM: {type(llm).__name__}")

except Exception as e:
    print(f"[ERROR] LLM 创建失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[SUCCESS] 所有测试通过！")
