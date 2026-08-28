import asyncio
from dotenv import load_dotenv
from agent import CodingAgentSession

# 加载 .env 环境变量
load_dotenv()

async def async_main():
    # 在 CLI 模式下，默认使用全权模式 (permission_mode="full")
    # 避免在控制台中实现复杂的异步阻塞审批逻辑
    agent = CodingAgentSession(permission_mode="full")
    print("=" * 55)
    print("🤖 自主编程智能体 CLI 测试入口已启动")
    print("💡 提示: 输入 exit 或 quit 退出")
    print("=" * 55)

    while True:
        try:
            # 等待用户输入任务
            task = input("\n请输入你的编程任务 > ")
            if not task.strip():
                continue
            if task.strip().lower() in ["exit", "quit"]:
                print("退出程序。")
                break
            
            # 使用 async for 消费 agent.py 抛出的异步事件流
            async for event in agent.step_stream(task):
                if event["type"] == "step_start":
                    print(f"\n[Step {event['step']}/{event['max_steps']}] Agent 正在思考与探索...")
                
                elif event["type"] == "tool_call":
                    print(f"  -> 🔧 准备调用工具: {event['name']}")
                    print(f"     参数: {event['args']}")
                
                elif event["type"] == "tool_output":
                    out_text = event['output']
                    # 控制台展示时截断过长的输出，保持整洁
                    if len(out_text) > 300:
                        out_text = out_text[:300] + "\n     ... [已在控制台折叠长输出] ..."
                    
                    # 避免在控制台中打印大块的换行破坏版面，对多行文本稍作处理
                    out_lines = out_text.split('\n')
                    print(f"  <- 🛠️ 工具返回结果:")
                    for line in out_lines:
                         print(f"     {line}")
                
                elif event["type"] == "finish":
                    print("\n" + "=" * 20 + " 最终回复 " + "=" * 20)
                    print(event['content'])
                    print("=" * 50)
                
                elif event["type"] == "error":
                    print(f"\n❌ [执行错误]: {event['message']}")

        except KeyboardInterrupt:
            print("\n\n操作已取消。")
            break
        except Exception as e:
            print(f"\n❌ 运行时异常: {e}")
            break

def main():
    # 使用 asyncio.run 启动异步主循环
    asyncio.run(async_main())

if __name__ == "__main__":
    main()