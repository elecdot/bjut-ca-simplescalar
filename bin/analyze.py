# analyze.py
# 兼容旧用法的入口：运行实验（容器内）+ 结果分析

import sys

from run import run_experiments, load_config as load_conf_run
from pure_data_analyze import analyze_results, load_config as load_conf_analyze


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze.py [run|analyze|all] [config.yaml]")
        sys.exit(1)

    mode = sys.argv[1]
    cfg_path = sys.argv[2] if len(sys.argv) >= 3 else "config.yaml"

    if mode == "run":
        conf = load_conf_run(cfg_path)
        run_experiments(conf)
    elif mode == "analyze":
        conf = load_conf_analyze(cfg_path)
        analyze_results(conf)
    elif mode == "all":
        conf_run = load_conf_run(cfg_path)
        run_experiments(conf_run)
        conf_analyze = load_conf_analyze(cfg_path)
        analyze_results(conf_analyze)
    else:
        print("Unknown mode: {}".format(mode))
        sys.exit(1)


if __name__ == "__main__":
    main()
