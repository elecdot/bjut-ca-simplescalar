#include <stdio.h>
#include <stdlib.h>

typedef struct Node {
    int value;
    int next;  /* 存储下一个节点的下标，-1 表示结束 */
} Node;

/* 简单线性同余伪随机数发生器，避免依赖库实现 */
static unsigned int seed = 1;
static unsigned int my_rand(void) {
    seed = seed * 1103515245u + 12345u;
    return seed;
}

int main(int argc, char *argv[]) {
    /* 第一个参数：节点个数（默认 1M）
       第二个参数：遍历步数（默认 = 4 * 节点数） */
    int n = (argc > 1) ? atoi(argv[1]) : 1024 * 1024;
    int steps = (argc > 2) ? atoi(argv[2]) : 4 * n;
    int i;
    int head;
    int p;
    volatile long sum = 0;

    Node *nodes = (Node *)malloc((size_t)n * sizeof(Node));
    int *perm = (int *)malloc((size_t)n * sizeof(int));
    if (!nodes || !perm) {
        fprintf(stderr, "malloc failed\n");
        free(nodes); free(perm);
        return 1;
    }

    for (i = 0; i < n; i++) {
        nodes[i].value = i;
        nodes[i].next = -1;
        perm[i] = i;
    }

    /* Fisher-Yates 打乱 perm，构造随机访问顺序 */
    for (i = n - 1; i > 0; i--) {
        unsigned int r = my_rand() % (unsigned int)(i + 1);
        int tmp = perm[i];
        perm[i] = perm[r];
        perm[r] = tmp;
    }

    /* 根据 perm 构造单链表 */
    head = perm[0];
    for (i = 0; i < n - 1; i++) {
        nodes[perm[i]].next = perm[i + 1];
    }
    nodes[perm[n - 1]].next = -1;

    p = head;
    for (i = 0; i < steps; i++) {
        if (p == -1) {
            p = head;  /* 走完一圈后重新从头开始 */
        }
        sum += nodes[p].value;
        p = nodes[p].next;
    }

    printf("sum=%ld\n", sum);

    free(nodes);
    free(perm);
    return 0;
}
