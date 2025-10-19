export $(grep -v '^#' ba.env | xargs)

download_file() {
    local url=$1
    local output=$2
    local max_retries=3
    local retry_count=0

    if [ -f "$output" ]; then
        echo "文件已存在，跳过下载: $output"
        return
    fi

    local dir=$(dirname "$output")
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
    fi

    while [ $retry_count -lt $max_retries ]; do
        echo "正在下载: $url (尝试 $((retry_count + 1))/$max_retries)"
        http_status=$(curl -A "UnityWebRequest" -s -w "%{http_code}" -o "$output" "$url")

        if [ "$http_status" -eq 200 ] && [ -s "$output" ]; then
            echo "下载成功: $output"
            return 0
        else
            echo "下载失败 (HTTP $http_status): $url"
            rm -f "$output"
            retry_count=$((retry_count + 1))
            sleep 2
        fi
    done

    echo "错误: 无法下载文件，请检查网络或 URL: $url"
    return 1
}

echo "===== 开始下载 TableBundles 资源 ====="
mkdir -p "./downloads/TableBundles/"
TABLE_CATALOG_JSON="./JP/TableBundles/TableCatalog.json"

if [ ! -f "$TABLE_CATALOG_JSON" ]; then
    echo "错误: 未找到 TableCatalog.json: $TABLE_CATALOG_JSON"
    exit 1
fi

python3 "./get_filenames.py" "$TABLE_CATALOG_JSON" | while read -r filename; do
    download_url="${ADDRESSABLE_CATALOG_URL}/TableBundles/${filename}"
    output_file="./downloads/TableBundles/${filename}"
    download_file "$download_url" "$output_file"
done

echo "===== 开始下载 MediaResources 资源 ====="
mkdir -p "./downloads/MediaResources/"
MEDIA_CATALOG_JSON="./JP/MediaResources/Catalog/MediaCatalog.json"

if [ ! -f "$MEDIA_CATALOG_JSON" ]; then
    echo "错误: 未找到 MediaCatalog.json: $MEDIA_CATALOG_JSON"
    exit 1
fi

python3 "./get_filenames.py" "$MEDIA_CATALOG_JSON" | while read -r path; do
    download_url="${ADDRESSABLE_CATALOG_URL}/MediaResources/${path}"
    output_file="./downloads/MediaResources/${path}"
    download_file "$download_url" "$output_file"
done

echo "===== 所有资源下载完成 ====="
