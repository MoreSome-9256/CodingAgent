def length_of_longest_substring(s: str) -> int:
    """找出字符串中不含有重复字符的最长子串的长度。

    使用滑动窗口算法，时间复杂度 O(n)，空间复杂度 O(min(m, n))。
    """
    char_index = {}  # 记录每个字符最近一次出现的索引位置
    left = 0         # 窗口的左边界
    max_len = 0      # 结果

    for right, ch in enumerate(s):
        # 如果当前字符在窗口内出现过，更新左边界
        if ch in char_index and char_index[ch] >= left:
            left = char_index[ch] + 1

        char_index[ch] = right
        max_len = max(max_len, right - left + 1)

    return max_len


if __name__ == "__main__":
    # 测试用例
    test_cases = [
        ("abcabcbb", 3),
        ("bbbbb", 1),
        ("pwwkew", 3),
        ("", 0),
        (" ", 1),
        ("dvdf", 3),
        ("au", 2),
    ]
    for s, expected in test_cases:
        result = length_of_longest_substring(s)
        status = "OK" if result == expected else "FAIL"
        print(f"{status}: length_of_longest_substring({s!r}) = {result}, 期望 = {expected}")
