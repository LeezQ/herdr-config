#!/usr/bin/env bash
# 把当前机器上 herdr 的 GitHub 插件清单导出到 plugins.txt（固定到已安装的 commit）。
# 在某台机器上用 `herdr plugin install` 装了新插件后执行一次，然后提交 git 即可同步到其它机器。
# config.toml 和 local-plugins 本身就在仓库里（软链/直接 link），不需要导出。
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="${REPO_DIR}/plugins.txt"

{
  echo '# GitHub 插件清单：每行 "owner/repo[@ref]"，install.sh 会逐个 herdr plugin install'
  # herdr plugin list 输出示例：- persiyanov.reviewr (reviewr) enabled [github:persiyanov/herdr-reviewr@c49220f...]
  herdr plugin list | sed -n 's/.*\[github:\([^]]*\)\].*/\1/p'
} > "${OUT}"

echo "已写入 ${OUT}："
cat "${OUT}"
