# config.yaml 说明

`bin/config.yaml` 驱动全部实验，不应在代码中硬编码参数。

## 顶层字段
- `sim`：sim-cache 全局设置  
  - `sim_cache`：sim-cache 可执行文件路径（默认 `sim-cache`）  
  - `max_workers`：并行任务数  
  - `output_dir`：输出目录（默认 `results`）  
  - `base_options`：通用选项列表（已包含 il1/il2 定义）  
  - `dl2_option`：默认 L2 配置（若实验未指定则自动补上）
- `programs`：基准程序及参数  
  - `path`：可执行文件路径（`bin/*.ss`）  
  - `args`：命令行参数数组
- `experiments`：实验集合，每个实验包含若干 `configs`

## 每个 experiment.config
- `id`：配置 ID，用于输出文件名  
- `label`：显示名称  
- `options`：sim-cache 参数列表（会被拆成 tokens）。典型：`-cache:dl1 dl1:64:32:1:l`
- `program`（在实验层）指定绑定的基准程序。

## 约束与技巧
- **L1/L2 块大小**：L2 块必须 ≥ L1；否则 sim-cache 报错。blocksize 实验已额外设置 L2 块=2048。
- **il1 定义顺序**：当 il1 指向 dl1，需先定义 dl1；run.py 会把实验特定 dl1 放在通用参数之前。
- **自动派生任务**：每个配置自动生成 base / full-assoc-same-capacity / ideal 大容量三类任务；ideal 默认 8MB、相联度 ≤16。
- **新增实验**：在 `experiments` 下添加新节点，指向已有程序或新程序；run/analysis 脚本自动适配，无需改代码。
- **输出目录**：统一写入 `output_dir`（默认 `bin/results/`），不要写其它路径。

## 示例片段
```yaml
sim:
  sim_cache: "sim-cache"
  max_workers: 8
  base_options:
    - "-cache:il1 il1:256:32:1:l"
    - "-cache:il2 dl2"
  dl2_option: "-cache:dl2 ul2:1024:64:4:l"

programs:
  seq_scan:
    path: "bin/seq_scan.ss"
    args: ["8000000", "4"]

experiments:
  capacity:
    program: "seq_scan"
    configs:
      - id: "cap_x1"
        label: "2KB (64x32x1)"
        options:
          - "-cache:dl1 dl1:64:32:1:l"
```
