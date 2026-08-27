from typing import List


def dailyTemperatures(temperatures: List[int]) -> List[int]:
    """
    给定一个整数数组 temperatures 表示每天的温度，
    返回一个数组 answer，answer[i] 表示第 i 天之后第一个更高的温度出现在几天后。
    如果之后气温不会再升高，则该位置用 0 代替。

    使用单调递减栈（保存下标），保证栈内温度从栈底到栈顶递减。
    遇到更高的温度时，将对应的天数差值填入结果。

    时间复杂度 O(n)，空间复杂度 O(n)。
    """
    n = len(temperatures)
    answer = [0] * n
    stack = []  # 存储下标，对应温度单调递减

    for i in range(n):
        # 当前温度高于栈顶下标对应的温度，说明找到了栈顶元素的下一个更高温度
        while stack and temperatures[i] > temperatures[stack[-1]]:
            prev = stack.pop()
            answer[prev] = i - prev
        stack.append(i)

    return answer
