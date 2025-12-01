# Makefile

# SimpleScalar 交叉编译器（按你本地环境改）
CC      ?= sslittle-na-sstrix-gcc
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
