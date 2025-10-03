set -euo pipefail

ENV_FILE="${1:-ba.env}"

get_var() {
  grep -E "^$1=" "$ENV_FILE" | cut -d '=' -f2- | sed -e 's/^"//' -e 's/"$//' | tr -d "'"
}

ADDRESSABLE_CATALOG_URL=$(get_var "ADDRESSABLE_CATALOG_URL")
BA_VERSION_CODE=$(get_var "BA_VERSION_CODE")
BA_VERSION_NAME=$(get_var "BA_VERSION_NAME")
last_seg() { basename "$1"; }
BUILD_VERSION="${BA_VERSION_NAME}-${BA_VERSION_CODE}($(last_seg "$ADDRESSABLE_CATALOG_URL"))"

{
  echo "BA_VERSION_NAME=$BUILD_VERSION"
} >> "$GITHUB_OUTPUT"
