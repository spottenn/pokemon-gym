# Pokemon Demo Agents

这个项目包含了几个用于与Pokemon Evaluator Server通信的演示Agent。这些Agent可以通过RESTful API与服务器交互，控制Pokemon游戏。

## 环境要求

- Python 3.6+
- requests
- PIL (Pillow)

## 安装

确保已经安装了必要的依赖：

```bash
pip install requests pillow
```

## 使用方法

### 1. 启动评估服务器

首先，确保Pokemon Evaluator Server已经启动：

```bash
python server.py --rom pokemon.gb --host 0.0.0.0 --port 8000
```

### 2. 运行简单的Demo Agent

简单的Demo Agent会随机执行动作，没有特定的游戏策略：

```bash
python demo_agent.py --server http://localhost:8000 --steps 100
```

参数说明：
- `--server`: 服务器的URL (默认: http://localhost:8000)
- `--steps`: 运行的步数 (默认: 100)
- `--headless`: 无界面运行 (可选)
- `--sound`: 启用声音 (可选，需要非无界面模式)
- `--save-screenshots`: 保存游戏截图 (可选)
- `--screenshot-interval`: 截图间隔步数 (默认: 10)

### 3. 运行智能Demo Agent

智能Demo Agent具有基本的游戏策略，会按照预定义的路径移动，处理对话，以及检测卡住的情况：

```bash
python smart_demo_agent.py --server http://localhost:8000 --steps 200
```

参数说明与简单的Demo Agent相同。

## Agent功能

### Demo Agent

简单的演示Agent，具有以下功能：

- 初始化游戏环境
- 随机执行动作（按键和等待）
- 记录和显示游戏状态

### Smart Demo Agent

智能演示Agent，在Demo Agent的基础上增加了以下功能：

- 按照预定义的路径移动
- 检测并处理对话
- 检测卡住的情况并尝试恢复
- 探索地图
- 移动到特定坐标
- 更智能的行动决策

## 例子

以下是一个使用Smart Demo Agent的简单例子：

```python
from smart_demo_agent import SmartDemoAgent

# 创建Agent
agent = SmartDemoAgent(server_url="http://localhost:8000")

# 初始化环境
state = agent.initialize(headless=False, sound=True)

# 运行50步
agent.run(max_steps=50)

# 停止环境
agent.stop()
```

## 自定义Agent

你可以基于这些Demo Agent创建自己的Agent，添加更复杂的游戏策略。以下是一些可能的扩展：

1. 添加战斗策略
2. 实现更复杂的导航和寻路算法
3. 增加任务系统，如收集徽章、捕捉特定的Pokemon等
4. 增强对话处理能力，理解游戏情节并做出相应决策
5. 使用机器学习来优化行动策略

## 注意事项

- Agent的性能很大程度上取决于服务器的响应速度，尤其是在处理复杂动作时。
- 为了避免过度请求服务器，建议添加适当的延迟。
- 在实际运行中，可能需要处理网络异常、服务器重启等情况。
- 游戏状态解析可能不完美，有时需要手动干预。

## 贡献

欢迎提交改进建议和Bug报告！

## 许可

[MIT License](LICENSE) 