from typing import List


def threeSum(nums: List[int]) -> List[List[int]]:
    """返回所有和为 0 且不重复的三元组。"""
    res = []
    nums.sort()
    n = len(nums)

    for i in range(n):
        # 跳过重复的起始数字
        if i > 0 and nums[i] == nums[i - 1]:
            continue
        # 剪枝：最小的数已经大于 0，则后续不可能凑出 0
        if nums[i] > 0:
            break

        left, right = i + 1, n - 1
        target = -nums[i]
        while left < right:
            s = nums[left] + nums[right]
            if s == target:
                res.append([nums[i], nums[left], nums[right]])
                left += 1
                right -= 1
                # 跳过重复元素
                while left < right and nums[left] == nums[left - 1]:
                    left += 1
                while left < right and nums[right] == nums[right + 1]:
                    right -= 1
            elif s < target:
                left += 1
            else:
                right -= 1

    return res
