# AGENTS.md

## Overview

本项目是一套围绕 SimpleScalar 的全自动 Cache 实验系统。
它包含：

1. 三个 C 程序（不同访存模式）。
2. `config.yaml`（集中式实验配置）。
3. `Makefile`（自动编译 + 自动实验调度 + 调用 Python）。
4. `analyze.py`（运行全部 `sim-cache` + 结果解析 + CSV 输出 + 图表绘制）。
5. 未来将交给 Codex/Aengts 接手继续增强自动化能力。

本文件（AGENTS.md）用于描述：

* 各 Agent 的角色
* 项目当前状态
* 需要遵守的约束
* 文件结构与任务流
  以便 Codex/Aengts 能顺畅衔接并继续扩展。

---

## Project Goals

1. **自动化执行 SimpleScalar sim-cache 实验**

   * 支持并行任务调度
   * 每个实验独立运行，输出重定向至文件
   * 配置完全由 `config.yaml` 驱动

2. **自动化数据抽取与分析**

   * 解析 sim-cache 输出
   * 生成 `.csv` 汇总文件
   * 输出图表（如 miss rate 曲线图）
   * 后续扩展分析逻辑

3. **模块化扩展**

   * 可以在 `config.yaml` 中继续添加实验
   * 支持添加更多 metric
   * 支持更多程序与参数
   * 便于在 Aengts/Codex 中添加新的 Agent（如报告自动生成 Agent）

---

## Current Files & Responsibilities

项目当前已具备以下关键文件：

### 1. `seq_scan.c`, `matmul.c`, `random_list.c`

三类具有代表性的缓存访问模式程序：

* `seq_scan.c`：顺序访问（空间局部性强）
* `matmul.c`：矩阵乘（三重循环，有空间与时间局部性）
* `random_list.c`：随机链表（最低局部性）

均已适配 SimpleScalar 工具链，可使用 `sslittle-na-sstrix-gcc` 编译。

---

### 2. `config.yaml`

集中配置所有实验参数：

* 每类实验（capacity / associativity / blocksize / key assays）
* 每个小实验的参数
* 程序路径
* `sim-cache` 基础参数
* 并行度
* 输出目录

实验体系依赖它，不应该在源码里 hard-code 参数。

---

### 3. `Makefile`

核心功能：

1. 自动创建目录 (`bin/`, `results/`)
2. 编译所有程序 → SimpleScalar 可执行文件
3. 调用 `python analyze.py run` 执行全部实验
4. 调用 `python analyze.py analyze` 生成 `.csv` 和图表
5. `make all` = build + run + analyze（完整流水线）

---

### 4. `analyze.py`

负责全部自动化逻辑：

#### 模式 1：`run`

* 解析 `config.yaml`
* 构造所有 `sim-cache` 命令
* 通过 ThreadPoolExecutor 并行运行
* 生成 `results/<experiment>/<id>.out`

#### 模式 2：`analyze`

* 解析每个 `.out` 的 sim-cache metric
* 提取主要字段（dl1/ul2 misses, miss_rate 等）
* 写入 `<experiment>_summary.csv`
* 输出图表 `<experiment>_dl1_miss_rate.png`

该脚本是整个系统的中枢自动化调度器。

---

## Agents Specification

此项目适合使用以下类型的 Agent（适配 Codex/Aengts）：

### Agent 1: **Build Agent**

职责：

* 根据 `Makefile` 自动执行编译
* 检查 SimpleScalar 工具链可用性
* 如缺失则提示用户安装
* 扩展能力：自动检测新增 `.c` 文件，生成 Makefile 规则

输入：

* `Makefile`
* `*.c`

输出：

* `bin/*.ss`（SimpleScalar 可执行文件）

---

### Agent 2: **Experiment Runner Agent**

职责：

* 调用 `analyze.py run`
* 并行执行所有 sim-cache 子任务
* 确保每个任务的日志路径正确
* 监控失败实验并输出诊断信息

输入：

* `config.yaml`
* 当前工作目录结构

输出：

* `results/<experiment>/<config_id>.out`

---

### Agent 3: **Analysis Agent**

职责：

* 调用 `analyze.py analyze`
* 自动生成 `.csv` 数据表
* 自动生成图表（png/svg）
* 提供统计摘要（如最优 miss rate 配置）

输入：

* `results/` 输出文件

输出：

* `<experiment>_summary.csv`
* `<experiment>_dl1_miss_rate.png`

---

### Agent 4: **Reporting Agent（可选扩展）**

职责：

* 自动读取 `summary.csv`
* 生成学术风格的实验报告
* 包含图表、实验方法、结论
* 适用于论文/课堂作业的自动生产

输入：

* `summary.csv`
* 图表

输出：

* `report.md` 或 `report.pdf`

---

## Workflow Summary

整个系统的流水线如下：

```
        Build Agent
             |
             v
     +----------------+
     | compile C --> *.ss |
     +----------------+
             |
             v
    Experiment Runner Agent
             |
             v
 results/<experiment>/<id>.out
             |
             v
         Analysis Agent
             |
   CSV tables + charts generated
             |
             v
   (optional) Reporting Agent
```

用户只需执行：

```
make all
```

Agents 将自动完成全部步骤。

---

## Constraints & Conventions

为了保持系统稳定及可扩展性，所有 Agent 需要遵守以下规则：

### 1. 严禁硬编码 sim-cache 参数

所有实验参数必须来自 `config.yaml`。

### 2. 输出必须写入 `results/` 目录

不能乱写入项目根目录。

### 3. 并行任务必须遵循 `max_workers`

避免占满机器资源。

### 4. sim-cache 输出必须保留完整原文

便于未来调试与精细分析。

### 5. 所有图表必须使用 matplotlib

确保环境可重复执行。

### 6. 强制结构化 CSV 输出

列字段必须一致：
`config_id, label, dl1.accesses, dl1.misses, ...`

### 7. Agent 之间使用文件接口通讯

Aengts 的 Agent 不共享内存，必须使用文件作为接口。