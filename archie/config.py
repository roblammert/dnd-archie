from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False)

@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    source_pdf: Path = ROOT / "sources" / "SRD_CC_v5.2.1.pdf"
    manifest: Path = ROOT / "sources" / "manifest.json"
    database: Path = ROOT / "data" / "index" / "srd.sqlite3"
    characters: Path = ROOT / "data" / "characters"
    llm_base_url: str = os.getenv("ARCHIE_LLM_BASE_URL", "http://127.0.0.1:8080/v1")
    llm_model: str = os.getenv("ARCHIE_LLM_MODEL", "gemma4-12b-it-q4_k_m")
    llm_timeout: float = float(os.getenv("ARCHIE_LLM_TIMEOUT", "300"))
    llm_max_tokens: int = int(os.getenv("ARCHIE_LLM_MAX_TOKENS", "768"))
    top_k: int = int(os.getenv("ARCHIE_TOP_K", "6"))
    retrieval_candidate_k: int = int(os.getenv("ARCHIE_RETRIEVAL_CANDIDATE_K", "36"))
    neighbor_radius: int = int(os.getenv("ARCHIE_NEIGHBOR_RADIUS", "1"))
    strict_audit: bool = os.getenv("ARCHIE_STRICT_AUDIT", "1").lower() not in {"0", "false", "no"}

settings = Settings()
