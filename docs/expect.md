# 期望结果与样例

说明典型输出长什么样，便于对比验证。

## 目录结构
- `bin/results/<experiment>/<config>.out`：sim-cache 原始输出（包含 CMD 和指标）
- `bin/results/<experiment>_summary.csv`：汇总表，含总 miss 及 compulsory/conflict/capacity 分解
- 图表：`<experiment>_dl1_miss_rate.png`、`<experiment>_dl1_miss_breakdown.png`

## CSV 样例（节选）

### associativity（seq_scan）
```
config_id,dl1.accesses,dl1.miss_rate,dl1.misses,label,ul2.accesses,ul2.miss_rate,ul2.misses,total_misses,total_miss_rate,compulsory_misses,compulsory_rate,conflict_misses,conflict_rate,capacity_misses,capacity_rate
assoc_1way,104032017.0,0.0572,5946068.0,1-way (64x32x1),7452565.0,0.3357,2502140.0,5946068.0,0.0572,5018169.0,0.0482,927899.0,0.0089,0,0
assoc_2way,104032017.0,0.0481,5003937.0,2-way (32x32x2),6008114.0,0.4165,2502141.0,5003937.0,0.0481,5018169.0,0.0482,0,0,0,0
assoc_4way,104032017.0,0.0481,5003925.0,4-way (16x32x4),6008092.0,0.4165,2502141.0,...
```

### blocksize（seq_scan）
```
config_id,dl1.miss_rate,...,compulsory_rate,conflict_rate,capacity_rate
bsize_32,0.0572,...,0.0572,0,0
bsize_64,0.0427,...,0.0427,0,0
bsize_128,0.0499,...,0.0499,0,0
bsize_256,0.0824,...,0.0824,0,0
bsize_2048,0.6154,...,0.6154,0,0
```
可见块从 32→64B 改善，过大反而恶化。

### key_assoc_matmul
```
mm_assoc_1way miss_rate ~0.3342
mm_assoc_4way/8way/64way miss_rate ~0.084（平台）
```

### key_assoc_random
```
1-way miss_rate ~0.2433，4/8/64-way ~0.2363，改善很小（随机访问）
```

### substitute（替换策略）
```
2KB 1-way LRU vs Rand：miss 率差距极小
8KB/32KB 高相联：差距进一步缩小
```

## 图表示例
- `*_dl1_miss_rate.png`：x 轴为 label，y 为 miss rate 曲线。期待形状：
  - capacity：单调下降、收益递减
  - associativity：1-way 高，2-way 降，之后平台
  - blocksize：32→64 降，过大反升
- `*_dl1_miss_breakdown.png`：堆叠柱状图，展示 compulsory（蓝）、conflict（橙）、capacity（绿）数量。

## 常见判断基准
- `.out` 文件应无 `fatal` / `# EXITCODE` 标记；有则先检查块大小或参数拼接。
- CSV 中 miss_rate 不应全部为 1.0；若为 1 说明模拟异常（如跨块错误）。
- 图表有明显趋势而非全平线，说明实验覆盖有效。***
