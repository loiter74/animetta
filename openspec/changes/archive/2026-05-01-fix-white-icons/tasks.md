## 1. 编写图片处理脚本

- [x] 1.1 编写 Python 脚本 `scripts/process_icons.py`
  - 实现：读取 JPEG/PNG → chroma key 去白底 → 添加 Alpha → 缩放到 64x64 → 输出 PNG
  - 支持批量处理整个目录
  - 支持白底阈值参数（默认 240/255）

## 2. 处理服务图标

- [x] 2.1 运行脚本处理 `frontend/public/icons/` 下所有子目录（asr, background, chat, controls, interrupt, live2d, llm, memory, persona, tts, vad）
- [x] 2.2 验证每个图标透明背景正确、大小合适（全部 RGBA 64x64）

## 3. 检查并修复其他素材

- [x] 3.1 修复 `public/avatar/avatar.png`：从源文件重新复制 + 去白底 + RGBA，保留 1024x1024
- [x] 3.2 修复 `public/loading/loading.png`：从源文件重新复制 + 去白底 + RGBA，保留 1792x1008
- [x] 3.3 修复 `public/error/error.png`：从源文件重新复制 + 去白底 + RGBA，保留 1792x1008
- [x] 3.4 修复 `public/favicon.png`：从 logo 源重新复制 + 去白底 + RGBA，缩放 64x64
- [x] 3.5 检查 `public/backgrounds/`：全部正常（深色中心，无白底问题），无需修改

## 4. 启动前端验证

- [x] 4.1 启动 Vite dev server（已清理旧进程，等待用户重启）
- [ ] 4.2 打开浏览器检查所有图标在暗色主题上显示清晰（白色图标 + 透明度渐变）
- [ ] 4.3 检查边缘过渡自然、无白晕
