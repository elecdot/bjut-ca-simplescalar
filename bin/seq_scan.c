#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    /* 第一个参数：数组元素个数，默认 8M 元素
       第二个参数：重复扫描次数，默认 4 次 */
    int n = (argc > 1) ? atoi(argv[1]) : 8 * 1024 * 1024;
    int repeat = (argc > 2) ? atoi(argv[2]) : 4;

    int *a = (int *)malloc((size_t)n * sizeof(int));
    if (!a) {
        fprintf(stderr, "malloc failed\n");
        return 1;
    }

    for (int i = 0; i < n; i++) {
        a[i] = i & 0xFF;
    }

    volatile long long sum = 0; /* 防止被优化掉 */

    for (int r = 0; r < repeat; r++) {
        for (int i = 0; i < n; i++) {
            sum += a[i];
        }
    }

    printf("sum=%lld\n", sum);
    free(a);
    return 0;
}