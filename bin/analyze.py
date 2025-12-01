# analyze.py

import sys
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml
import pandas as pd
import matplotlib.pyplot as plt


# ----------------- 工具函数 ----------------- #

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


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
    cmd = [sim_bin] + base_opts + extra_opts + [program_path] + program_args
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# CMD: " + " ".join(cmd) + "\n\n")
        try:
            subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, check=False)
        except Exception as e:
            f.write(f"\n# ERROR: {e}\n")


# ----------------- 实验运行 ----------------- #

def run_experiments(conf: dict):
    sim_conf = conf["sim"]
    sim_bin = sim_conf.get("sim_cache", "sim-cache")
    base_opts = sim_conf.get("base_options", [])
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
            extra_opts = cfg.get("options", [])
            out_dir = os.path.join(out_root, exp_name)
            out_file = os.path.join(out_dir, f"{cfg_id}.out")

            jobs.append({
                "exp_name": exp_name,
                "cfg_id": cfg_id,
                "label": cfg.get("label", cfg_id),
                "cmd_args": {
                    "sim_bin": sim_bin,
                    "base_opts": base_opts,
                    "program_path": prog_path,
                    "program_args": prog_args,
                    "extra_opts": extra_opts,
                    "out_path": out_file,
                }
            })

    print(f"[run] total jobs: {len(jobs)}, max_workers={max_workers}")

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
            try:
                fut.result()
                print(f"[run] DONE {exp_name}/{cfg_id}")
            except Exception as e:
                print(f"[run] ERROR {exp_name}/{cfg_id}: {e}")


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
        print(f"[analyze] experiment: {exp_name}")
        rows = []
        configs = exp_info["configs"]

        for cfg in configs:
            cfg_id = cfg["id"]
            label = cfg.get("label", cfg_id)
            out_file = os.path.join(out_root, exp_name, f"{cfg_id}.out")

            metrics = parse_sim_output(out_file)
            row = {
                "config_id": cfg_id,
                "label": label,
            }
            for m in metrics_of_interest:
                row[m] = metrics.get(m, None)

            rows.append(row)

        if not rows:
            print(f"[analyze] no rows for {exp_name}, skip")
            continue

        df = pd.DataFrame(rows)
        csv_path = os.path.join(out_root, f"{exp_name}_summary.csv")
        df.to_csv(csv_path, index=False)
        print(f"[analyze] wrote CSV: {csv_path}")

        # 画 dl1.miss_rate 曲线
        if "dl1.miss_rate" in df.columns:
            plt.figure()
            # 用 label 做 x 轴，便于阅读
            x = df["label"]
            y = df["dl1.miss_rate"]

            plt.plot(x, y, marker="o")
            plt.xlabel("config")
            plt.ylabel("dl1.miss_rate")
            plt.title(exp_info.get("description", exp_name))
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()

            img_path = os.path.join(out_root, f"{exp_name}_dl1_miss_rate.png")
            plt.savefig(img_path)
            plt.close()
            print(f"[analyze] wrote plot: {img_path}")


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
        print(f"Unknown mode: {mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
