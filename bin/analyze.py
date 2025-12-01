# analyze.py

import sys
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
import shlex
import math

import yaml
import pandas as pd

# 强制使用无显示的后端，兼容无 GUI 环境的容器
os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ----------------- 工具函数 ----------------- #

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def split_opts(opts):
    """
    旧配置里每个字符串可能包含空格（例如 "-cache:dl2 ul2:1024:64:4:l"）。
    这里用 shlex.split 展开，避免 sim-cache 收到带空格的单一参数。
    """
    tokens = []
    for opt in opts:
        tokens.extend(shlex.split(opt))
    return tokens


def extract_dl1(tokens):
    """
    选项列表是 token 化后的（如 ["-cache:dl1", "dl1:64:32:1:l", ...]）。
    找到 "-cache:dl1" 并返回其索引及后一个 token（dl1 配置串）。
    """
    for i in range(len(tokens) - 1):
        if tokens[i] == "-cache:dl1":
            return i, tokens[i + 1]
    return None, None


def build_full_assoc_same_capacity(dl1_cfg):
    """
    给定 dl1:<nsets>:<bsize>:<assoc>:<repl>
    返回全相联但容量相同的配置：nsets=1，assoc = nsets*assoc。
    """
    parts = dl1_cfg.split(":")
    if len(parts) < 5:
        return None
    _, nsets, bsize, assoc, repl = parts[:5]
    try:
        nsets_i = int(nsets)
        bsize_i = int(bsize)
        assoc_i = int(assoc)
    except ValueError:
        return None
    total_lines = nsets_i * assoc_i
    return "dl1:1:{}:{}:{}".format(bsize_i, total_lines, repl)


def build_ideal_dl1(dl1_cfg, target_bytes=8 * 1024 * 1024, max_assoc=16):
    """
    构造“近似无限容量”的大容量 L1：
    - 块大小与原配置一致
    - 容量至少 target_bytes
    - 将相联度限制在 max_assoc（避免 sim-cache 在极大相联度下过慢）
      通过增加 nsets 提供总容量
    """
    parts = dl1_cfg.split(":")
    if len(parts) < 5:
        return None
    _, _, bsize, _, repl = parts[:5]
    try:
        bsize_i = int(bsize)
    except ValueError:
        return None
    lines_target = int(math.ceil(float(target_bytes) / float(bsize_i)))
    assoc = min(max_assoc, max(1, lines_target))
    nsets = int(math.ceil(float(lines_target) / float(assoc)))
    return "dl1:{}:{}:{}:{}".format(nsets, bsize_i, assoc, repl)


def replace_dl1(tokens, new_dl1_cfg):
    """
    在 token 列表中替换 dl1 配置（紧随 "-cache:dl1" 的下一个 token）。
    若不存在，则在最前插入 "-cache:dl1", <cfg>。
    """
    out = []
    replaced = False
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if tok == "-cache:dl1" and not replaced:
            out.append(tok)
            if i + 1 < n:
                out.append(new_dl1_cfg)
                i += 2
            else:
                out.append(new_dl1_cfg)
                i += 1
            replaced = True
        else:
            out.append(tok)
            i += 1
    if not replaced:
        out = ["-cache:dl1", new_dl1_cfg] + out
    return out


def parse_sim_output(path: str) -> dict:
    """
    简单解析 sim-cache 输出：
    把以 'dl1.' / 'ul2.' 开头且第二列是数字的行收集为 metrics。
    """
    metrics = {}
    if not os.path.exists(path):
        return metrics

    num_re = re.compile(r'^-?\d+(\.\d+)?([eE][-+]?\d+)?$')

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            name = parts[0]
            val_str = parts[1]

            if not (name.startswith("dl1.") or name.startswith("ul2.")):
                continue

            if not num_re.match(val_str):
                continue

            try:
                val = float(val_str)
            except ValueError:
                continue

            metrics[name] = val

    return metrics


def run_single_sim(sim_bin, base_opts, program_path, program_args,
                   extra_opts, out_path):
    ensure_dir(os.path.dirname(out_path))
    # 先应用 experiment 特定的 dl1 配置，再接通用选项，避免 il1 指向 dl1 时出现未定义。
    cmd = [sim_bin] + extra_opts + base_opts + [program_path] + program_args
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# CMD: " + " ".join(cmd) + "\n\n")
        try:
            ret = subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT)
            if ret != 0:
                f.write("\n# EXITCODE: {}\n".format(ret))
        except Exception as e:
            f.write("\n# ERROR: {}\n".format(e))


# ----------------- 实验运行 ----------------- #

