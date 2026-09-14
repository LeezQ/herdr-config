#!/usr/bin/env python3
"""working-spinner 常驻进程。

每个 tick：
1. `herdr workspace list` 读取每个 workspace 汇总后的 agent 状态；
2. 给每个 workspace 写入自定义 token `state`：
   - working  → 当前 spinner 帧（带 ttl，daemon 挂了会自动过期）
   - 其它状态 → 状态文字本身（idle / done / blocked / unknown），只在变化时写一次
   侧栏行布局用 "$state" 代替内置的 state_text，这样 working 时只看到动画、没有文字。
3. 退出时把正在转的 workspace 写回静态 "working"，避免状态栏空掉。

环境变量（可选）：
  SPINNER_INTERVAL_MS  帧间隔，默认 150
  SPINNER_FRAMES       帧序列，默认 braille 圆点
用 --stop 参数运行则结束正在跑的实例。
"""
import json
import os
import signal
import subprocess
import sys
import time

HERDR = os.environ.get("HERDR_BIN_PATH", "herdr")
SOURCE = "local.working-spinner"
INTERVAL = int(os.environ.get("SPINNER_INTERVAL_MS", "150")) / 1000
FRAMES = os.environ.get("SPINNER_FRAMES", "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
# token 存活时间要明显大于一个 tick，否则帧之间会闪一下
TTL_MS = max(int(INTERVAL * 1000) * 6, 1000)
STATE_DIR = os.environ.get("HERDR_PLUGIN_STATE_DIR") or os.path.expanduser(
    "~/.local/state/herdr/plugins/local.working-spinner"
)
PID_FILE = os.path.join(STATE_DIR, "spinner.pid")
MAX_CONSECUTIVE_FAILURES = 20  # server 没了就退出，别一直空转


def log(msg: str) -> None:
    print(f"working-spinner: {msg}", file=sys.stderr, flush=True)


def herdr(*args: str) -> str:
    proc = subprocess.run([HERDR, *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"herdr {' '.join(args)} 失败: {proc.stderr.strip()}")
    return proc.stdout


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_pid() -> int | None:
    try:
        with open(PID_FILE) as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return None


def stop_running() -> int:
    pid = read_pid()
    if pid and pid_alive(pid):
        os.kill(pid, signal.SIGTERM)
        log(f"已停止 pid={pid}")
    else:
        log("没有正在运行的实例")
    try:
        os.remove(PID_FILE)
    except OSError:
        pass
    return 0


def acquire_lock() -> bool:
    os.makedirs(STATE_DIR, exist_ok=True)
    pid = read_pid()
    if pid and pid != os.getpid() and pid_alive(pid):
        log(f"已有实例在运行 pid={pid}，本次退出")
        return False
    with open(PID_FILE, "w") as fh:
        fh.write(str(os.getpid()))
    return True


def workspace_states() -> dict[str, str | None]:
    """返回 {workspace_id: agent_status}，没有 agent 的 workspace 为 None。"""
    workspaces = json.loads(herdr("workspace", "list"))["result"]["workspaces"]
    return {w["workspace_id"]: w.get("agent_status") for w in workspaces}


def next_seq() -> int:
    """herdr 按 source 记录 seq，比历史值小的写入会被静默丢弃；
    用毫秒时间戳保证 daemon 重启后仍然单调递增。"""
    return time.time_ns() // 1_000_000


def set_token(ws: str, value: str, seq: int, ttl_ms: int | None = None) -> None:
    args = ["workspace", "report-metadata", ws, "--source", SOURCE,
            "--token", f"state={value}", "--seq", str(seq)]
    if ttl_ms:
        args += ["--ttl-ms", str(ttl_ms)]
    herdr(*args)


def clear_token(ws: str) -> None:
    herdr("workspace", "report-metadata", ws, "--source", SOURCE, "--clear-token", "state")


def main() -> int:
    if "--stop" in sys.argv:
        return stop_running()
    if not acquire_lock():
        return 0

    written: dict[str, str] = {}  # 每个 workspace 上一次写入的静态文字（spinner 帧不记）
    spinning: set[str] = set()
    seq = next_seq()
    failures = 0
    frame_index = 0

    def cleanup(*_: object) -> None:
        # 退出前把正在转的 workspace 写回静态文字，其它 workspace 的文字保留
        for ws in list(spinning):
            try:
                set_token(ws, "working", next_seq())
            except Exception as exc:  # noqa: BLE001
                log(f"收尾写入 {ws} 失败: {exc}")
        try:
            if read_pid() == os.getpid():
                os.remove(PID_FILE)
        except OSError:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)
    log(f"启动 pid={os.getpid()} interval={INTERVAL}s frames={FRAMES}")

    while True:
        try:
            states = workspace_states()
            failures = 0
        except Exception as exc:  # noqa: BLE001
            failures += 1
            log(f"读取 workspace 列表失败({failures}/{MAX_CONSECUTIVE_FAILURES}): {exc}")
            if failures >= MAX_CONSECUTIVE_FAILURES:
                log("herdr server 似乎已停止，退出")
                cleanup()
            time.sleep(1)
            continue

        frame = FRAMES[frame_index % len(FRAMES)]
        frame_index += 1
        seq = next_seq()
        now_spinning: set[str] = set()
        for ws, status in states.items():
            try:
                if status == "working":
                    # 动画帧每 tick 都写，带 ttl
                    set_token(ws, frame, seq, TTL_MS)
                    now_spinning.add(ws)
                    written.pop(ws, None)
                elif status:
                    # 静态文字只在变化时写一次，不带 ttl
                    if written.get(ws) != status:
                        set_token(ws, status, seq)
                        written[ws] = status
                elif ws in written or ws in spinning:
                    clear_token(ws)
                    written.pop(ws, None)
            except Exception as exc:  # noqa: BLE001
                log(f"写入 {ws} 失败: {exc}")
        # 已关闭的 workspace 从记录里去掉
        for ws in list(written):
            if ws not in states:
                written.pop(ws, None)
        spinning = now_spinning
        time.sleep(INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
