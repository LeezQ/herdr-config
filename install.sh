#!/usr/bin/env bash
# herdr 配置一键部署脚本（macOS / Linux）
#
# 做的事：
#   1. 把本仓库的 config.toml 软链到 ~/.config/herdr/config.toml（已有的非软链文件先备份）
#   2. 用 `herdr plugin link` 链接 local-plugins/ 下的每个本地插件（直接指向本仓库，改完 git pull 即生效）
#   3. 按 plugins.txt 安装 GitHub 插件（固定到 commit，保证多台机器版本一致）
#   4. 热重载配置
#
# 可重复执行：已链接/已安装的插件会被跳过。
set -euo pipefail

# 仓库根目录（脚本所在目录），不依赖执行时的 cwd
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERDR_DIR="${HOME}/.config/herdr"

log() { printf '\033[1;34m[herdr-config]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[herdr-config] ERROR:\033[0m %s\n' "$*" >&2; }

# ---- 0. 前置检查 ----
if ! command -v herdr >/dev/null 2>&1; then
  err "未找到 herdr，请先安装：brew install herdr"
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  err "本地插件依赖 python3，请先安装"
  exit 1
fi
mkdir -p "${HERDR_DIR}"

# ---- 1. 软链 config.toml ----
TARGET="${HERDR_DIR}/config.toml"
if [ -L "${TARGET}" ]; then
  log "config.toml 已是软链 -> $(readlink "${TARGET}")，重新指向本仓库"
  ln -sfn "${REPO_DIR}/config.toml" "${TARGET}"
else
  if [ -e "${TARGET}" ]; then
    BACKUP="${TARGET}.bak.$(date +%Y%m%d%H%M%S)"
    log "备份已有 config.toml -> ${BACKUP}"
    mv "${TARGET}" "${BACKUP}"
  fi
  ln -s "${REPO_DIR}/config.toml" "${TARGET}"
  log "已软链 config.toml"
fi

# 当前已安装插件列表，用于跳过重复安装
INSTALLED="$(herdr plugin list 2>/dev/null || true)"

# ---- 2. 链接本地插件 ----
for manifest in "${REPO_DIR}"/local-plugins/*/herdr-plugin.toml; do
  [ -e "${manifest}" ] || continue
  plugin_dir="$(dirname "${manifest}")"
  # 从 manifest 里读插件 id，例如 local.pane-id-label
  plugin_id="$(sed -n 's/^id *= *"\(.*\)"/\1/p' "${manifest}" | head -n1)"
  if printf '%s' "${INSTALLED}" | grep -q -- "- ${plugin_id} "; then
    log "本地插件 ${plugin_id} 已存在，跳过（路径不对可先 herdr plugin unlink ${plugin_id}）"
    continue
  fi
  log "链接本地插件 ${plugin_id} (${plugin_dir})"
  # 注意：herdr 0.9.0 的 link 虽在 help 里列出 --enabled，实际会报 unknown option；默认就是启用状态
  herdr plugin link "${plugin_dir}" || err "链接 ${plugin_id} 失败"
done

# ---- 3. 安装 GitHub 插件 ----
while IFS= read -r line || [ -n "${line}" ]; do
  # 跳过空行和注释
  line="${line%%#*}"
  line="$(printf '%s' "${line}" | tr -d '[:space:]')"
  [ -n "${line}" ] || continue

  repo="${line%%@*}"
  ref=""
  [ "${line}" != "${repo}" ] && ref="${line#*@}"

  # 插件 id 形如 owner.name（仓库名去掉 herdr- 前缀），用仓库 owner/repo 在 list 输出里匹配更稳妥
  if printf '%s' "${INSTALLED}" | grep -q "github:${repo}@"; then
    log "GitHub 插件 ${repo} 已安装，跳过"
    continue
  fi
  log "安装 GitHub 插件 ${repo}${ref:+ @ ${ref}}"
  if [ -n "${ref}" ]; then
    herdr plugin install -y --ref "${ref}" "${repo}" || err "安装 ${repo} 失败"
  else
    herdr plugin install -y "${repo}" || err "安装 ${repo} 失败"
  fi
done < "${REPO_DIR}/plugins.txt"

# ---- 4. 热重载 ----
if herdr server reload-config >/dev/null 2>&1; then
  log "已热重载配置。插件的 startup 命令需要重启 herdr server 才会执行。"
else
  log "herdr server 未运行，下次启动 herdr 时自动生效。"
fi

log "完成 ✅"
