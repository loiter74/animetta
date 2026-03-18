# 快速开始

5 分钟运行 Anima 项目。

---

## 环境要求

- Python 3.8+
- Node.js 18+
- pnpm 8+ (推荐) 或 npm

---

## 启动项目

```bash
# 使用启动脚本（推荐）
python scripts/start.py

# 或手动启动
pip install -r requirements.txt  # 安装后端依赖
python -m anima.socketio_server  # 启动后端（端口 12394）
```

---

## 配置 API Key

创建 `.env` 文件：

```bash
GLM_API_KEY=your_glm_api_key_here
```

---

## 切换服务商

编辑 `config/config.yaml`：

```yaml
services:
  agent: glm      # LLM: openai, glm, ollama, mock
  asr: faster_whisper  # ASR: openai, glm, faster_whisper, mock
  tts: edge        # TTS: openai, glm, edge, mock
  vad: silero      # VAD: silero
```

---

## 下载 Live2D 模型

```bash
python scripts/download_live2d_model.py
```

手动下载：解压到 `frontend/public/live2d/` 目录

---

## 常见问题

| 问题 | 解决方案 |
|------|----------|
| 端口被占用 | 修改 `config/config.yaml` 中的 `system.port` |
| API Key 无效 | 检查 `.env` 文件是否存在 |
| Live2D 不显示 | 检查模型文件是否正确下载 |

---

## 停止服务

```bash
python scripts/stop.py
```
