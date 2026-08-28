#include <vector>
#include <string>
#include <iostream>
#include <cassert>
#include <functional>

// 计算二维网格中岛屿的数量（DFS 实现）
int numIslands(std::vector<std::vector<char>>& grid) {
    if (grid.empty() || grid[0].empty()) {
        return 0;
    }

    int rows = static_cast<int>(grid.size());
    int cols = static_cast<int>(grid[0].size());

    // 深度优先搜索，把相连陆地全部标记为已访问（'0'）
    std::function<void(int, int)> dfs = [&](int r, int c) {
        // 越界或遇到水，返回
        if (r < 0 || r >= rows || c < 0 || c >= cols || grid[r][c] == '0') {
            return;
        }
        // 标记为已访问
        grid[r][c] = '0';
        dfs(r + 1, c); // 下
        dfs(r - 1, c); // 上
        dfs(r, c + 1); // 右
        dfs(r, c - 1); // 左
    };

    int count = 0;
    for (int r = 0; r < rows; ++r) {
        for (int c = 0; c < cols; ++c) {
            if (grid[r][c] == '1') {
                ++count;
                dfs(r, c);
            }
        }
    }
    return count;
}

// ---------- 测试 ----------
int main() {
    // 示例 1 → 1
    {
        std::vector<std::vector<char>> grid = {
            {'1','1','1','1','0'},
            {'1','1','0','1','0'},
            {'1','1','0','0','0'},
            {'0','0','0','0','0'},
        };
        assert(numIslands(grid) == 1);
        std::cout << "示例 1 测试通过，输出: " << numIslands(grid) << "\n";
    }

    // 示例 2 → 3
    {
        std::vector<std::vector<char>> grid = {
            {'1','1','0','0','0'},
            {'1','1','0','0','0'},
            {'0','0','1','0','0'},
            {'0','0','0','1','1'},
        };
        assert(numIslands(grid) == 3);
        std::cout << "示例 2 测试通过，输出: " << numIslands(grid) << "\n";
    }

    // 空网格 → 0
    {
        std::vector<std::vector<char>> grid;
        assert(numIslands(grid) == 0);
        std::cout << "空网格测试通过，输出: 0\n";
    }

    // 全水 → 0
    {
        std::vector<std::vector<char>> grid = {
            {'0','0','0'},
            {'0','0','0'},
        };
        assert(numIslands(grid) == 0);
        std::cout << "全水测试通过，输出: 0\n";
    }

    // 全陆地 → 1
    {
        std::vector<std::vector<char>> grid = {
            {'1','1','1'},
            {'1','1','1'},
        };
        assert(numIslands(grid) == 1);
        std::cout << "全陆地测试通过，输出: 1\n";
    }

    // 对角线不相邻 → 2
    {
        std::vector<std::vector<char>> grid = {
            {'1','0'},
            {'0','1'},
        };
        assert(numIslands(grid) == 2);
        std::cout << "对角线测试通过，输出: 2\n";
    }

    std::cout << "全部测试通过！\n";
    return 0;
}
