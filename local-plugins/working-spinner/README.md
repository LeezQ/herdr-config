# working-spinner

本地 herdr 插件：侧栏里处于 working 状态的项目用一个转动的 braille spinner（⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏）代替 "working" 文字；其它状态照常显示 idle / done / blocked。

## 原理

herdr 侧栏本身不支持动画，但支持自定义 token（`$name`）。`spinner.py` 常驻后台，每 150ms 读一次 `herdr workspace list`，给每个 workspace 写 token `state`：
- working → 当前 spinner 帧（带 ttl，daemon 挂掉后自动过期）
- 其它状态 → 状态文字本身，只在变化时写一次

`config.toml` 的 `[ui.sidebar.spaces].rows` 第二行用 `"$state"` 代替了内置的 `state_text`，并按 idle / done / blocked / unknown 配了颜色规则，spinner 本身是橙色加粗。

注意 `--seq`：herdr 按 source 持久记录 seq，比历史值小的写入会被静默丢弃，所以脚本用毫秒时间戳当 seq。

## 运行

- herdr server 启动后由 startup hook 自动拉起（有 pid 锁，不会重复）。
- 手动启动（不经过 server 重启）：
  `cd ~/.config/herdr/local-plugins/working-spinner && (nohup python3 spinner.py >/tmp/working-spinner.log 2>&1 &)`
- 停止：`python3 spinner.py --stop`，或 `herdr plugin action invoke local.working-spinner.stop`。
- 注意：`herdr plugin action invoke local.working-spinner.start` 会阻塞（action 同步等待命令退出），不要用它启动。

## 调参

环境变量 `SPINNER_INTERVAL_MS`（默认 150）、`SPINNER_FRAMES`（默认 braille）。想要文字动画可以把帧改成例如 `SPINNER_FRAMES="▁▂▃▄▅▆▇█▇▆▅▄▃▂"`。

## 开销

每 tick 1 + N（N = working 的项目数）次 herdr CLI 调用，每次约 10ms；实测 3 个项目 working 时约 2~3% CPU。
