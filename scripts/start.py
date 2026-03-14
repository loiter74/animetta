#!/usr/bin/env python3
"""
Anima 统一启动脚本
Usage: python scripts/start.py [options]
"""

import os
import sys
import time
import platform
import subprocess
import argparse
import signal
from pathlib import Path


# ===========================
# Colors and Output
# ===========================

class Colors:
    """ANSI color codes"""
    CYAN = '\033[0;36m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    RED = '\033[0;31m'
    MAGENTA = '\033[0;35m'
    GRAY = '\033[0;90m'
    NC = '\033[0m'  # No Color

    @staticmethod
    def enabled():
        """Check if colors are supported"""
        return platform.system() != "Windows" or os.getenv('TERM')


def info(msg):
    print(f"{Colors.CYAN}[INFO]{Colors.NC} {msg}" if Colors.enabled() else f"[INFO] {msg}")


def success(msg):
    print(f"{Colors.GREEN}[OK]{Colors.NC} {msg}" if Colors.enabled() else f"[OK] {msg}")


def warn(msg):
    print(f"{Colors.YELLOW}[WARN]{Colors.NC} {msg}" if Colors.enabled() else f"[WARN] {msg}")


def error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}" if Colors.enabled() else f"[ERROR] {msg}")
    sys.exit(1)


# ===========================
# Process Management
# ===========================

