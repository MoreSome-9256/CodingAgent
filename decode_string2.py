def decodeString(s: str) -> str:
    """递归解码 k[encoded_string] 形式的编码字符串。"""

    def dfs(i):
        res, num = "", 0
        while i < len(s):
            ch = s[i]
            if ch.isdigit():
                # 累计多位数
                num = num * 10 + int(ch)
                i += 1
            elif ch == '[':
                # 递归解析括号内的内容，返回(内层字符串, 结束下标)
                inner, i = dfs(i + 1)
                res += inner * num      # 重复 k 次
                num = 0
            elif ch == ']':
                # 本层括号结束，返回结果和 ']' 之后的下标
                return res, i + 1
            else:
                # 普通字符
                res += ch
                i += 1
        return res, i

    result, _ = dfs(0)
    return result


# 与测试套件一致的蛇形命名别名
decode_string = decodeString


if __name__ == "__main__":
    test_cases = [
        ("3[a]2[bc]", "aaabcbc"),
        ("3[a2[c]]", "accaccacc"),
        ("2[abc]3[cd]ef", "abcabccdcdcdef"),
        ("abc3[cd]xyz", "abccdcdcdxyz"),
        ("abc", "abc"),
        ("2[a]", "aa"),
        ("2[ab3[cd]]", "abcdcdcdabcdcdcd"),
        ("12[a]", "a" * 12),
        ("1[a]1[b]", "ab"),
        ("2[ab]c3[d]", "ababcddd"),
    ]
    all_pass = True
    for s, expected in test_cases:
        result = decodeString(s)
        status = "PASS" if result == expected else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"{status}: decodeString({s!r}) = {result!r} (expected {expected!r})")
    print("ALL TESTS PASSED" if all_pass else "SOME TESTS FAILED")
