# AgentToGo 部署指南

## 在 OrangePi 3B 上部署

### 1. 准备环境

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Python 和 pip
sudo apt install python3 python3-pip python3-venv -y

# 克隆项目
git clone <your-repo-url> AgentToGo
cd AgentToGo
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# LLM API 配置（兼容 OpenAI 格式的 API）
LLM_API_BASE=http://your-llm-server:11434/v1
LLM_API_KEY=your-api-key
LLM_MODEL=qwen2.5

# 服务器配置
HOST=0.0.0.0
PORT=8000
```

### 3. 启动服务

```bash
chmod +x start.sh
./start.sh
```

### 4. 访问 Web 界面

在浏览器中访问：`http://your-orangepi-ip:8000`

### 5. 设置开机自启（可选）

创建 systemd 服务：

```bash
sudo nano /etc/systemd/system/agenttogo.service
```

内容：

```ini
[Unit]
Description=AgentToGo Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/AgentToGo
ExecStart=/home/pi/AgentToGo/venv/bin/python server/main.py
Restart=always
RestartSec=5
Environment=LLM_API_BASE=http://your-llm-server:11434/v1
Environment=LLM_API_KEY=your-api-key
Environment=LLM_MODEL=qwen2.5

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable agenttogo
sudo systemctl start agenttogo
```

## 功能说明

### 聊天功能
- 创建多个独立会话
- 每个会话有独立上下文
- 会话间共享记忆

### 循环任务
- 用自然语言描述任务，AI 自动生成 Python 监测脚本
- 脚本按设定间隔执行
- 只有条件满足时才会唤醒 LLM
- 支持三种响应：忽略继续、通知并继续、通知并停止

### 记忆管理
- 存储键值对形式的记忆
- 支持分类管理
- 聊天和任务执行时可使用记忆

### 通知系统
- 任务触发时发送通知
- 未读通知计数
- 打开网页时集中显示
