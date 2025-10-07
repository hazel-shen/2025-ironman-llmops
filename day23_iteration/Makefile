SHELL := bash

ENV ?= rag-inc-demo
REGISTRY_URL ?= http://localhost:8000
MODEL_NAME ?= faq-bot

DOCS_DIR := docs
JSONL := $(DOCS_DIR)/new_kb.jsonl

.PHONY: env init add search pack register all sample-jsonl add-jsonl import

env:
	conda env create -f environment.yaml || true
	@echo "Run: conda activate $(ENV)"

init:
	mkdir -p data scripts
	[ -f data/kb.jsonl ] || : > data/kb.jsonl
	[ -f data/mappings.json ] || printf '%s\n' '{"rowid_to_doc_id":{}}' > data/mappings.json
	[ -f data/kb_meta.json ] || printf '%s\n' '{"kb_version":0,"doc_count":0,"dim":384,"model":"sentence-transformers/all-MiniLM-L6-v2"}' > data/kb_meta.json
	@echo "✅ 初始化完成"

add:
	python scripts/add_docs.py --jsonl docs/examples_10.jsonl

search:
	python scripts/search.py "$(q)" --k $(k)

pack:
	python scripts/pack_and_register.py --pack-only --name $(MODEL_NAME) --registry $(REGISTRY_URL)

register:
	python scripts/pack_and_register.py --name $(MODEL_NAME) --registry $(REGISTRY_URL) --auto-unique


# --- 產生後立即匯入到 KB ---
add-jsonl: sample-jsonl
	python scripts/add_docs.py --jsonl $(JSONL)

# 匯入任意 JSONL（用法：make import FILE=path/to/file.jsonl）
import:
	@if [ -z "$(FILE)" ]; then echo "用法：make import FILE=path/to/file.jsonl"; exit 2; fi
	python scripts/add_docs.py --jsonl "$(FILE)"

all: add search register


check-model:
	@code=$$(curl -s -o /dev/null -w "%{http_code}" $(REGISTRY_URL)/models/$(MODEL_NAME)); \
	if [ "$$code" = "200" ]; then \
	  echo "✅ model '$(MODEL_NAME)' 存在"; \
	else \
	  echo "❌ 找不到 model '$(MODEL_NAME)'（HTTP $$code）"; \
	fi

list-models:
	curl -s $(REGISTRY_URL)/models | jq

list-versions:
	curl -s $(REGISTRY_URL)/models/$(MODEL_NAME)/versions | jq

# === Fine-tuning（可選）===
OPENAI_MODEL ?= gpt-4o-mini-2024-07-18
FT_OUT := scenarios/open_ai/train_new.jsonl
FT_OUT_DIR := $(dir $(FT_OUT))

ft-export:
	mkdir -p $(FT_OUT_DIR)
	python scripts/ft_prep_from_kb.py --out $(FT_OUT)

# 匯出整個 KB（不看游標）
ft-export-all:
	mkdir -p $(FT_OUT_DIR)
	python scripts/ft_prep_from_kb.py --out $(FT_OUT) --force-all

# 匯出最近 N 筆（用法：make ft-export-last N=30）
ft-export-last:
	mkdir -p $(FT_OUT_DIR)
	@if [ -z "$(N)" ]; then echo "用法：make ft-export-last N=數量"; exit 2; fi
	python scripts/ft_prep_from_kb.py --out $(FT_OUT) --since $(N)

# 重置游標（下次 ft-export 會從頭抓）
ft-reset:
	rm -f data/ft_cursor.json

ft-run: ft-export
	python scripts/openai_finetune.py run --model $(OPENAI_MODEL) --train_jsonl $(FT_OUT)

ft-run-nowait: ft-export
	python scripts/openai_finetune.py run --model $(OPENAI_MODEL) --train_jsonl $(FT_OUT) --no-wait

ft-status:
	@if [ -z "$(JOB)" ]; then echo "用法：make ft-status JOB=ftjob_xxx"; exit 2; fi
	python scripts/openai_finetune.py status --job $(JOB)

ft-test:
	python scripts/test_ft_model.py