from can_finish import canFinish

cases = [
    # (numCourses, prerequisites, expected)
    (2, [[1, 0]], True),                 # 示例1
    (2, [[1, 0], [0, 1]], False),        # 示例2（环）
    (1, [], True),                       # 单门课无先修
    (4, [[1, 0], [2, 0], [3, 1], [3, 2]], True),  # DAG 无环
    (3, [[0, 1], [1, 2], [2, 0]], False),          # 三元环
    (5, [], True),                       # 无任何先修
    (2, [[0, 1]], True),
    (3, [[0, 0]], False),                # 自环
]

all_pass = True
for i, (n, pre, expected) in enumerate(cases):
    result = canFinish(n, pre)
    status = "PASS" if result == expected else "FAIL"
    if result != expected:
        all_pass = False
    print(f"用例{i+1}: canFinish({n}, {pre}) = {result}, 期望 {expected} -> {status}")

print("\n全部通过!" if all_pass else "\n存在失败用例!")
