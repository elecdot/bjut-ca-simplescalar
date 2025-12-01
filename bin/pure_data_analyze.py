# pure_data_analyze.py
#
# 只做结果解析与图表绘制，便于在宿主机/Notebook 环境使用

import sys
import os
import re
import yaml
import pandas as pd

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_sim_output(path: str) -> dict:
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


def analyze_results(conf: dict):
    sim_conf = conf["sim"]
    out_root = sim_conf.get("output_dir", "results")
    experiments = conf["experiments"]

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

        if "dl1.miss_rate" in df.columns:
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


def main():
    if len(sys.argv) < 2:
        print("Usage: python pure_data_analyze.py <config.yaml>")
        sys.exit(1)
    cfg_path = sys.argv[1]
    conf = load_config(cfg_path)
    analyze_results(conf)


if __name__ == "__main__":
    main()
