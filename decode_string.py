def decodeString(s: str) -> str:
    stack = []
    cur_str = ""
    cur_num = 0

    for ch in s:
        if ch.isdigit():
            cur_num = cur_num * 10 + int(ch)
        elif ch == '[':
            # push current string and number
            stack.append((cur_str, cur_num))
            cur_str = ""
            cur_num = 0
        elif ch == ']':
            prev_str, num = stack.pop()
            cur_str = prev_str + cur_str * num
        else:
            cur_str += ch

    return cur_str


# Alias for the snake_case name expected by the test suite.
decode_string = decodeString


if __name__ == "__main__":
    test_cases = [
        ("3[a]2[bc]", "aaabcbc"),
        ("3[a2[c]]", "accaccacc"),
        ("2[abc]3[cd]ef", "abcabccdcdcdef"),
        ("abc3[cd]xyz", "abccdcdcdxyz"),
    ]
    for s, expected in test_cases:
        result = decodeString(s)
        status = "PASS" if result == expected else "FAIL"
        print(f"{status}: decodeString({s!r}) = {result!r} (expected {expected!r})")
