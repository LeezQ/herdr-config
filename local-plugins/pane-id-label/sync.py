#!/usr/bin/env python3
"""pane-id-label 同步脚本。

每次运行做一次全量对账：
1. 通过 herdr CLI 拉取所有 pane；
2. 为每个 pane 生成标签 "<pane_id> · <agent>"（无 agent 时只有 pane_id）；
3. 标签与当前不一致时调用 `herdr pane rename` 写回。

重命名成相同标签是幂等的，所以 startup / action / event 多次触发互不影响。
任何一步失败都打印到 stderr 并以非零退出，herdr 会记录到插件日志。
"""
import json
import os
import subprocess
import sys

# herdr 注入的二进制路径；本地手动运行时退回 PATH 里的 herdr
HERDR = os.environ.get("HERDR_BIN_PATH", "herdr")
SEP = " · "


def run(*args: str) -> str:
    """执行 herdr 子命令并返回 stdout，失败时抛出异常。"""
    proc = subprocess.run([HERDR, *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"herdr {' '.join(args)} 失败: {proc.stderr.strip()}")
    return proc.stdout


def desired_label(pane: dict) -> str:
    """根据 pane 信息生成期望的边框标签。"""
    pane_id = pane["pane_id"]
    agent = pane.get("agent")
    return f"{pane_id}{SEP}{agent}" if agent else pane_id


def main() -> int:
    try:
        panes = json.loads(run("pane", "list"))["result"]["panes"]
    except Exception as exc:  # noqa: BLE001 - 统一记录后退出
        print(f"pane-id-label: 读取 pane 列表失败: {exc}", file=sys.stderr)
        return 1

    failures = 0
    for pane in panes:
        label = desired_label(pane)
        # 已经是期望标签就跳过，避免无谓的 rename 请求
        if pane.get("label") == label:
            continue
        try:
            run("pane", "rename", pane["pane_id"], label)
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"pane-id-label: 重命名 {pane['pane_id']} 失败: {exc}", file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
