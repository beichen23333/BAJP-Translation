import os
from os import path
from xtractor.bundle import BundleExtractor

# 设置路径
input_file = "/storage/emulated/0/uis-01_common-27_eventcontent-playguide-_mxload-textures-2025-07-02_assets_all_17533797.bundle"
output_dir = "/storage/emulated/0/extracted_results"  # 你可以修改为想要的输出目录

# 确保输出目录存在
os.makedirs(output_dir, exist_ok=True)

# 创建BundleExtractor实例
extractor = BundleExtractor(
    EXTRACT_DIR=output_dir,
    BUNDLE_FOLDER=path.dirname(input_file)  # 使用输入文件所在目录作为BUNDLE_FOLDER
)

# 提取bundle文件
print(f"开始解密文件: {input_file}")
extractor.extract_bundle(
    res_path=input_file,
    extract_types=None  # 使用预定义的主要提取类型
)
print("解密完成！提取的文件保存在:", output_dir)
