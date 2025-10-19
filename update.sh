#!/bin/bash

export $(grep -v '^#' ba.env | xargs)

download_file() {
    local url=$1
    local output=$2

    if [ -f "$output" ]; then
        echo "File already exists, skipping download: $output"
        return
    fi

    local dir=$(dirname "$output")
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
    fi

    while true; do
        echo "Downloading: $url"
        http_status=$(curl -s -w "%{http_code}" -o "$output" "$url")

        if [ "$http_status" -eq 200 ] && [ -s "$output" ]; then
            echo "Downloaded: $output"
            break
        else
            echo "Download failed with status $http_status or file is empty: $url"
            exit 1
        fi
    done
}


download_file "${ADDRESSABLE_CATALOG_URL}/TableBundles/TableCatalog.bytes" "./downloads/TableBundles/TableCatalog.bytes"
download_file "${ADDRESSABLE_CATALOG_URL}/MediaResources/Catalog/MediaCatalog.bytes" "./downloads/MediaResources/Catalog/MediaCatalog.bytes"
download_file "${ADDRESSABLE_CATALOG_URL}/TableBundles/Excel.zip" "./downloads/TableBundles/Excel.zip"
download_file "${ADDRESSABLE_CATALOG_URL}/TableBundles/ExcelDB.db" "./downloads/TableBundles/ExcelDB.db"

chmod +x ./MemoryPackRepacker

./MemoryPackRepacker deserialize media ./downloads/MediaResources/Catalog/MediaCatalog.bytes ./JP/MediaResources/Catalog/MediaCatalog.json
./MemoryPackRepacker deserialize table ./downloads/TableBundles/TableCatalog.bytes ./JP/TableBundles/TableCatalog.json
