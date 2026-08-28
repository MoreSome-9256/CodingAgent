from typing import List
from collections import deque


def canFinish(numCourses: int, prerequisites: List[List[int]]) -> bool:
    """
    判断是否可以完成所有课程的学习（即课程依赖图是否存在环）。

    使用 Kahn 拓扑排序算法：
    - 统计每门课程的入度（先修课程数量）
    - 将所有入度为 0 的课程入队（可作为第一门学习的课程）
    - 依次出队，并减少其后续课程的入度，若入度降为 0 再入队
    - 若最终学完的课程数 == numCourses，则无环，返回 True；否则存在环，返回 False
    """
    # 构建邻接表 + 入度表
    in_degree = [0] * numCourses
    graph = [[] for _ in range(numCourses)]

    for a, b in prerequisites:
        # 学习 a 之前必须先学习 b，即 b -> a
        graph[b].append(a)
        in_degree[a] += 1

    # 收集所有入度为 0 的课程
    queue = deque([i for i in range(numCourses) if in_degree[i] == 0])

    completed = 0
    while queue:
        course = queue.popleft()
        completed += 1
        for nxt in graph[course]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)

    # 若完成的课程数等于总课程数，说明无环，可完成全部课程
    return completed == numCourses


if __name__ == "__main__":
    # 示例测试
    print(canFinish(2, [[1, 0]]))  # 期望 True
    print(canFinish(2, [[1, 0], [0, 1]]))  # 期望 False
