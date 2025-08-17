#!/bin/bash
set -euo pipefail

old="$1"
new="$2"

# 检查文件是否存在
if [[ ! -f "$old" || ! -f "$new" ]]; then
  echo "Error: 文件不存在" >&2
  exit 1
fi

changed="false"
regions=""

# 检查文件是否有变化
if ! cmp -s "$old" "$new"; then
  changed="true"
  
  # 检测各区域的变化（使用临时文件避免管道错误）
  tmp_diff=$(mktemp)
  diff "$old" "$new" > "$tmp_diff" || true
  
  # 检测各区域变化
  jp_changed=$(grep -qE '^[<>] (BA_SERVER_URL|ADDRESSABLE_CATALOG_URL|BA_VERSION_CODE|BA_VERSION_NAME)=' "$tmp_diff" && echo "jp" || true)
  cn_changed=$(grep -qE '^[<>] (BA_SERVER_URL_CN|ADDRESSABLE_CATALOG_URL_CN|BA_VERSION_CODE_CN|BA_VERSION_NAME_CN)=' "$tmp_diff" && echo "cn" || true)
  gl_changed=$(grep -qE '^[<>] (BA_SERVER_URL_GL|ADDRESSABLE_CATALOG_URL_GL|BA_VERSION_CODE_GL|BA_VERSION_NAME_GL)=' "$tmp_diff" && echo "gl" || true)
  
  rm "$tmp_diff"
  
  # 构建regions字符串
  [[ -n "$jp_changed" ]] && regions="jp"
  [[ -n "$cn_changed" ]] && regions="${regions:+$regions,}cn"
  [[ -n "$gl_changed" ]] && regions="${regions:+$regions,}gl"
fi

# 输出结果
{
  echo "changed=$changed"
  echo "regions=${regions:-none}"
  echo "JP=$([[ -n "$jp_changed" ]] && echo "true" || echo "false")"
  echo "CN=$([[ -n "$cn_changed" ]] && echo "true" || echo "false")"
  echo "GL=$([[ -n "$gl_changed" ]] && echo "true" || echo "false")"
} >> "$GITHUB_OUTPUT"
