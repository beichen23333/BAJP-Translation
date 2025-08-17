set -euo pipefail

ENV_FILE="${1:-ba.env}"

# 读取变量（去掉引号）
get_var() {
  grep -E "^$1=" "$ENV_FILE" | cut -d '=' -f2- | sed -e 's/^"//' -e 's/"$//' | tr -d "'"
}

# ===== 日服 =====
ADDRESSABLE_CATALOG_URL=$(get_var "ADDRESSABLE_CATALOG_URL")
BA_VERSION_CODE=$(get_var "BA_VERSION_CODE")
BA_VERSION_NAME=$(get_var "BA_VERSION_NAME")
last_seg() { basename "$1"; }
BUILD_VERSION="${BA_VERSION_NAME}-${BA_VERSION_CODE}($(last_seg "$ADDRESSABLE_CATALOG_URL"))"

# ===== 国服 =====
BA_SERVER_URL_CN=$(get_var "BA_SERVER_URL_CN")
BA_VERSION_CODE_CN=$(get_var "BA_VERSION_CODE_CN")
BA_VERSION_NAME_CN=$(get_var "BA_VERSION_NAME_CN")
BUILD_VERSION_CN="${BA_VERSION_NAME_CN}-${BA_VERSION_CODE_CN}($(basename "$(dirname "$BA_SERVER_URL_CN")"))"

# ===== 国际服 =====
ADDRESSABLE_CATALOG_URL_GL=$(get_var "ADDRESSABLE_CATALOG_URL_GL")
BA_VERSION_CODE_GL=$(get_var "BA_VERSION_CODE_GL")
BA_VERSION_NAME_GL=$(get_var "BA_VERSION_NAME_GL")
BUILD_VERSION_GL="${BA_VERSION_NAME_GL}-${BA_VERSION_CODE_GL}($(last_seg "$ADDRESSABLE_CATALOG_URL_GL"))"

# 输出给 GitHub Actions
{
  echo "BA_VERSION_NAME=$BUILD_VERSION"
  echo "BA_VERSION_NAME_CN=$BUILD_VERSION_CN"
  echo "BA_VERSION_NAME_GL=$BUILD_VERSION_GL"
} >> "$GITHUB_OUTPUT"
