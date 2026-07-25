#!/usr/bin/env python3
"""
AgentToGo Hardware - LLM API Local Proxy Service (Fixed Encoding)
自动将本地 127.0.0.1:<端口> 映射到已配置的 LLM API
支持命令行指定配置和一键安装为 Linux systemd 系统服务
"""

import os
import sys
import json
import argparse
import subprocess
import shutil
from pathlib import Path

# ============================================================
#  默认配置（可通过命令行参数覆盖）
# ============================================================
DEFAULT_CONFIG = {
    "api_key": "",
    "model": "gpt-3.5-turbo",
    "local_port": 8080,
    "target_url": "https://api.openai.com/v1/chat/completions",
    "service_name": "agenttogo-hardware",
    "description": "AgentToGo Hardware LLM API Proxy Service"
}

# ============================================================
#  系统路径定义
# ============================================================
INSTALL_DIR = Path("/opt") / DEFAULT_CONFIG["service_name"]
SCRIPT_PATH = INSTALL_DIR / f"{DEFAULT_CONFIG['service_name']}.py"
SERVICE_FILE = Path("/etc/systemd/system") / f"{DEFAULT_CONFIG['service_name']}.service"
PID_FILE = Path("/var/run") / f"{DEFAULT_CONFIG['service_name']}.pid"
LOG_FILE = Path("/var/log") / f"{DEFAULT_CONFIG['service_name']}.log"
CONFIG_FILE = INSTALL_DIR / "config.json"

# ============================================================
#  依赖检查与导入
# ============================================================
try:
    from flask import Flask, request, jsonify, Response
    import requests
except ImportError:
    print("正在安装依赖: flask requests ...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "flask", "requests"])
    from flask import Flask, request, jsonify, Response
    import requests

app = Flask(__name__)

# 全局配置（运行时填充）
current_config = DEFAULT_CONFIG.copy()

# ============================================================
#  配置管理
# ============================================================
def load_config():
    """加载配置：优先级 命令行 > 配置文件 > 默认值"""
    config = DEFAULT_CONFIG.copy()
    
    # 1. 从配置文件加载
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                saved = json.load(f)
                config.update(saved)
        except Exception as e:
            print(f"[!] 读取配置文件失败: {e}")
    
    # 2. 从环境变量加载
    env_mapping = {
        'AGENTTOGO_API_KEY': 'api_key',
        'AGENTTOGO_MODEL': 'model',
        'AGENTTOGO_PORT': 'local_port',
        'AGENTTOGO_TARGET_URL': 'target_url'
    }
    for env_var, config_key in env_mapping.items():
        if env_var in os.environ:
            value = os.environ[env_var]
            if config_key == 'local_port':
                value = int(value)
            config[config_key] = value
    
    return config

def save_config(config):
    """保存配置到文件"""
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"[✓] 配置已保存到: {CONFIG_FILE}")

# ============================================================
#  代理核心逻辑（已修复编码问题）
# ============================================================
def _decode_header_value(value):
    """安全地解码HTTP头值，处理非UTF-8字符"""
    if isinstance(value, bytes):
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError:
            # 使用 latin-1 作为 fallback，它永远不会失败
            # 这样可以保留原始字节信息
            return value.decode('latin-1', errors='replace')
    return str(value)

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def proxy(path):
    """将所有请求转发到目标 LLM API（已修复编码问题）"""
    try:
        target_url = f"{current_config['target_url'].rstrip('/')}/{path.lstrip('/')}"
        if not path:
            target_url = current_config['target_url']
        
        headers = dict(request.headers)
        headers.pop('Host', None)
        headers.pop('Content-Length', None)
        
        # 注入 API Key
        headers['Authorization'] = f"Bearer {current_config['api_key']}"
        
        data = request.get_data()
        
        # 自动替换模型字段
        if request.is_json and data:
            try:
                json_data = json.loads(data)
                if 'model' in json_data:
                    json_data['model'] = current_config['model']
                data = json.dumps(json_data)
                headers['Content-Type'] = 'application/json'
            except (json.JSONDecodeError, TypeError):
                pass
        
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=data,
            params=request.args,
            stream=True,
            timeout=60
        )
        
        # 正确处理响应头（修复编码问题）
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        resp_headers = []
        for name, value in resp.raw.headers.items():
            if name.lower() not in excluded_headers:
                # 关键修复：安全解码头值，避免UTF-8解码错误
                safe_value = _decode_header_value(value)
                resp_headers.append((name, safe_value))
        
        # 返回响应（确保二进制数据正确传输）
        return Response(
            resp.iter_content(chunk_size=1024),
            status=resp.status_code,
            headers=resp_headers
        )
        
    except requests.exceptions.Timeout:
        return jsonify({"error": "请求超时"}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "无法连接到目标 API"}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """健康检查端点"""
    return jsonify({
        "status": "ok",
        "service": DEFAULT_CONFIG["service_name"],
        "model": current_config["model"],
        "target": current_config["target_url"],
        "local_port": current_config["local_port"]
    })

# ============================================================
#  服务管理功能
# ============================================================
def create_service_file(config):
    """创建 systemd 服务文件"""
    python_path = sys.executable
    
    exec_start = f"{python_path} {SCRIPT_PATH} --run --config {CONFIG_FILE}"
    
    service_content = f"""[Unit]
Description={DEFAULT_CONFIG['description']}
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
WorkingDirectory={INSTALL_DIR}
ExecStart={exec_start}
Restart=always
RestartSec=5
Environment="PYTHONUNBUFFERED=1"
StandardOutput=append:{LOG_FILE}
StandardError=append:{LOG_FILE}

[Install]
WantedBy=multi-user.target
"""
    SERVICE_FILE.write_text(service_content)
    print(f"[✓] 服务文件已创建: {SERVICE_FILE}")

