import unittest

from daily_temperatures import dailyTemperatures


class TestDailyTemperatures(unittest.TestCase):
    def test_example_1(self):
        self.assertEqual(
            dailyTemperatures([73, 74, 75, 71, 69, 72, 76, 73]),
            [1, 1, 4, 2, 1, 1, 0, 0],
        )

    def test_example_2(self):
        self.assertEqual(dailyTemperatures([30, 40, 50, 60]), [1, 1, 1, 0])

    def test_example_3(self):
        self.assertEqual(dailyTemperatures([30, 60, 90]), [1, 1, 0])

    def test_all_equal(self):
        self.assertEqual(dailyTemperatures([0, 0, 0]), [0, 0, 0])

    def test_single_element(self):
        self.assertEqual(dailyTemperatures([1]), [0])

    def test_decreasing(self):
        self.assertEqual(dailyTemperatures([5, 4, 3, 2, 1]), [0, 0, 0, 0, 0])

    def test_two_elements(self):
        self.assertEqual(dailyTemperatures([1, 2]), [1, 0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