class ProcessManager:
    """跨平台进程管理"""

    def __init__(self):
        self.is_windows = platform.system() == "Windows"
        self.processes = []
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """设置信号处理器，确保 Ctrl+C 能停止所有子进程"""
        def handler(signum, frame):
            print("\n")
            self.stop_all()
            sys.exit(0)

        signal.signal(signal.SIGINT, handler)
        if self.is_windows and hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, handler)

    def find_processes_on_port(self, port):
        """查找占用端口的进程 ID"""
        pids = []

        if self.is_windows:
            # Windows: 使用 Get-NetTCPConnection
            try:
                ps_script = f"""
                Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue |
                    Where-Object {{ $_.State -eq "Listen" }} |
                    Select-Object -ExpandProperty OwningProcess
                """
                result = subprocess.run(
                    ['powershell', '-Command', ps_script],
                    capture_output=True,
                    text=True,
                    check=True
                )
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line and line.isdigit():
                        pid = int(line)
                        if pid not in pids:
                            pids.append(pid)
            except (subprocess.CalledProcessError, FileNotFoundError):
                # 回退到 netstat
                try:
                    result = subprocess.run(
                        ['netstat', '-ano'],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    for line in result.stdout.split('\n'):
                        if f':{port}' in line and 'LISTENING' in line:
                            parts = line.split()
                            if len(parts) >= 5:
                                pid = int(parts[-1])
                                if pid not in pids:
                                    pids.append(pid)
                except subprocess.CalledProcessError:
                    pass
        else:
            # Unix: 使用 lsof
            try:
                result = subprocess.run(
                    ['lsof', '-ti', f':{port}'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                pids = [int(pid.strip()) for pid in result.stdout.split('\n') if pid.strip()]
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

        return pids

    def stop_process(self, pid, service_name):
        """停止指定 PID 的进程"""
        if not pid:
            return True

        try:
            if self.is_windows:
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], check=True, capture_output=True)
            else:
                subprocess.run(['kill', '-9', str(pid)], check=True, capture_output=True)
            success(f"停止 {service_name} (PID: {pid})")
            return True
        except subprocess.CalledProcessError as e:
            warn(f"无法停止进程 {pid}: {e}")
            return False

    def stop_processes_on_port(self, port, service_name):
        """停止占用指定端口的所有进程"""
        pids = self.find_processes_on_port(port)

        if not pids:
            return True

        info(f"发现 {service_name} 占用端口 {port}: PID {pids}")
        for pid in pids:
            self.stop_process(pid, service_name)
            time.sleep(0.5)

        # 验证
        time.sleep(1)
        remaining = self.find_processes_on_port(port)
        if remaining:
            warn(f"端口 {port} 仍被占用: {remaining}")
            return False

        return True

    def start_backend(self, project_root):
        """启动后端 Socket.IO 服务"""
        info("启动后端 Socket.IO 服务 (端口 12394)...")

        src_path = project_root / "src"
        env = os.environ.copy()
        env['PYTHONPATH'] = str(src_path)

        cmd = [sys.executable, '-m', 'anima.socketio_server']

        try:
            # 不使用 CREATE_NEW_PROCESS_GROUP，让子进程继承信号处理
            process = subprocess.Popen(
                cmd,
                cwd=project_root,
                env=env,
                stdout=None,  # 不重定向，让输出显示在终端
                stderr=None,
            )
            self.processes.append(("后端", process, 12394))
            return process
        except Exception as e:
            error(f"启动后端失败: {e}")

    def start_web_config(self, project_root, port=8080):
        """启动 Web 配置界面"""
        info(f"启动 Web 配置界面 (端口 {port})...")

        # 使用正斜杠避免 Windows 路径转义问题
        web_dir = project_root / "frontend" / "web"
        web_dir_str = str(web_dir).replace('\\', '/')

        cmd = [sys.executable, '-c', f'''
import sys
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler

class ConfigHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=r"{web_dir_str}", **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def do_GET(self):
        if self.path == "/" or self.path == "":
            self.path = "/templates/config.html"
        super().do_GET()

    def log_message(self, *args):
        pass

server = HTTPServer(("0.0.0.0", {port}), ConfigHandler)
print(f"[Config] Web 配置界面已启动: http://localhost:{port}")
server.serve_forever()
''']

        try:
            process = subprocess.Popen(
                cmd,
                stdout=None,
                stderr=None,
            )
            self.processes.append(("Web配置", process, port))
            return process
        except Exception as e:
            error(f"启动 Web 配置失败: {e}")

    def start_desktop_app(self, project_root, dev_mode=False):
        """启动 Electron 桌面应用"""
        info("启动 Electron 桌面应用...")

        frontend_dir = project_root / "frontend"

        # 检查依赖
        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            warn("检测到前端依赖未安装，正在安装...")
            subprocess.run(
                ["npm", "install"],
                cwd=frontend_dir,
                shell=True,
                check=True
            )

        cmd = ["npm", "run", "dev"]
        if dev_mode:
            cmd = ["npm", "run", "dev", "--", "--dev"]

        try:
            process = subprocess.Popen(
                cmd,
                cwd=frontend_dir,
                shell=True,
                stdout=None,
                stderr=None,
            )
            self.processes.append(("桌面应用", process, None))
            return process
        except Exception as e:
            error(f"启动桌面应用失败: {e}")

    def start_frontend_dev(self, project_root, pkg_manager):
        """启动 Next.js 开发服务器"""
        info("启动 Next.js 开发服务器 (端口 3000)...")

        frontend_dir = project_root / "frontend"
        env = os.environ.copy()
        env['NEXT_PRIVATE_BENCHMARK_ENABLED'] = 'false'
        env['NODE_OPTIONS'] = '--no-warnings'

        cmd = [pkg_manager, 'dev']

        try:
            process = subprocess.Popen(
                cmd,
                cwd=frontend_dir,
                env=env,
                stdout=None,
                stderr=None,
            )
            self.processes.append(("前端", process, 3000))
            return process
        except Exception as e:
            error(f"启动前端失败: {e}")

    def wait_for_services(self):
        """等待所有服务启动"""
        if not self.processes:
            return

        info("等待服务启动...")
        time.sleep(2)

        for name, process, port in self.processes:
            if port:
                for _ in range(15):
                    if self.find_processes_on_port(port):
                        success(f"{name} 已就绪 (端口 {port})")
                        break
                    time.sleep(0.5)
                else:
                    warn(f"{name} 可能未正常启动")

    def stop_all(self):
        """停止所有启动的服务"""
        if not self.processes:
            return

        info("\n正在停止所有服务...")

        for name, process, port in self.processes:
            try:
                if self.is_windows:
                    # Windows: 使用 taskkill 强制终止进程树
                    subprocess.run(
                        ['taskkill', '/F', '/T', '/PID', str(process.pid)],
                        capture_output=True,
                        timeout=5
                    )
                else:
                    process.terminate()
                    process.wait(timeout=3)
            except:
                try:
                    process.kill()
                except:
                    pass

        # 额外清理：确保端口被释放
        for name, process, port in self.processes:
            if port:
                self.stop_processes_on_port(port, name)

        self.processes.clear()
        success("所有服务已停止")


# ===========================
# Main
# ===========================

def main():
    parser = argparse.ArgumentParser(
        description='Anima 统一启动脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/start.py              # 启动默认服务 (后端 + Web配置 + 桌面应用)
  python scripts/start.py --mode web   # 启动 Web 模式 (后端 + Next.js)
  python scripts/start.py --backend-only  # 仅启动后端
        """
    )

    parser.add_argument(
        '--mode',
        choices=['desktop', 'web'],
        default='desktop',
        help='运行模式: desktop (Electron桌面应用) 或 web (Next.js)'
    )
    parser.add_argument('--backend-only', action='store_true', help='仅启动后端')
    parser.add_argument('--no-backend', action='store_true', help='不启动后端')
    parser.add_argument('--no-web-config', action='store_true', help='不启动 Web 配置界面')
    parser.add_argument('--no-app', action='store_true', help='不启动桌面/前端应用')
    parser.add_argument('--web-port', type=int, default=8080, help='Web 配置界面端口')
    parser.add_argument('--install', action='store_true', help='安装依赖')
    parser.add_argument('--dev', action='store_true', help='开启开发者工具 (DevTools)')

    args = parser.parse_args()

    # 打印标题
    print()
    if Colors.enabled():
        print(f"{Colors.MAGENTA}{'=' * 50}{Colors.NC}")
        print(f"{Colors.MAGENTA}  Anima 启动脚本{Colors.NC}")
        print(f"{Colors.MAGENTA}{'=' * 50}{Colors.NC}")
    else:
        print('=' * 50)
        print('  Anima 启动脚本')
        print('=' * 50)
    print()

    # 获取项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)

    # 检查包管理器
    pkg_manager = None
    use_shell = platform.system() == "Windows"
    for pm in ['pnpm', 'npm']:
        try:
            subprocess.run([pm, '--version'], capture_output=True, check=True, shell=use_shell)
            pkg_manager = pm
            break
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue

    if pkg_manager:
        info(f"包管理器: {pkg_manager}")

    # 安装依赖
    if args.install:
        info("安装 Python 依赖...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)

        if pkg_manager:
            info("安装前端依赖...")
            subprocess.run([pkg_manager, 'install'], check=True, cwd='frontend', shell=use_shell)
        print()

    # 进程管理器
    pm = ProcessManager()

    # 停止现有服务
    info("检查并停止现有服务...")
    pm.stop_processes_on_port(12394, "后端")
    pm.stop_processes_on_port(8080, "Web配置")
    pm.stop_processes_on_port(3000, "前端")
    print()

    try:
        # 启动后端
        if not args.no_backend and not args.backend_only:
            pm.start_backend(project_root)
            time.sleep(2)

        # 启动 Web 配置
        if not args.no_web_config and not args.backend_only:
            pm.start_web_config(project_root, args.web_port)
            time.sleep(1)

        # 启动应用
        if not args.no_app and not args.backend_only:
            if args.mode == 'desktop':
                pm.start_desktop_app(project_root, dev_mode=args.dev)
            else:
                if not pkg_manager:
                    error("Web 模式需要 pnpm/npm")
                pm.start_frontend_dev(project_root, pkg_manager)

        # 等待服务就绪
        print()
        pm.wait_for_services()

        # 打印状态
        print()
        if Colors.enabled():
            print(f"{Colors.GREEN}{'=' * 50}{Colors.NC}")
            print(f"{Colors.GREEN}  启动完成！{Colors.NC}")
            print(f"{Colors.GREEN}{'=' * 50}{Colors.NC}")
        else:
            print('=' * 50)
            print('  启动完成！')
            print('=' * 50)
        print()

        if not args.no_backend:
            if Colors.enabled():
                print(f"  后端:      {Colors.CYAN}http://localhost:12394{Colors.NC}")
            else:
                print("  后端:      http://localhost:12394")

        if not args.no_web_config and not args.backend_only:
            if Colors.enabled():
                print(f"  Web 配置:  {Colors.CYAN}http://localhost:{args.web_port}{Colors.NC}")
            else:
                print(f"  Web 配置:  http://localhost:{args.web_port}")

        if not args.no_app and not args.backend_only:
            if args.mode == 'desktop':
                print("  桌面应用:  Electron 窗口")
            else:
                if Colors.enabled():
                    print(f"  前端:     {Colors.CYAN}http://localhost:3000{Colors.NC}")
                else:
                    print("  前端:     http://localhost:3000")

        print()
        info("按 Ctrl+C 停止所有服务\n")

        # 等待进程
        for name, process, _ in pm.processes:
            process.wait()

    except KeyboardInterrupt:
        pm.stop_all()


if __name__ == "__main__":
    main()