def install_service(config):
    """安装为 systemd 服务"""
    if os.geteuid() != 0:
        print("[!] 安装服务需要 root 权限，请使用 sudo 运行")
        sys.exit(1)
    
    print(f"[*] 正在安装 {DEFAULT_CONFIG['service_name']} 服务...")
    
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    
    current_script = Path(__file__).resolve()
    shutil.copy2(current_script, SCRIPT_PATH)
    SCRIPT_PATH.chmod(0o755)
    print(f"[✓] 脚本已复制到: {SCRIPT_PATH}")
    
    save_config(config)
    
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.touch(mode=0o644, exist_ok=True)
    
    create_service_file(config)
    
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", DEFAULT_CONFIG["service_name"]], check=True)
    subprocess.run(["systemctl", "start", DEFAULT_CONFIG["service_name"]], check=True)
    
    print(f"\n[✓] {DEFAULT_CONFIG['service_name']} 服务安装成功！")
    print(f"    本地代理地址: http://127.0.0.1:{config['local_port']}")
    print(f"    健康检查: curl http://127.0.0.1:{config['local_port']}/health")
    print(f"    查看日志: sudo tail -f {LOG_FILE}")
    print(f"    管理服务: sudo systemctl {DEFAULT_CONFIG['service_name']} [start|stop|restart|status]")

def uninstall_service():
    """卸载 systemd 服务"""
    if os.geteuid() != 0:
        print("[!] 卸载服务需要 root 权限，请使用 sudo 运行")
        sys.exit(1)
    
    print(f"[*] 正在卸载 {DEFAULT_CONFIG['service_name']} 服务...")
    
    subprocess.run(["systemctl", "stop", DEFAULT_CONFIG["service_name"]], check=False)
    subprocess.run(["systemctl", "disable", DEFAULT_CONFIG["service_name"]], check=False)
    
    if SERVICE_FILE.exists():
        SERVICE_FILE.unlink()
        print(f"[✓] 已删除服务文件: {SERVICE_FILE}")
    
    if INSTALL_DIR.exists():
        shutil.rmtree(INSTALL_DIR)
        print(f"[✓] 已删除安装目录: {INSTALL_DIR}")
    
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    
    print(f"\n[✓] {DEFAULT_CONFIG['service_name']} 服务已卸载")

def run_server(config):
    """运行代理服务器"""
    global current_config
    current_config = config
    
    print(f"[*] 启动 {DEFAULT_CONFIG['service_name']} 代理服务...")
    print(f"    监听地址: 127.0.0.1:{config['local_port']}")
    print(f"    目标 API:  {config['target_url']}")
    print(f"    使用模型:  {config['model']}")
    print(f"    按 Ctrl+C 停止服务\n")
    
    PID_FILE.write_text(str(os.getpid()))
    
    try:
        app.run(
            host="127.0.0.1",
            port=config["local_port"],
            threaded=True,
            use_reloader=False
        )
    except KeyboardInterrupt:
        print("\n[*] 服务已停止")
    finally:
        if PID_FILE.exists():
            PID_FILE.unlink()

def show_status():
    """查看服务状态"""
    if os.geteuid() != 0:
        print("[!] 查看服务状态需要 root 权限")
        return
    
    result = subprocess.run(
        ["systemctl", "status", DEFAULT_CONFIG["service_name"], "--no-pager"],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)

def update_service_config(new_config):
    """更新已安装服务的配置"""
    if os.geteuid() != 0:
        print("[!] 更新配置需要 root 权限")
        return False
    
    save_config(new_config)
    create_service_file(new_config)
    
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "restart", DEFAULT_CONFIG["service_name"]], check=True)
    
    print(f"[✓] 配置已更新，服务已重启")
    return True

# ============================================================
#  命令行入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="AgentToGo Hardware - LLM API 本地代理服务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 安装服务（需 sudo）
  sudo %(prog)s --install --api-key sk-xxx --model gpt-4 --port 8080
  
  # 直接运行
  %(prog)s --run --api-key sk-xxx --target-url https://api.openai.com/v1/chat/completions
  
  # 查看状态
  sudo %(prog)s --status
  
  # 卸载服务
  sudo %(prog)s --uninstall
  
  # 更新已安装服务的配置
  sudo %(prog)s --update --model gpt-4 --port 9090
        """
    )
    
    config_group = parser.add_argument_group("配置参数")
    config_group.add_argument("--api-key", help="LLM API Key")
    config_group.add_argument("--model", help="模型名称")
    config_group.add_argument("--port", type=int, help="本地监听端口")
    config_group.add_argument("--target-url", help="目标 LLM API 地址")
    
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--install", action="store_true", help="安装为系统服务")
    mode_group.add_argument("--uninstall", action="store_true", help="卸载系统服务")
    mode_group.add_argument("--run", action="store_true", help="运行代理服务器")
    mode_group.add_argument("--status", action="store_true", help="查看服务状态")
    mode_group.add_argument("--update", action="store_true", help="更新已安装服务的配置")
    
    args = parser.parse_args()
    
    config = load_config()
    
    if args.api_key:
        config['api_key'] = args.api_key
    if args.model:
        config['model'] = args.model
    if args.port:
        config['local_port'] = args.port
    if args.target_url:
        config['target_url'] = args.target_url
    
    if args.run or args.install or args.update:
        if not config['api_key']:
            print("[!] 错误: 必须指定 --api-key 或设置 AGENTTOGO_API_KEY 环境变量")
            sys.exit(1)
    
    if args.install:
        install_service(config)
    elif args.uninstall:
        uninstall_service()
    elif args.run:
        run_server(config)
    elif args.status:
        show_status()
    elif args.update:
        update_service_config(config)

if __name__ == "__main__":
    main()