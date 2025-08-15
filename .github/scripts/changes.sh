set -euo pipefail

old="$1"
new="$2"

changed="false"
regions=""

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
      1|2|3|4) regions="$regions,jp" ;;
      5|6|7|8) regions="$regions,cn" ;;
      9|10|11|12) regions="$regions,gl" ;;
    esac
  done

  # 去重并去掉前导逗号
  regions=$(echo "$regions" | tr ',' '\n' | sort -u | paste -sd ',' - | sed 's/^,//')
fi

# 输出 GitHub Actions 所需的变量
echo "changed=$changed"
echo "regions=$regions"

# 生成布尔值供 repository_dispatch 使用
[[ ",$regions," == *",jp,"* ]] && jp=true || jp=false
[[ ",$regions," == *",cn,"* ]] && cn=true || cn=false
[[ ",$regions," == *",gl,"* ]] && gl=true || gl=false

echo "JP=$jp"
echo "CN=$cn"
echo "GL=$gl"
