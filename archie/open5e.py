from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import httpx

from .config import settings

# V2 resources we inventory in alpha.2.  These names match Open5e's API routes,
# not Archie's future normalized content types.  Alpha.2 never imports content.
RESOURCE_ENDPOINTS: dict[str, str] = {
    "classes": "classes",
    "subclasses": "classes",
    "species": "species",
    "spells": "spells",
    "backgrounds": "backgrounds",
    "feats": "feats",
    "equipment": "items",
    "magic_items": "magicitems",
    "rules": "rules",
    "conditions": "conditions",
    "creatures": "creatures",
}


class Open5eError(RuntimeError):
    pass


@dataclass(frozen=True)
class Open5eDocument:
    key: str
    name: str
    document_type: str | None
    publisher: dict[str, Any] | str | None
    license: dict[str, Any] | str | None
    game_system: dict[str, Any] | str | None
    author: str | None
    published_at: str | None
    permalink: str | None
    raw: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def _first(obj: dict[str, Any], *keys: str, default=None):
    for key in keys:
        if key in obj and obj[key] is not None:
            return obj[key]
    return default


def _document_from_api(obj: dict[str, Any]) -> Open5eDocument:
    key = str(_first(obj, "key", "slug", default="")).strip()
    name = str(_first(obj, "name", "title", default=key)).strip()
    if not key:
        raise Open5eError(f"Open5e document is missing a key: {obj!r}")
    return Open5eDocument(
        key=key,
        name=name or key,
        document_type=_first(obj, "type", "document_type"),
        publisher=_first(obj, "publisher"),
        license=_first(obj, "license"),
        game_system=_first(obj, "game_system", "gamesystem", "ruleset"),
        author=_first(obj, "author"),
        published_at=_first(obj, "published_at", "published"),
        permalink=_first(obj, "permalink", "url"),
        raw=obj,
    )


class Open5eClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = (base_url or settings.open5e_base_url).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.open5e_timeout
        self.transport = transport

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                r = client.get(url, params=params)
                r.raise_for_status()
                data = r.json()
        except Exception as exc:
            raise Open5eError(f"Open5e request failed at {url}: {exc}") from exc
        if not isinstance(data, dict):
            raise Open5eError(f"Open5e returned a non-object payload at {url}")
        return data

    def _paged(self, path: str) -> list[dict[str, Any]]:
        page = 1
        out: list[dict[str, Any]] = []
        while True:
            data = self._get(path, {"limit": 100, "page": page})
            results = data.get("results")
            if not isinstance(results, list):
                raise Open5eError(f"Open5e paginated payload at {path} has no results list")
            out.extend(x for x in results if isinstance(x, dict))
            count = data.get("count")
            if isinstance(count, int) and len(out) >= count:
                break
            if not results:
                break
            # DRF responses often expose next, but page counting is more stable for snapshots.
            if data.get("next") in (None, "") and not (isinstance(count, int) and len(out) < count):
                break
            page += 1
            if page > 1000:
                raise Open5eError("Open5e pagination exceeded safety limit")
        return out

    def documents(self) -> list[Open5eDocument]:
        return [_document_from_api(x) for x in self._paged("documents/")]

    def resource_count(self, endpoint: str, document_key: str, *, extra_params: dict[str, Any] | None = None) -> int | None:
        params: dict[str, Any] = {"document__key__in": document_key, "limit": 1, "fields": "key"}
        if extra_params:
            params.update(extra_params)
        data = self._get(f"{endpoint.strip('/')}/", params)
        count = data.get("count")
        if isinstance(count, int):
            return count
        results = data.get("results")
        if isinstance(results, list):
            # This fallback is deliberately conservative; exact inventory counts require count.
            return len(results) if len(results) == 0 else None
        return None

    def inventory_document(self, document_key: str) -> dict[str, int | None]:
        out: dict[str, int | None] = {}
        for label, endpoint in RESOURCE_ENDPOINTS.items():
            extra = None
            if label == "classes":
                extra = {"is_subclass": "false"}
            elif label == "subclasses":
                extra = {"is_subclass": "true"}
            out[label] = self.resource_count(endpoint, document_key, extra_params=extra)
        return out


def _canonical_json(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _snapshot_path(stamp: str) -> Path:
    return settings.open5e_discovery_dir / f"open5e-discovery-{stamp}.json"


def write_snapshot(snapshot: dict[str, Any]) -> Path:
    settings.open5e_discovery_dir.mkdir(parents=True, exist_ok=True)
    payload = dict(snapshot)
    payload.pop("snapshot_sha256", None)
    digest = hashlib.sha256(_canonical_json(payload)).hexdigest()
    payload["snapshot_sha256"] = digest
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = _snapshot_path(stamp)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")
    latest = settings.open5e_discovery_dir / "latest.json"
    latest.write_text(text, encoding="utf-8")
    return path


def discover_open5e(client: Open5eClient | None = None) -> dict[str, Any]:
    client = client or Open5eClient()
    docs = client.documents()
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    documents = []
    for doc in docs:
        d = doc.to_dict()
        d["resource_counts"] = client.inventory_document(doc.key)
        d.pop("raw", None)  # Snapshot keeps normalized provenance metadata, not content.
        documents.append(d)
    snapshot: dict[str, Any] = {
        "schema_version": 1,
        "provider": "open5e",
        "api_version": "v2",
        "base_url": client.base_url,
        "generated_at": generated,
        "imported_into_archie": False,
        "documents": documents,
        "resource_endpoints": RESOURCE_ENDPOINTS,
    }
    path = write_snapshot(snapshot)
    saved = json.loads(path.read_text(encoding="utf-8"))
    saved["snapshot_path"] = str(path.relative_to(settings.root))
    saved["document_count"] = len(documents)
    return saved


def load_latest_snapshot() -> dict[str, Any]:
    path = settings.open5e_discovery_dir / "latest.json"
    if not path.exists():
        raise Open5eError("No Open5e discovery snapshot exists. Run: archie sources discover open5e")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("provider") != "open5e":
        raise Open5eError(f"Invalid Open5e discovery snapshot: {path}")
    return data


def inventory_from_snapshot(document_key: str | None = None) -> dict[str, Any]:
    data = load_latest_snapshot()
    docs = data.get("documents", [])
    if document_key is not None:
        docs = [d for d in docs if d.get("key") == document_key]
        if not docs:
            raise Open5eError(f"Document not found in latest Open5e snapshot: {document_key}")
    return {
        "provider": "open5e",
        "api_version": data.get("api_version"),
        "generated_at": data.get("generated_at"),
        "snapshot_sha256": data.get("snapshot_sha256"),
        "documents": docs,
        "document_count": len(docs),
        "imported_into_archie": False,
    }
