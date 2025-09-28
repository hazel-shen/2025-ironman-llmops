from pathlib import Path
from datetime import datetime
from prefect import flow, task, get_run_logger
from dotenv import load_dotenv

from utils.cleaning import clean_text
from utils.chunking import chunk_text
from utils.embeddings import embed_texts, save_vector_index

load_dotenv()

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "worker_manual.txt"
OUT_PATH  = Path(__file__).resolve().parents[1] / "data" / "vector_index.json"

@task(retries=3, retry_delay_seconds=10)
def fetch_data(path: Path) -> str:
    logger = get_run_logger()
    logger.info(f"Reading file: {path}")
    return path.read_text(encoding="utf-8")

@task
def process_text(raw: str) -> list[str]:
    cleaned = clean_text(raw)
    chunks = chunk_text(cleaned, max_chars=200, overlap=40)
    return chunks

@task
def build_embeddings(chunks: list[str]) -> list[list[float]]:
    return embed_texts(chunks)

@task
def upload(chunks: list[str], vectors: list[list[float]], out_path: Path) -> None:
    meta = {
        "source": str(DATA_PATH.name),
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "model": "text-embedding-3-small or FAKE",
    }
    save_vector_index(chunks, vectors, str(out_path), meta=meta)

@flow(name="daily_rag_update")
def daily_pipeline():
    raw = fetch_data(DATA_PATH)
    chunks = process_text(raw)
    vectors = build_embeddings(chunks)
    upload(chunks, vectors, OUT_PATH)

if __name__ == "__main__":
    daily_pipeline()
