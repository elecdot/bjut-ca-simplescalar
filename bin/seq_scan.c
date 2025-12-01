#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    /* 第一个参数：数组元素个数，默认 8M 元素
       第二个参数：重复扫描次数，默认 4 次 */
    int n = (argc > 1) ? atoi(argv[1]) : 8 * 1024 * 1024;
    int repeat = (argc > 2) ? atoi(argv[2]) : 4;
    int i;
    int r;
    volatile long sum = 0; /* 防止被优化掉 */

    int *a = (int *)malloc((size_t)n * sizeof(int));
    if (!a) {
        fprintf(stderr, "malloc failed\n");
        return 1;
    }

    for (i = 0; i < n; i++) {
        a[i] = i & 0xFF;
    }

    for (r = 0; r < repeat; r++) {
        for (i = 0; i < n; i++) {
            sum += a[i];
        }
    }

    printf("sum=%ld\n", sum);
    free(a);
    return 0;
}
