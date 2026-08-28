import unittest
from collections import Counter
from anagram_groups import groupAnagrams


class TestGroupAnagrams(unittest.TestCase):
    def test_example1(self):
        result = groupAnagrams(["eat", "tea", "tan", "ate", "nat", "bat"])
        # 分组内容不依赖顺序，按集合比较
        result_sets = [tuple(sorted(g)) for g in result]
        expected = {tuple(sorted(["bat"])),
                    tuple(sorted(["nat", "tan"])),
                    tuple(sorted(["ate", "eat", "tea"]))}
        self.assertEqual(set(result_sets), expected)

    def test_example2_empty_string(self):
        result = groupAnagrams([""])
        self.assertEqual(result, [[""]])

    def test_example3_single(self):
        result = groupAnagrams(["a"])
        self.assertEqual(result, [["a"]])

    def test_no_anagrams(self):
        result = groupAnagrams(["a", "b", "c"])
        result_sets = [tuple(sorted(g)) for g in result]
        self.assertEqual(len(result_sets), 3)
        expected = {("a",), ("b",), ("c",)}
        self.assertEqual(set(result_sets), expected)

    def test_all_same(self):
        result = groupAnagrams(["abc", "bac", "cab"])
        result_sets = [tuple(sorted(g)) for g in result]
        self.assertEqual(set(result_sets), {("abc", "bac", "cab")})

    def test_repeated_chars(self):
        result = groupAnagrams(["aab", "aba", "baa", "abb"])
        result_sets = [tuple(sorted(g)) for g in result]
        expected = {tuple(sorted(["aab", "aba", "baa"])), ("abb",)}
        self.assertEqual(set(result_sets), expected)

    def test_groups_cover_all_strings(self):
        strs = ["eat", "tea", "tan", "ate", "nat", "bat", "", "a"]
        result = groupAnagrams(strs)
        flat = [s for g in result for s in g]
        self.assertEqual(Counter(flat), Counter(strs))

    def test_multiple_random_groups(self):
        strs = ["", "", "ab", "ba"]
        result = groupAnagrams(strs)
        result_sets = [tuple(sorted(g)) for g in result]
        expected = {("", ""), ("ab", "ba")}
        self.assertEqual(set(result_sets), expected)


if __name__ == "__main__":
    unittest.main()
