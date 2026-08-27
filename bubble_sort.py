def bubble_sort(arr):
    """对整数列表进行冒泡排序（原地排序），返回排序后的列表。"""
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        # 如果这一轮没有发生交换，说明已经有序，提前退出
        if not swapped:
            break
    return arr
