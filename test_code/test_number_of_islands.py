import pytest


def num_islands(grid):
    """计算二维网格中岛屿的数量。

    使用 DFS 遍历：遇到陆地 '1' 时，岛屿计数 +1，
    并通过深度优先搜索把相连的所有陆地都标记为 '0'（已访问）。
    """
    if not grid or not grid[0]:
        return 0

    rows = len(grid)
    cols = len(grid[0])

    def dfs(r, c):
        # 出界或遇到水，直接返回
        if r < 0 or r >= rows or c < 0 or c >= cols or grid[r][c] == '0':
            return
        # 标记为已访问
        grid[r][c] = '0'
        dfs(r + 1, c)
        dfs(r - 1, c)
        dfs(r, c + 1)
        dfs(r, c - 1)

    count = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == '1':
                count += 1
                dfs(r, c)
    return count


def test_example1():
    grid = [
        ['1', '1', '1', '1', '0'],
        ['1', '1', '0', '1', '0'],
        ['1', '1', '0', '0', '0'],
        ['0', '0', '0', '0', '0'],
    ]
    assert num_islands(grid) == 1


def test_example2():
    grid = [
        ['1', '1', '0', '0', '0'],
        ['1', '1', '0', '0', '0'],
        ['0', '0', '1', '0', '0'],
        ['0', '0', '0', '1', '1'],
    ]
    assert num_islands(grid) == 3


def test_empty():
    assert num_islands([]) == 0
    assert num_islands([[]]) == 0


def test_all_water():
    grid = [
        ['0', '0', '0'],
        ['0', '0', '0'],
    ]
    assert num_islands(grid) == 0


def test_all_land():
    grid = [
        ['1', '1', '1'],
        ['1', '1', '1'],
    ]
    assert num_islands(grid) == 1


def test_diagonal_not_connected():
    # 对角线相邻不算同一岛屿
    grid = [
        ['1', '0'],
        ['0', '1'],
    ]
    assert num_islands(grid) == 2
