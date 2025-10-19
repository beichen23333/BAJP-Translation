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

mkdir -p "./downloads/TableBundles/"

PYTHON_SCRIPT="./get_filenames.py"
TABLE_CATALOG_JSON="./JP/TableBundles/TableCatalog.json"

if [ ! -f "$TABLE_CATALOG_JSON" ]; then
    echo "Error: TableCatalog.json not found at $TABLE_CATALOG_JSON"
    exit 1
fi

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Python script $PYTHON_SCRIPT not found"
    exit 1
fi

python3 "$PYTHON_SCRIPT" | while read -r filename; do
    download_url="${ADDRESSABLE_CATALOG_URL}/TableBundles/${filename}"

    output_file="./downloads/TableBundles/${filename}"

    download_file "$download_url" "$output_file"
done
