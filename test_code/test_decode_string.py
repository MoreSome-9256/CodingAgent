import pytest

from decode_string import decode_string


def test_example_1():
    # 3[a]2[bc] => aaabcbc
    assert decode_string("3[a]2[bc]") == "aaabcbc"


def test_example_2():
    # 3[a2[c]] => accaccacc
    assert decode_string("3[a2[c]]") == "accaccacc"


def test_example_3():
    # 2[abc]3[cd]ef => abcabccdcdcdef
    assert decode_string("2[abc]3[cd]ef") == "abcabccdcdcdef"


def test_example_4():
    # abc3[cd]xyz => abccdcdcdxyz
    assert decode_string("abc3[cd]xyz") == "abccdcdcdxyz"


def test_no_brackets():
    assert decode_string("abc") == "abc"


def test_single_repeat():
    assert decode_string("2[a]") == "aa"


def test_nested_multiple():
    # 2[ab3[cd]] => abcdcdcdabcdcdcd
    assert decode_string("2[ab3[cd]]") == "abcdcdcdabcdcdcd"


def test_multiple_digits():
    # 12[a] => 12 个 a
    assert decode_string("12[a]") == "a" * 12


def test_multiple_segments():
    assert decode_string("1[a]1[b]") == "ab"


def test_adjacent_repeats_and_text():
    assert decode_string("2[ab]c3[d]") == "ababcddd"
