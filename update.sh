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
        http_status=$(curl -s -w "%{http_code}" -o "$output" "$url")

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

    echo "错误: 无法下载文件，请检查网络或 URL 是否正确: $url"
    return 1
}


download_file "${ADDRESSABLE_CATALOG_URL}/TableBundles/TableCatalog.bytes" "./downloads/TableBundles/TableCatalog.bytes"
download_file "${ADDRESSABLE_CATALOG_URL}/MediaResources/Catalog/MediaCatalog.bytes" "./downloads/MediaResources/Catalog/MediaCatalog.bytes"
download_file "${ADDRESSABLE_CATALOG_URL}/TableBundles/Excel.zip" "./downloads/TableBundles/Excel.zip"
download_file "${ADDRESSABLE_CATALOG_URL}/TableBundles/ExcelDB.db" "./downloads/TableBundles/ExcelDB.db"

chmod +x ./MemoryPackRepacker

./MemoryPackRepacker deserialize media ./downloads/MediaResources/Catalog/MediaCatalog.bytes MediaCatalog.json
./MemoryPackRepacker deserialize table ./downloads/TableBundles/TableCatalog.bytes TableCatalog.json
