from dotenv import load_dotenv
from agent import CodingAgent

# 加载 .env 环境变量
load_dotenv()

def main():
    agent = CodingAgent()
    print("=" * 50)
    print("自主编程智能体已启动 (输入 exit 或 quit 退出)")
    print("=" * 50)

    while True:
        try:
            task = input("\n请输入你的编程任务 > ")
            if not task.strip():
                continue
            if task.strip().lower() in ["exit", "quit"]:
                print("退出程序。")
                break
            agent.step(task)
        except KeyboardInterrupt:
            print("\n操作已取消。")
            break

if __name__ == "__main__":
    main()