def run_experiments(conf: dict):
    sim_conf = conf["sim"]
    sim_bin = sim_conf.get("sim_cache", "sim-cache")
    base_opts = split_opts(sim_conf.get("base_options", []))
    dl2_default = sim_conf.get("dl2_option", "-cache:dl2 ul2:1024:64:4:l")
    dl2_tokens = split_opts([dl2_default])
    out_root = sim_conf.get("output_dir", "results")
    max_workers = int(sim_conf.get("max_workers", 4))

    programs = conf["programs"]
    experiments = conf["experiments"]

    jobs = []

    for exp_name, exp_info in experiments.items():
        prog_name = exp_info["program"]
        prog_conf = programs[prog_name]
        prog_path = prog_conf["path"]
        prog_args = prog_conf.get("args", [])
        configs = exp_info["configs"]

        for cfg in configs:
            cfg_id = cfg["id"]
            extra_opts = split_opts(cfg.get("options", []))
            # 如果配置里没有指定 dl2，则补上默认 dl2，确保 il2 指向已定义的 l2。
            if not any(opt.startswith("-cache:dl2") for opt in extra_opts):
                extra_opts = dl2_tokens + extra_opts
            out_dir = os.path.join(out_root, exp_name)
            base_out = os.path.join(out_dir, "{}.out".format(cfg_id))

            # 基础任务
            jobs.append({
                "exp_name": exp_name,
                "cfg_id": cfg_id,
                "variant": "base",
                "label": cfg.get("label", cfg_id),
                "cmd_args": {
                    "sim_bin": sim_bin,
                    "base_opts": base_opts,
                    "program_path": prog_path,
                    "program_args": prog_args,
                    "extra_opts": extra_opts,
                    "out_path": base_out,
                }
            })

            # 生成额外任务：全相联同容量 & 近似无限容量
            _, dl1_cfg = extract_dl1(extra_opts)
            if dl1_cfg:
                fa_cfg = build_full_assoc_same_capacity(dl1_cfg)
                ideal_cfg = build_ideal_dl1(dl1_cfg)
                if fa_cfg:
                    fa_opts = replace_dl1(extra_opts, fa_cfg)
                    jobs.append({
                        "exp_name": exp_name,
                        "cfg_id": cfg_id,
                        "variant": "fa",
                        "label": cfg.get("label", cfg_id),
                        "cmd_args": {
                            "sim_bin": sim_bin,
                            "base_opts": base_opts,
                            "program_path": prog_path,
                            "program_args": prog_args,
                            "extra_opts": fa_opts,
                            "out_path": os.path.join(out_dir, "{}_fa.out".format(cfg_id)),
                        }
                    })
                if ideal_cfg:
                    ideal_opts = replace_dl1(extra_opts, ideal_cfg)
                    jobs.append({
                        "exp_name": exp_name,
                        "cfg_id": cfg_id,
                        "variant": "ideal",
                        "label": cfg.get("label", cfg_id),
                        "cmd_args": {
                            "sim_bin": sim_bin,
                            "base_opts": base_opts,
                            "program_path": prog_path,
                            "program_args": prog_args,
                            "extra_opts": ideal_opts,
                            "out_path": os.path.join(out_dir, "{}_ideal.out".format(cfg_id)),
                        }
                    })

    print("[run] total jobs: {}, max_workers={}".format(len(jobs), max_workers))

    # 并行跑 sim-cache
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(run_single_sim, **job["cmd_args"]): job
            for job in jobs
        }
        for fut in as_completed(futures):
            job = futures[fut]
            exp_name = job["exp_name"]
            cfg_id = job["cfg_id"]
            variant = job.get("variant", "base")
            try:
                fut.result()
                print("[run] DONE {}/{} [{}]".format(exp_name, cfg_id, variant))
            except Exception as e:
                print("[run] ERROR {}/{} [{}]: {}".format(exp_name, cfg_id, variant, e))


# ----------------- 结果分析 ----------------- #

