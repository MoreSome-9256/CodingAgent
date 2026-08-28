#include <iostream>
#include <vector>
#include <string>
#include <unordered_map>
#include <algorithm>

using namespace std;

/**
 * 将字母异位词组合在一起。
 *
 * 思路：使用排序后的字符串作为分组键。
 * 字母异位词经过字符排序后得到完全相同的字符串，
 * 因此可以将它们映射到同一个列表中。
 *
 * 复杂度：
 *   时间复杂度：O(n * k * log k)，其中 n 是字符串个数，k 是最大字符串长度
 *   空间复杂度：O(n * k)
 */
class Solution {
public:
    vector<vector<string>> groupAnagrams(vector<string>& strs) {
        unordered_map<string, vector<string>> groups;

        for (const string& s : strs) {
            // 对字符串副本排序后作为键
            string key = s;
            sort(key.begin(), key.end());
            groups[key].push_back(s);
        }

        // 将 map 中的每个分组转存到结果向量中
        vector<vector<string>> result;
        result.reserve(groups.size());
        for (auto& kv : groups) {
            result.push_back(move(kv.second));
        }
        return result;
    }
};

int main() {
    Solution sol;

    {
        vector<string> strs = {"eat", "tea", "tan", "ate", "nat", "bat"};
        auto result = sol.groupAnagrams(strs);
        for (auto& group : result) {
            cout << "[";
            for (size_t i = 0; i < group.size(); ++i) {
                cout << "\"" << group[i] << "\"";
                if (i != group.size() - 1) cout << ", ";
            }
            cout << "]" << endl;
        }
        cout << "---" << endl;
    }

    {
        vector<string> strs = {""};
        auto result = sol.groupAnagrams(strs);
        for (auto& group : result) {
            cout << "[";
            for (size_t i = 0; i < group.size(); ++i) {
                cout << "\"" << group[i] << "\"";
                if (i != group.size() - 1) cout << ", ";
            }
            cout << "]" << endl;
        }
        cout << "---" << endl;
    }

    {
        vector<string> strs = {"a"};
        auto result = sol.groupAnagrams(strs);
        for (auto& group : result) {
            cout << "[";
            for (size_t i = 0; i < group.size(); ++i) {
                cout << "\"" << group[i] << "\"";
                if (i != group.size() - 1) cout << ", ";
            }
            cout << "]" << endl;
        }
    }

    return 0;
}
