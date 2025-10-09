# registry/registry.py
from pathlib import Path
import yaml
from jinja2 import Template
from jinja2.sandbox import SandboxedEnvironment

class PromptRegistry:
    def __init__(self, folder: str):
        self.folder = Path(folder)
        self._env = SandboxedEnvironment()
        self._prompts = {}  # {version: {name: template}}
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
        return list(self._prompts[version].keys())

    def get(self, name: str, version: str):
        return self._prompts[version][name]["template"]

    def render(self, name: str, version: str, **vars):
        tmpl = self._env.from_string(self.get(name, version))
        return tmpl.render(**vars)