def analyze_results(conf: dict):
    sim_conf = conf["sim"]
    out_root = sim_conf.get("output_dir", "results")
    experiments = conf["experiments"]

    # 关心的一些 metric（如果缺失就留空）
    metrics_of_interest = [
        "dl1.accesses",
        "dl1.misses",
        "dl1.miss_rate",
        "ul2.accesses",
        "ul2.misses",
        "ul2.miss_rate",
    ]

    for exp_name, exp_info in experiments.items():
        print("[analyze] experiment: {}".format(exp_name))
        rows = []
        configs = exp_info["configs"]

        for cfg in configs:
            cfg_id = cfg["id"]
            label = cfg.get("label", cfg_id)
            base_out = os.path.join(out_root, exp_name, "{}.out".format(cfg_id))
            fa_out = os.path.join(out_root, exp_name, "{}_fa.out".format(cfg_id))
            ideal_out = os.path.join(out_root, exp_name, "{}_ideal.out".format(cfg_id))

            metrics = parse_sim_output(base_out)
            fa_metrics = parse_sim_output(fa_out)
            ideal_metrics = parse_sim_output(ideal_out)

            row = {
                "config_id": cfg_id,
                "label": label,
            }
            for m in metrics_of_interest:
                row[m] = metrics.get(m, None)

            dl1_acc = metrics.get("dl1.accesses", None)
            base_miss = metrics.get("dl1.misses", None)
            fa_miss = fa_metrics.get("dl1.misses", None)
            ideal_miss = ideal_metrics.get("dl1.misses", None)

            row["total_misses"] = base_miss
            row["total_miss_rate"] = metrics.get("dl1.miss_rate", None)

            if dl1_acc is not None and ideal_miss is not None:
                row["compulsory_misses"] = ideal_miss
                row["compulsory_rate"] = ideal_miss / dl1_acc if dl1_acc else None
            else:
                row["compulsory_misses"] = None
                row["compulsory_rate"] = None

            if base_miss is not None and fa_miss is not None:
                conflict = base_miss - fa_miss
                row["conflict_misses"] = conflict if conflict >= 0 else 0
                row["conflict_rate"] = row["conflict_misses"] / dl1_acc if dl1_acc else None
            else:
                row["conflict_misses"] = None
                row["conflict_rate"] = None

            if fa_miss is not None and ideal_miss is not None:
                capacity = fa_miss - ideal_miss
                row["capacity_misses"] = capacity if capacity >= 0 else 0
                row["capacity_rate"] = row["capacity_misses"] / dl1_acc if dl1_acc else None
            else:
                row["capacity_misses"] = None
                row["capacity_rate"] = None

            rows.append(row)

        if not rows:
            print("[analyze] no rows for {}, skip".format(exp_name))
            continue

        df = pd.DataFrame(rows)
        # 调整列顺序，便于阅读
        cols_order = [
            "config_id",
            "label",
            "dl1.accesses",
            "dl1.misses",
            "dl1.miss_rate",
            "total_misses",
            "total_miss_rate",
            "compulsory_misses",
            "compulsory_rate",
            "conflict_misses",
            "conflict_rate",
            "capacity_misses",
            "capacity_rate",
            "ul2.accesses",
            "ul2.misses",
            "ul2.miss_rate",
        ]
        df = df.reindex(columns=[c for c in cols_order if c in df.columns])
        csv_path = os.path.join(out_root, "{}_summary.csv".format(exp_name))
        df.to_csv(csv_path, index=False)
        print("[analyze] wrote CSV: {}".format(csv_path))

        # 画 dl1.miss_rate 曲线
        if "dl1.miss_rate" in df.columns:
            # 老版 matplotlib 对字符串 x 轴支持弱：使用整数索引并手动贴 label
            labels = list(df["label"])
            values = list(df["dl1.miss_rate"])
            pairs = [(idx, lbl, val) for idx, (lbl, val) in enumerate(zip(labels, values)) if val is not None]
            if pairs:
                xs = [p[0] for p in pairs]
                lbls = [p[1] for p in pairs]
                ys = [p[2] for p in pairs]

                plt.figure()
                plt.plot(xs, ys, marker="o")
                plt.xlabel("config")
                plt.ylabel("dl1.miss_rate")
                plt.title(exp_info.get("description", exp_name))
                plt.xticks(xs, lbls, rotation=45, ha="right")
                plt.tight_layout()

                img_path = os.path.join(out_root, "{}_dl1_miss_rate.png".format(exp_name))
                plt.savefig(img_path)
                plt.close()
                print("[analyze] wrote plot: {}".format(img_path))

        # 画 miss 分解堆叠柱状图
        if {"compulsory_misses", "conflict_misses", "capacity_misses"}.issubset(df.columns):
            labels = list(df["label"])
            comp = list(df["compulsory_misses"])
            conf = list(df["conflict_misses"])
            capa = list(df["capacity_misses"])
            xs = list(range(len(labels)))
            plt.figure()
            plt.bar(xs, comp, label="compulsory", color="#4c78a8")
            comp_bottom = [v if v is not None else 0 for v in comp]
            plt.bar(xs, conf, bottom=comp_bottom, label="conflict", color="#f58518")
            comp_conf = [
                (comp[i] if comp[i] is not None else 0) + (conf[i] if conf[i] is not None else 0)
                for i in range(len(xs))
            ]
            plt.bar(xs, capa, bottom=comp_conf, label="capacity", color="#54a24b")
            plt.xlabel("config")
            plt.ylabel("dl1 misses (stacked)")
            plt.title("{} miss breakdown".format(exp_info.get("description", exp_name)))
            plt.xticks(xs, labels, rotation=45, ha="right")
            plt.legend()
            plt.tight_layout()
            img_path = os.path.join(out_root, "{}_dl1_miss_breakdown.png".format(exp_name))
            plt.savefig(img_path)
            plt.close()
            print("[analyze] wrote breakdown plot: {}".format(img_path))


# ----------------- CLI 入口 ----------------- #

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze.py [run|analyze|all] [config.yaml]")
        sys.exit(1)

    mode = sys.argv[1]
    cfg_path = sys.argv[2] if len(sys.argv) >= 3 else "config.yaml"

    conf = load_config(cfg_path)

    if mode == "run":
        run_experiments(conf)
    elif mode == "analyze":
        analyze_results(conf)
    elif mode == "all":
        run_experiments(conf)
        analyze_results(conf)
    else:
        print("Unknown mode: {}".format(mode))
        sys.exit(1)


if __name__ == "__main__":
    main()
