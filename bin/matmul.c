#include <stdio.h>
#include <stdlib.h>

/* 简单的方阵乘法 C = A * B
 * 默认 N=256，可通过命令行调整
 */

int main(int argc, char *argv[]) {
    int N = (argc > 1) ? atoi(argv[1]) : 256;

    size_t size = (size_t)N * (size_t)N;
    double *A = (double *)malloc(size * sizeof(double));
    double *B = (double *)malloc(size * sizeof(double));
    double *C = (double *)malloc(size * sizeof(double));

    if (!A || !B || !C) {
        fprintf(stderr, "malloc failed\n");
        free(A); free(B); free(C);
        return 1;
    }

    /* 初始化矩阵 */
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            A[i * N + j] = (i + j) * 0.5;
            B[i * N + j] = (i == j) ? 1.0 : 0.0;
            C[i * N + j] = 0.0;
        }
    }

    /* 经典 i-j-k 三重循环 */
    for (int i = 0; i < N; i++) {
        for (int k = 0; k < N; k++) {
            double aik = A[i * N + k];
            for (int j = 0; j < N; j++) {
                C[i * N + j] += aik * B[k * N + j];
            }
        }
    }

    volatile double checksum = 0.0;
    for (int i = 0; i < N; i++) {
        checksum += C[i * N + (i % N)];
    }

    printf("checksum=%f\n", checksum);

    free(A); free(B); free(C);
    return 0;
}
