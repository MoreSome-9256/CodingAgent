from typing import List
from collections import defaultdict


def groupAnagrams(strs: List[str]) -> List[List[str]]:
    """
    将字母异位词组合在一起。

    思路：使用排序后的字符串作为分组键。
    字母异位词经过字符排序后得到完全相同的字符串，
    因此可以将它们映射到同一个列表中。

    思路2（哈希计数键）：统计每个字符串各字母出现的次数，
    使用计数元组作为键，也能达到同样效果，且无需显式排序。
    这里采用排序法，简洁清晰。
    """
    groups = defaultdict(list)

    for s in strs:
        # 将字符串排序后作为键
        key = "".join(sorted(s))
        groups[key].append(s)

    return list(groups.values())


if __name__ == "__main__":
    print(groupAnagrams(["eat", "tea", "tan", "ate", "nat", "bat"]))
    print(groupAnagrams([""]))
    print(groupAnagrams(["a"]))
