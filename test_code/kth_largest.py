from typing import List
import random


def findKthLargest(nums: List[int], k: int) -> int:
    """
    返回数组中第 k 个最大的元素（数组排序后的第 k 个最大元素，而非第 k 个不同元素）。

    基于 Quickselect 算法（快速选择），这是一种基于快速排序分区思想的
    选择算法。每次分区后，根据枢轴的位置决定在左半部分还是右半部分继续查找，
    每次只需处理一侧，因此平均时间复杂度为 O(n)。

    时间复杂度：平均 O(n)，最坏 O(n^2)（可通过随机选择枢轴有效避免）。
    空间复杂度：O(log n)（递归栈），可改为非递归实现优化到 O(1)。

    思路：
        将"第 k 个最大"转化为"第 (n - k) 个最小"（0 索引），
        然后在 [0, n-1] 区间上执行快速选择。
    """
    n = len(nums)
    target = n - k  # 目标下标（第 k 大的元素对应排序后下标 n-k）

    left, right = 0, n - 1
    while left <= right:
        pivot_index = partition(nums, left, right)
        if pivot_index == target:
            return nums[pivot_index]
        elif pivot_index < target:
            left = pivot_index + 1
        else:
            right = pivot_index - 1

    # 正常情况下不会到达这里
    return -1


def partition(nums: List[int], left: int, right: int) -> int:
    """
    对于区间 [left, right] 进行一次分区：
    随机选取一个枢轴，将小于等于枢轴的元素移到左边，
    大于枢轴的元素移到右边，返回枢轴最终所在的索引。
    """
    # 随机选择枢轴，避免最坏情况，同时与 right 交换
    pivot_idx = random.randint(left, right)
    nums[pivot_idx], nums[right] = nums[right], nums[pivot_idx]

    pivot = nums[right]
    i = left  # 记录小于等于枢轴的边界
    for j in range(left, right):
        if nums[j] <= pivot:
            nums[i], nums[j] = nums[j], nums[i]
            i += 1

    # 将枢轴放到正确位置
    nums[i], nums[right] = nums[right], nums[i]
    return i


# 蛇形命名别名，便于测试与调用
find_kth_largest = findKthLargest


if __name__ == "__main__":
    test_cases = [
        ([3, 2, 1, 5, 6, 4], 2, 5),
        ([3, 2, 3, 1, 2, 4, 5, 5, 6], 4, 4),
        ([3, 2, 1, 5, 6, 4], 1, 6),
        ([3, 2, 1, 5, 6, 4], 6, 1),
        ([1], 1, 1),
        ([99, 99], 1, 99),
        ([99, 99], 2, 99),
        ([1, 2, 3, 4, 5], 3, 3),
    ]
    for nums, k, expected in test_cases:
        result = findKthLargest(nums, k)
        status = "PASS" if result == expected else "FAIL"
        print(f"{status}: findKthLargest({nums!r}, {k}) = {result!r} (expected {expected!r})")
