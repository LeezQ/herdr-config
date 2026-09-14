# pane-id-label

本地 herdr 插件：把每个 pane 的 id 显示在 pane 边框上，格式 `wM:p3 · claude`（无 agent 时只有 `wM:p3`）。
目的是让任意 pane 里的人或 agent 都能一眼看到目标 pane id，直接用 `herdr pane run <id> ...` / `herdr agent prompt <id> ...` 互相操作。

## 触发时机

- herdr server 启动、会话恢复后（startup）
- 新建 pane、移动 pane、检测到 agent（事件）
- 手动：`herdr plugin action invoke local.pane-id-label.sync`

## 配套配置

`~/.config/herdr/config.toml` 里 `pane_borders = "always"` + `pane_outer_borders = true`，否则只有分屏 pane 才有边框可显示标签。

## 注意

- 标签是通过 `herdr pane rename` 写的，属于"手动标签"，会覆盖 herdr 自带的 agent 边框标签，所以脚本自己把 agent 名拼进去了。
- 想给某个 pane 起别的名字，直接 rename 即可；下一次同步事件会把它改回 id 格式。想永久保留自定义名，禁用插件：`herdr plugin disable local.pane-id-label`。
- 卸载：`herdr plugin unlink local.pane-id-label`，然后 `herdr pane rename <id> --clear` 清标签。
