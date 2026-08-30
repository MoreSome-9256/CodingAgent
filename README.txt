一、Git 仓库地址
https://github.com/MoreSome-9256/CodingAgent

二、如何运行
1. 环境配置：
   - 依赖 Python 3.10+。
   - 安装依赖：pip install openai fastapi uvicorn pydantic python-dotenv
   - 配置凭据：在项目根目录下创建 .env 文件并填入：
     OPENAI_API_KEY=your_api_key
     OPENAI_BASE_URL=https://api.deepseek.com/v1
     MODEL_NAME=deepseek-chat
2. 启动方式：
   - 方式 A (Web Studio 交互控制台)：
     运行 python server.py，在浏览器访问 http://127.0.0.1:8000
   - 方式 B (轻量 CLI 终端模式)：
     运行 python main.py，即可直接在终端命令行交互。

三、特色功能说明
1. 零 SDK 纯原生架构与异步并发调度：
   不依赖任何第三方 Agent 框架或服务端代码沙箱，完全自主手写基于原生 Tool Calling 的 ReAct 决策循环。底层对工具执行设计了“并发只读 + 屏障串行写”调度机制（基于 asyncio 线程池），兼顾执行速度与文件系统状态一致性。
2. 三层 (L1-L3) 渐进式上下文防护体系：
   - L1/L2 视图压缩：在生成器内存中采用浅拷贝视图，针对过期轮次的思维链及冗长工具输出进行动态特征提取与占位替换，保障零 Token 冗余且底层真实对话落盘无污染。
   - L3 大数据外溢 (Spilling)：当单次终端执行输出超阈值时，自动落盘本地日志并仅向模型反馈首尾视图与日志路径，引导模型自主用 read_file 按需下钻。
3. 人机协同 (HITL) 与运行时动态纠偏 (Steering)：
   - 权限可控：支持在前端对 write_file / edit_file 等破坏性操作进行可视化 Diff 预览与一键审批/拒绝。
   - 运行时干预：在模型多步自主循环中，用户可随时通过轻量队列注入 Steering 指令，实现不打断任务流的无感纠偏。
4. 全闭环工程化体验：
   前端支持 Todo 动态看板追踪、多模态附件拖拽上传，并提供独立的本地生成 Web 应用 iframe 实时预览与调试沙箱。

四、其它说明
1. 安全规范：项目全程通过环境变量注入 API Key，工具内部严格防御读取 .env 凭据文件，仓库无任何敏感信息泄露。
2. 自愈引导：本地工具执行返回结构化错误与自愈建议（Self-Healing Suggestions），引导大模型在命令报错或文件冲突时自主修复。