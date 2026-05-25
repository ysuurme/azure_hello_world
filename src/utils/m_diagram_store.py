"""Persistence for Diagram Studio artifacts.

A diagram is a stable-slug trio: brief.json + source.d2 + render.svg. The primary
backend is Azure Blob (project storage account, container `diagrams`), accessed via
DefaultAzureCredential — SP locally, UAMI in the cloud. When no storage account is
configured the store falls back to the local filesystem (CI / offline). Blob
versioning (enabled on the account) provides history for the build-forward flow.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src import config
from src.utils.m_log import f_log

_BRIEF = "brief.json"
_D2 = "source.d2"
_SVG = "render.svg"


def slugify(subject: str) -> str:
    """Derive a stable, filesystem/blob-safe identity from a diagram subject."""
    cleaned = re.sub(r"[^a-z0-9]+", "-", (subject or "").strip().lower()).strip("-")
    return cleaned[:48] or "diagram"


@dataclass
class DiagramSummary:
    slug: str
    subject: str
    updated_at: str | None = None


@dataclass
class DiagramRecord:
    slug: str
    brief: dict
    d2: str
    svg: bytes | None


class FilesystemDiagramStore:
    """Local-filesystem backend (CI / offline). Layout: <root>/<slug>/{brief.json,source.d2,render.svg}."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = Path(root or config.DIAGRAM_STORE_DIR)

    def save(self, brief: dict, d2: str, svg: bytes | None) -> str:
        slug = slugify(brief.get("subject", ""))
        target = self._root / slug
        target.mkdir(parents=True, exist_ok=True)
        (target / _BRIEF).write_text(json.dumps(brief, indent=2), encoding="utf-8")
        (target / _D2).write_text(d2, encoding="utf-8")
        if svg:
            (target / _SVG).write_bytes(svg)
        f_log(f"Diagram '{slug}' saved to filesystem store.", level="success")
        return slug

    def load(self, slug: str) -> DiagramRecord | None:
        target = self._root / slug
        brief_file = target / _BRIEF
        if not brief_file.exists():
            return None
        svg_file = target / _SVG
        return DiagramRecord(
            slug=slug,
            brief=json.loads(brief_file.read_text(encoding="utf-8")),
            d2=(target / _D2).read_text(encoding="utf-8") if (target / _D2).exists() else "",
            svg=svg_file.read_bytes() if svg_file.exists() else None,
        )

    def list(self) -> list[DiagramSummary]:
        if not self._root.exists():
            return []
        summaries = []
        for child in sorted(self._root.iterdir()):
            brief_file = child / _BRIEF
            if not (child.is_dir() and brief_file.exists()):
                continue
            brief = json.loads(brief_file.read_text(encoding="utf-8"))
            updated = datetime.fromtimestamp(brief_file.stat().st_mtime, tz=timezone.utc).isoformat()
            summaries.append(
                DiagramSummary(slug=child.name, subject=brief.get("subject", child.name), updated_at=updated)
            )
        return summaries

    def delete(self, slug: str) -> bool:
        target = self._root / slug
        if not target.exists():
            return False
        shutil.rmtree(target)
        f_log(f"Diagram '{slug}' deleted from filesystem store.", level="process")
        return True


class BlobDiagramStore:
    """Azure Blob backend; blobs keyed <slug>/{brief.json,source.d2,render.svg}. Account versioning = history."""

    def __init__(self, account: str, container: str, credential: Any) -> None:
        from azure.storage.blob import ContainerClient

        self._container = ContainerClient(
            account_url=f"https://{account}.blob.core.windows.net",
            container_name=container,
            credential=credential,
        )

    def save(self, brief: dict, d2: str, svg: bytes | None) -> str:
        slug = slugify(brief.get("subject", ""))
        self._container.upload_blob(f"{slug}/{_BRIEF}", json.dumps(brief, indent=2), overwrite=True)
        self._container.upload_blob(f"{slug}/{_D2}", d2, overwrite=True)
        if svg:
            self._container.upload_blob(f"{slug}/{_SVG}", svg, overwrite=True)
        f_log(f"Diagram '{slug}' saved to blob store (new version).", level="success")
        return slug

    def load(self, slug: str) -> DiagramRecord | None:
        brief_raw = self._download(f"{slug}/{_BRIEF}")
        if brief_raw is None:
            return None
        d2_raw = self._download(f"{slug}/{_D2}")
        svg_raw = self._download(f"{slug}/{_SVG}")
        return DiagramRecord(
            slug=slug,
            brief=json.loads(brief_raw.decode("utf-8")),
            d2=d2_raw.decode("utf-8") if d2_raw else "",
            svg=svg_raw,
        )

    def list(self) -> list[DiagramSummary]:
        summaries = []
        for prefix in self._container.walk_blobs(delimiter="/"):
            slug = prefix.name.rstrip("/")
            brief_raw = self._download(f"{slug}/{_BRIEF}")
            if brief_raw is None:
                continue
            brief = json.loads(brief_raw.decode("utf-8"))
            summaries.append(DiagramSummary(slug=slug, subject=brief.get("subject", slug)))
        return summaries

    def delete(self, slug: str) -> bool:
        names = [b.name for b in self._container.list_blobs(name_starts_with=f"{slug}/")]
        if not names:
            return False
        for name in names:
            self._container.delete_blob(name)
        f_log(f"Diagram '{slug}' deleted from blob store.", level="process")
        return True

    def _download(self, blob_name: str) -> bytes | None:
        from azure.core.exceptions import ResourceNotFoundError

        try:
            return self._container.download_blob(blob_name).readall()
        except ResourceNotFoundError:
            return None


def get_diagram_store(credential: Any = None) -> FilesystemDiagramStore | BlobDiagramStore:
    """Return the blob store when a storage account is configured, else the filesystem fallback."""
    account = config.DIAGRAM_STORAGE_ACCOUNT
    if not account:
        f_log("No diagram storage account configured; using filesystem store.", level="debug")
        return FilesystemDiagramStore()
    if credential is None:
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()
    return BlobDiagramStore(account=account, container=config.DIAGRAM_CONTAINER, credential=credential)
