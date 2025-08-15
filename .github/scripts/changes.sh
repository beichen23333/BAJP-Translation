#!/bin/bash
set -euo pipefail

old="$1"
new="$2"

changed="false"
regions=""

# 检查文件是否有变化
if ! cmp -s "$old" "$new"; then
  changed="true"
  
  # 检测各区域的变化
  jp_changed=$(diff "$old" "$new" | grep -qE '^[<>] BA_SERVER_URL=|^[<>] ADDRESSABLE_CATALOG_URL=|^[<>] BA_VERSION_CODE=|^[<>] BA_VERSION_NAME=' && echo "jp")
  cn_changed=$(diff "$old" "$new" | grep -qE '^[<>] BA_SERVER_URL_CN=|^[<>] ADDRESSABLE_CATALOG_URL_CN=|^[<>] BA_VERSION_CODE_CN=|^[<>] BA_VERSION_NAME_CN=' && echo "cn")
  gl_changed=$(diff "$old" "$new" | grep -qE '^[<>] BA_SERVER_URL_GL=|^[<>] ADDRESSABLE_CATALOG_URL_GL=|^[<>] BA_VERSION_CODE_GL=|^[<>] BA_VERSION_NAME_GL=' && echo "gl")
  
  # 构建regions字符串
  [[ -n "$jp_changed" ]] && regions="jp"
  [[ -n "$cn_changed" ]] && regions="${regions:+$regions,}cn"
  [[ -n "$gl_changed" ]] && regions="${regions:+$regions,}gl"
fi

# 输出结果
echo "changed=$changed" >> $GITHUB_OUTPUT
echo "regions=${regions:-none}" >> $GITHUB_OUTPUT
echo "JP=$([[ -n "$jp_changed" ]] && echo "true" || echo "false")" >> $GITHUB_OUTPUT
echo "CN=$([[ -n "$cn_changed" ]] && echo "true" || echo "false")" >> $GITHUB_OUTPUT
echo "GL=$([[ -n "$gl_changed" ]] && echo "true" || echo "false")" >> $GITHUB_OUTPUT
