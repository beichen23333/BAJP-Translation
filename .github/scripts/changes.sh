#!/bin/bash
set -euo pipefail

old="$1"
new="$2"

changed="false"
declare -A region_map=([jp]=false [cn]=false [gl]=false)

# 只要文件不同就标记为有变化
if ! cmp -s "$old" "$new"; then
  changed="true"
  # 取出新增/修改行的行号
  mapfile -t lines < <(
    diff -u0 "$old" "$new" \
    | grep -E '^\+[^+]' \
    | sed 's/^+//' \
    | nl -ba \
    | awk '{print $1}'
  )

  # 根据行号映射区域
  for ln in "${lines[@]}"; do
    case $ln in
      1|2|3|4) region_map[jp]=true ;;
      5|6|7|8) region_map[cn]=true ;;
      9|10|11|12) region_map[gl]=true ;;
    esac
  done
fi

# 构建regions字符串
regions=""
for region in "${!region_map[@]}"; do
  if ${region_map[$region]}; then
    regions="${regions:+$regions,}$region"
  fi
done

# 输出 GitHub Actions 所需的变量
echo "changed=$changed" >> $GITHUB_OUTPUT
echo "regions=${regions:-none}" >> $GITHUB_OUTPUT
echo "JP=${region_map[jp]}" >> $GITHUB_OUTPUT
echo "CN=${region_map[cn]}" >> $GITHUB_OUTPUT
echo "GL=${region_map[gl]}" >> $GITHUB_OUTPUT
