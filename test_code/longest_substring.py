def lengthOfLongestSubstring(s: str) -> int:
    from collections import defaultdict
    char_index = defaultdict(int)  # 记录字符最后出现的位置（1-indexed）
    left = 1
    max_len = 0

    for i, ch in enumerate(s, start=1):
        # 如果当前字符在窗口内出现过，则更新左边界
        if ch in char_index and char_index[ch] >= left:
            left = char_index[ch] + 1
        char_index[ch] = i
        max_len = max(max_len, i - left + 1)

    return max_len


if __name__ == "__main__":
    tests = [
        ("abcabcbb", 3),
        ("bbbbb", 1),
        ("pwwkew", 3),
        ("", 0),
        (" ", 1),
        ("au", 2),
        ("dvdf", 3),
    ]
    for s, expected in tests:
        result = lengthOfLongestSubstring(s)
        status = "OK" if result == expected else "FAIL"
        print(f"{status} s={s!r:12} expected={expected} got={result}")
