# Build and run with Docker

SimpleScalar 的交叉编译器与 `sim-cache` 需要在容器里运行。本仓库提供的 `Makefile` 已经自动通过 Docker 代理执行，无需在宿主机安装 SimpleScalar。

## Prerequisite

1. 安装 [Docker](https://docs.docker.com/get-docker/)。  
2. （可选）配置镜像源，你可以参考这篇[教程](https://yeasy.gitbook.io/docker_practice/install/mirror)。

## Build the local image

在仓库根目录执行：

```bash
docker build -t simplescalar .
```

镜像基于 `khaledhassan/simplescalar:latest`，并预装了 `python3 + pandas + matplotlib` 以运行 `analyze.py`。

## Run the workflow (Makefile 会自动进入容器)

1) 进入 `bin/` 目录（Makefile 和源代码所在位置）：

```bash
cd bin
```

2) 直接执行流水线，Makefile 会把自己再拉进容器：

```bash
make all        # 等价于 build + run + analyze
# 或分别执行：
make build
make run
make analyze
```

默认使用镜像名 `simplescalar`，并把仓库根目录挂载到容器的 `/workspace` 下。产物写入 `bin/bin/` 与 `bin/results/`。

## Helpers

- 打开容器交互 shell（会挂载当前仓库到 `/workspace`）：

```bash
cd bin && make docker-shell
```

- 如果你已经手动进入容器，需要绕过 Docker 代理，可加 `USE_DOCKER=0`：

```bash
make all USE_DOCKER=0
```

## Resources

- [Linux 101的Docker教程](https://101.lug.ustc.edu.cn/Ch08/#install-docker)
