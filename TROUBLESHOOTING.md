# Troubleshooting

记录开发与运行中遇到的实际问题与解决方案。

## Docker / 环境
- **pip 参数不兼容**：基础镜像内 pip 版本旧，不支持 `--no-cache-dir`、`--trusted-host`。改为直接指定镜像源或使用 apt 安装 `python3-*` 包。
- **无法访问官方 PyPI**：改用清华镜像 `https://pypi.tuna.tsinghua.edu.cn/simple`，或用 apt 安装 `python3-yaml/pandas/matplotlib`。
- **容器内无图形界面**：matplotlib 需强制 `Agg` 后端（代码已设置），否则报 `$DISPLAY` 错误。

## SimpleScalar / sim-cache
- **缺少 sim-cache 参数**：`-cache:il1 dl1` 等参数必须在命令行中出现；run.py 会补全 `-cache:dl2`，但其他参数需在 config.yaml 中明确。
- **L1/L2 块大小关系**：L2 块必须大于等于 L1。否则 `fatal: cache: access error: access spans block`。
- **il1 未定义错误**：当 il1 指向 dl1 时，必须先定义 dl1。已调整参数顺序（实验特定 dl1 放在前面）。
- **极大相联度导致模拟极慢**：全相联超大容量会使 LRU 更新成本巨大。ideal 配置已限制相联度 ≤16，并通过增加 nsets 提供容量。

## 代码 / Python 兼容性
- **老版 Python 不支持 f-string、subprocess.run**：已替换为 `.format` 和 `subprocess.call`。
- **matplotlib 与 pandas 兼容问题**：对 x 轴字符串使用整数索引 + `xticks`，避免旧版 `plot` 误解析格式字符串。

## Makefile / 目录
- **路径错误**：所有命令需在 `bin/` 目录运行（Makefile 所在）。输出强制写入 `bin/results/`。
- **容器内重复套 Docker**：进入容器后需 `USE_DOCKER=0`，否则会再次尝试启动容器。

## 性能
- **任务过多**：每个配置会生成 base/fa/ideal 三个模拟。`max_workers` 可在 config.yaml 中调节，推荐逻辑核数一半。
- **大相联度 ideal 过慢**：可下调 `target_bytes` 或 `max_assoc`（run.py 中 `build_ideal_dl1`）。

## 常用检查项
- 输出 `.out` 是否有 `# EXITCODE` 或 `fatal`；出现则先检查参数（块大小、il1 定义、路径）。
- 检查 `bin/results/*_summary.csv` 是否填有数值（非 1.0 全 miss）。
- 如需手动 debug，先 `make docker-shell` 进入容器再运行 `python run.py config.yaml`。***
