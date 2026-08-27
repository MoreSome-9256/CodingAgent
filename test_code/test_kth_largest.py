import random
import unittest

from kth_largest import findKthLargest


class TestKthLargest(unittest.TestCase):
    def test_example_1(self):
        self.assertEqual(findKthLargest([3, 2, 1, 5, 6, 4], 2), 5)

    def test_example_2(self):
        self.assertEqual(findKthLargest([3, 2, 3, 1, 2, 4, 5, 5, 6], 4), 4)

    def test_k_equals_1(self):
        self.assertEqual(findKthLargest([3, 2, 1, 5, 6, 4], 1), 6)

    def test_k_equals_n(self):
        self.assertEqual(findKthLargest([3, 2, 1, 5, 6, 4], 6), 1)

    def test_single_element(self):
        self.assertEqual(findKthLargest([1], 1), 1)

    def test_all_duplicates(self):
        self.assertEqual(findKthLargest([99, 99], 1), 99)
        self.assertEqual(findKthLargest([99, 99], 2), 99)

    def test_sorted_ascending(self):
        self.assertEqual(findKthLargest([1, 2, 3, 4, 5], 3), 3)

    def test_sorted_descending(self):
        self.assertEqual(findKthLargest([5, 4, 3, 2, 1], 2), 4)

    def test_negative_numbers(self):
        self.assertEqual(findKthLargest([-1, -5, -3, -2, -4], 2), -2)

    def test_random_against_sorted(self):
        # 随机校验：结果必须与"直接排序取第 k 大"一致
        for _ in range(50):
            n = random.randint(1, 50)
            nums = [random.randint(-100, 100) for _ in range(n)]
            k = random.randint(1, n)
            expected = sorted(nums, reverse=True)[k - 1]
            self.assertEqual(findKthLargest(list(nums), k), expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
