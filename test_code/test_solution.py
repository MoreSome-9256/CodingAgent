import unittest
from solution import canJump


class TestCanJump(unittest.TestCase):
    def test_example1(self):
        self.assertTrue(canJump([2, 3, 1, 1, 4]))

    def test_example2(self):
        self.assertFalse(canJump([3, 2, 1, 0, 4]))

    def test_single_element(self):
        # 只有一个元素，已经在最后一个下标，直接可达
        self.assertTrue(canJump([0]))

    def test_zero_at_start(self):
        # 第一个下标最大跳跃长度为 0，无法移动
        self.assertFalse(canJump([0, 2, 3]))

    def test_large_jump(self):
        self.assertTrue(canJump([2, 0, 0]))

    def test_all_zeros_except_last(self):
        self.assertTrue(canJump([1, 1, 1, 0]))

    def test_need_greedy_choice(self):
        self.assertTrue(canJump([2, 5, 0, 0]))


if __name__ == "__main__":
    unittest.main()
