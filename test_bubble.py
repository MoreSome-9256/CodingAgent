import pytest

from bubble_sort import bubble_sort


def test_empty_list():
    assert bubble_sort([]) == []


def test_single_element():
    assert bubble_sort([5]) == [5]


def test_sorted_ascending():
    # 正序（已排好序）
    lst = [1, 2, 3, 4, 5]
    assert bubble_sort(lst) == [1, 2, 3, 4, 5]


def test_reverse_sorted():
    # 逆序
    lst = [5, 4, 3, 2, 1]
    assert bubble_sort(lst) == [1, 2, 3, 4, 5]


def test_duplicates():
    lst = [3, 1, 2, 3, 1]
    assert bubble_sort(lst) == [1, 1, 2, 3, 3]
