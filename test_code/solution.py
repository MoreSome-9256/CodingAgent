from typing import List


def canJump(nums: List[int]) -> bool:
    """
    判断是否能够到达最后一个下标。

    思路：贪心算法，维护当前能够到达的最远位置。
    如果当前位置超过了最远可达位置，则无法继续前进，返回 False。
    否则更新最远可达位置，若能覆盖到最后一个下标，返回 True。
    """
    max_reach = 0
    n = len(nums)

    for i in range(n):
        if i > max_reach:
            return False
        max_reach = max(max_reach, i + nums[i])
        if max_reach >= n - 1:
            return True

    return True


if __name__ == "__main__":
    print(canJump([2, 3, 1, 1, 4]))  # True
    print(canJump([3, 2, 1, 0, 4]))  # False
