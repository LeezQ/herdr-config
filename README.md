# herdr-config

我的 [herdr](https://herdr.dev) 配置，用 git 在多台电脑之间同步。

## 目录结构

| 路径 | 说明 |
| --- | --- |
| `config.toml` | 主配置，软链到 `~/.config/herdr/config.toml` |
| `local-plugins/pane-id-label/` | 本地插件：pane 边框显示 `wM:p3 · claude` |
| `local-plugins/working-spinner/` | 本地插件：侧栏 working 状态显示转动 spinner（写 `$state` token） |
| `plugins.txt` | GitHub 插件清单（固定 commit），当前只有 `persiyanov/herdr-reviewr` |
| `install.sh` | 新机器一键部署 / 老机器更新后重跑 |
| `export.sh` | 装了新 GitHub 插件后，重新生成 `plugins.txt` |

**不同步的内容**（机器相关或运行时产物）：`session.json`、`*.log`、`*.sock`、`plugins.json`（含绝对路径，由 herdr 自动生成）、`plugins/github/`（由 `install.sh` 重新安装）、`release-notes.json`。

## 新电脑部署

```bash
brew install herdr            # 需要 python3、git
git clone <你的仓库地址> ~/Code/herdr-config
~/Code/herdr-config/install.sh
```

然后重启 herdr server，让插件的 startup 命令生效。

> Ghostty 需要开启 `macos-option-as-alt = true`，`alt+1..9` 切换 workspace 才能用。

## 日常同步

- **改了 `config.toml` / 本地插件**：直接在仓库里改（`~/.config/herdr/config.toml` 就是软链），`git commit && git push`；其它机器 `git pull` 后执行 `herdr server reload-config`。
- **装了新 GitHub 插件**：`./export.sh` 更新 `plugins.txt` → 提交推送；其它机器 `git pull && ./install.sh`。
- **新增本地插件**：放到 `local-plugins/<name>/`，其它机器 `git pull && ./install.sh`。
