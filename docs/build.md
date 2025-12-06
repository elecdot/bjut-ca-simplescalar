# 构建与运行指南

面向实验同学的快速说明：不建议本地编译 SimpleScalar，直接用提供的 Docker 镜像。

## 环境准备
1) 安装 Docker（任一平台）  
2) 进入仓库根目录，构建镜像：
```bash
docker build -t simplescalar .
```
镜像基于 `khaledhassan/simplescalar:latest`，预装 `python3 + pandas + matplotlib`。

## 目录与入口
- 所有命令在 `bin/` 下执行（Makefile、脚本、配置都在这里）。
- 输出目录：`bin/results/`；编译产物：`bin/bin/*.ss`。

## 一键运行
```bash
cd bin
make all        # = build + run + analyze，自动进入容器
```

## 分步执行
```bash
make build      # 编译 *.c -> bin/*.ss
make run        # 按 config.yaml 生成 base/fa/ideal 三类 .out
make analyze    # 解析 .out，生成 CSV + 图表
```

## 容器交互
```bash
cd bin && make docker-shell   # 进入容器，挂载当前仓库到 /workspace
make all USE_DOCKER=0         # 若已在容器内，关闭 Docker 包装
```

## 关键约束
- 仅修改 `bin/config.yaml` 配置实验；脚本不硬编码参数。
- L2 块大小必须 ≥ L1（blocksize 实验已覆盖）。
- 所有输出必须在 `bin/results/`，不要写其他目录。
- `max_workers` 控制并行度，避免占满机器。

## 如需源码编译（不推荐）
- SimpleScalar 源码需古老 gcc（≤3.4），可参考 [社区 fork](https://github.com/Awesome-BUPT/simple-scalar) 与[安装指南](http://www.ann.ece.ufl.edu/courses/eel5764_10fal/project/simplescalar_installation.pdf)。优先使用 Docker 以避免踩坑。***
