import pytest

from solution import threeSum


def test_example1():
    nums = [-1, 0, 1, 2, -1, -4]
    result = threeSum(nums)
    # 集合比较，忽略顺序
    expected = {(-1, -1, 2), (-1, 0, 1)}
    assert {tuple(triplet) for triplet in result} == expected


def test_example2():
    nums = [0, 1, 1]
    assert threeSum(nums) == []


def test_example3():
    nums = [0, 0, 0]
    result = threeSum(nums)
    assert {tuple(t) for t in result} == {(0, 0, 0)}


def test_no_repeated_triplets():
    # 多组重复元素的情况
    nums = [-2, 0, 0, 2, 2]
    result = threeSum(nums)
    assert {tuple(t) for t in result} == {(-2, 0, 2)}


def test_empty_and_short():
    assert threeSum([]) == []
    assert threeSum([0, 1]) == []


def test_all_negative():
    assert threeSum([-3, -2, -1]) == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
