# version_check.py
import yaml

def get_version(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("version", "0.0.0")

def compare_versions(old_v: str, new_v: str) -> bool:
    """若版本號升級，回傳 True"""
    def parse(v): return list(map(int, v.split(".")))
    return parse(new_v) > parse(old_v)

old_file = "faq_v1.yaml"
new_file = "faq_v2.yaml"

old_version = get_version(old_file)
new_version = get_version(new_file)

print(f"舊版: {old_version}, 新版: {new_version}")
if compare_versions(old_version, new_version):
    print("⚠️ 偵測到新版本，需要更新知識庫！")
else:
    print("✅ 沒有新版本，無需更新。")