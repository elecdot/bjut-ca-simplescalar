# run.py
#
# 负责调用 sim-cache 跑实验（base/full-assoc/ideal 三种变体）

import sys
import os
import math
import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def split_opts(opts):
    tokens = []
    for opt in opts:
        tokens.extend(shlex.split(opt))
    return tokens


def extract_dl1(tokens):
    for i in range(len(tokens) - 1):
        if tokens[i] == "-cache:dl1":
            return i, tokens[i + 1]
    return None, None


def build_full_assoc_same_capacity(dl1_cfg):
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


def run_single_sim(sim_bin, base_opts, program_path, program_args,
                   extra_opts, out_path):
    ensure_dir(os.path.dirname(out_path))
    cmd = [sim_bin] + extra_opts + base_opts + [program_path] + program_args
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# CMD: " + " ".join(cmd) + "\n\n")
        try:
            ret = subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT)
            if ret != 0:
                f.write("\n# EXITCODE: {}\n".format(ret))
        except Exception as e:
            f.write("\n# ERROR: {}\n".format(e))


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
            if not any(opt.startswith("-cache:dl2") for opt in extra_opts):
                extra_opts = dl2_tokens + extra_opts
            out_dir = os.path.join(out_root, exp_name)
            base_out = os.path.join(out_dir, "{}.out".format(cfg_id))

            jobs.append({
                "exp_name": exp_name,
                "cfg_id": cfg_id,
                "variant": "base",
                "cmd_args": {
                    "sim_bin": sim_bin,
                    "base_opts": base_opts,
                    "program_path": prog_path,
                    "program_args": prog_args,
                    "extra_opts": extra_opts,
                    "out_path": base_out,
                }
            })

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


def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py <config.yaml>")
        sys.exit(1)
    cfg_path = sys.argv[1]
    conf = load_config(cfg_path)
    run_experiments(conf)


if __name__ == "__main__":
    main()
