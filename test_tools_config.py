"""
测试工具配置加载
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_load_tools_config():
    """测试 _load_tools_config 方法"""
    print("=" * 60)
    print("测试 _load_tools_config()")
    print("=" * 60)

    # 模拟 SessionManager 的 _load_tools_config 方法
    async def _load_tools_config() -> dict:
        """加载工具配置"""
        try:
            import yaml
            config_path = Path(__file__).parent / "config" / "tools.yaml"

            print(f"配置文件路径: {config_path}")
            print(f"文件是否存在: {config_path.exists()}")

            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    tools_config = yaml.safe_load(f)

                    # 详细调试日志
                    print(f"原始 YAML 解析结果类型: {type(tools_config)}")
                    print(f"YAML 顶级键: {list(tools_config.keys()) if isinstance(tools_config, dict) else 'NOT A DICT'}")

                    # 检查是否显式启用工具
                    tool_settings = tools_config.get("tool_settings", {})
                    print(f"tool_settings 内容: {tool_settings}")
                    print(f"tool_settings 类型: {type(tool_settings)}")

                    enable_tools = tool_settings.get("enable_tools", False)
                    print(f"enable_tools 原始值: {enable_tools}")
                    print(f"enable_tools 类型: {type(enable_tools)}")

                    print(f"工具调用 {'已启用' if enable_tools else '未启用'}")

                    result = {
                        "enable_tools": enable_tools,
                        "config": tools_config,
                    }
                    print(f"返回结果 enable_tools: {result['enable_tools']}")
                    return result
            else:
                print(f"工具配置文件不存在: {config_path}")
                return {"enable_tools": False, "config": {}}

        except Exception as e:
            print(f"加载工具配置失败: {e}")
            import traceback
            traceback.print_exc()
            return {"enable_tools": False, "config": {}}

    result = await _load_tools_config()

    print("\n" + "=" * 60)
    print("测试结果:")
    print("=" * 60)
    print(f"enable_tools = {result.get('enable_tools')}")
    print(f"类型 = {type(result.get('enable_tools'))}")
    print(f"是否为 True: {result.get('enable_tools') is True}")
    print(f"布尔值检验: {bool(result.get('enable_tools'))}")

    # 验证期望结果
    expected = True
    actual = result.get('enable_tools')

    if actual == expected:
        print(f"\n✓ 测试通过: enable_tools = {actual} (期望: {expected})")
        return True
    else:
        print(f"\n✗ 测试失败: enable_tools = {actual} (期望: {expected})")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_load_tools_config())
    sys.exit(0 if success else 1)
