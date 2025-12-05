# Makefile

# ---------------- Docker wrapper ---------------- #
# 需要在容器里运行 SimpleScalar 工具链。默认使用本仓库的 Docker 镜像。
REPO_ROOT   := $(abspath $(CURDIR)/..)
DOCKER_IMG  ?= simplescalar
USE_DOCKER  ?= 1

ifeq ($(INSIDE_SIM_DOCKER),)
ifneq ($(USE_DOCKER),0)
DOCKER_RUN  := docker run --rm -v "$(REPO_ROOT)":/workspace -w /workspace/bin -e INSIDE_SIM_DOCKER=1 $(DOCKER_IMG)
DOCKER_IT_RUN := docker run --rm -it -v "$(REPO_ROOT)":/workspace -w /workspace/bin -e INSIDE_SIM_DOCKER=1 $(DOCKER_IMG)

.PHONY: all build run analyze clean docker-shell docker-image

all build run analyze clean:
	$(DOCKER_RUN) make $@ USE_DOCKER=0

docker-shell:
	$(DOCKER_IT_RUN) /bin/bash

docker-image:
	docker build -t $(DOCKER_IMG) "$(REPO_ROOT)"
else
# 如果用户明确关闭 Docker，则继续使用本地环境
endif
endif

# ---------------- Pipeline inside container ---------------- #
ifeq ($(INSIDE_SIM_DOCKER),1)
ENABLE_PIPELINE := 1
endif
ifeq ($(USE_DOCKER),0)
ENABLE_PIPELINE := 1
endif

ifeq ($(ENABLE_PIPELINE),1)
# SimpleScalar 交叉编译器（容器内已提供）
CC      := sslittle-na-sstrix-gcc
CFLAGS  ?= -O2

PYTHON  ?= python3
CONFIG  ?= config.yaml

BIN_DIR     := bin
RESULT_DIR  := results

PROGRAMS    := seq_scan matmul random_list
SS_BINS     := $(PROGRAMS:%=$(BIN_DIR)/%.ss)

.PHONY: all build run analyze clean dirs

# 一条命令做完：编译 + 跑实验 + 分析
all: build run analyze

# 只编译
build: dirs $(SS_BINS)

dirs:
	@mkdir -p $(BIN_DIR) $(RESULT_DIR)

# 编译 C 到 SimpleScalar 可执行文件
$(BIN_DIR)/%.ss: %.c | dirs
	$(CC) $(CFLAGS) $< -o $@

# 运行所有 sim-cache 实验（并行在 Python 里控制）
run: build
	$(PYTHON) analyze.py run $(CONFIG)

# 读取 sim-cache 输出，生成 CSV + 图表
analyze:
	$(PYTHON) analyze.py analyze $(CONFIG)

# 清理
clean:
	rm -rf $(BIN_DIR) $(RESULT_DIR)
endif
