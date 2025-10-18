# registry/registry.py
from pathlib import Path
import yaml
from jinja2.sandbox import SandboxedEnvironment

class PromptRegistry:
    def __init__(self, folder: str):
        self.folder = Path(folder)
        # 初始化 Jinja2 環境（sandbox 版本比較安全）
        self._env = SandboxedEnvironment(autoescape=False)
        self._prompts = {}  # {version: {name: {template: str}}}
        self._load_all()

    def _load_all(self):
        for file in sorted(self.folder.glob("prompts_v*.yaml")):
            version = file.stem.replace("prompts_", "")
            with open(file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self._prompts[version] = data.get("prompts", {})

    def list_versions(self):
        return sorted(self._prompts.keys())

    def list_prompts(self, version: str):
        if version not in self._prompts:
            raise KeyError(f"未知版本 {version}，可用版本: {self.list_versions()}")
        return list(self._prompts[version].keys())

    def get(self, name: str, version: str):
        try:
            return self._prompts[version][name]["template"]
        except KeyError:
            raise KeyError(f"找不到 prompt: {name} (版本 {version})")

    def render(self, name: str, version: str, **kwargs):
        tmpl = self._env.from_string(self.get(name, version))
        return tmpl.render(**kwargs)
