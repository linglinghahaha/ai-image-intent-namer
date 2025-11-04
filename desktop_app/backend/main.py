#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI backend exposing the AI image intent naming capabilities as HTTP
services.  This module wraps the existing core logic in
`tool/ai_image_intent_namer.py` so that a modern Electron + React client can
invoke the same workflows over a local API.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

# ---------------------------------------------------------------------------
# Import legacy core logic
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent.parent
TOOL_DIR = REPO_ROOT / "tool"

if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import ai_image_intent_namer as core  # type: ignore  # noqa: E402
from ai_image_intent_namer import (  # noqa: E402
    Config,
    DEFAULT_INTENT_LANGUAGE,
    DEFAULT_REASON_LANGUAGE,
    collect_images,
    read_text,
    sanitize_filename,
    write_text_utf8,
    build_attachment_plan,
    execute_attachment_plan,
    load_image_mapping,
    save_image_mapping,
    load_attachment_plan,
    save_attachment_plan,
    call_openai_chat,
    build_ai_messages,
    safe_parse_json,
    validate_ai_result,
    get_last_llm_error,
    process_document,
    extract_doc_title,
    collect_images_to_attachment,
    normalize_embedded_html_images,
)

# ---------------------------------------------------------------------------
# Files shared with legacy GUI (profiles/templates)
# ---------------------------------------------------------------------------

PROFILES_PATH = TOOL_DIR / "ai_image_intent_namer_gui.profiles.json"
TEMPLATE_PRESETS_PATH = TOOL_DIR / "ai_image_intent_namer_gui.templates.json"
DEFAULT_ATTACH_DIR = "attachments"
DEFAULT_NAME_TEMPLATE = "{title}_{index:02d}_{intent}"

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

class LogCollector:
    """Collects structured log entries emitted during long running tasks."""

    def __init__(self) -> None:
        self._entries: List[Dict[str, Any]] = []

    def _append(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        entry: Dict[str, Any] = {
            "level": level,
            "message": message,
            "ts": time.time(),
        }
        if extra:
            entry["extra"] = extra
        self._entries.append(entry)

    def info(self, message: str) -> None:
        self._append("info", message)

    def error(self, message: str) -> None:
        self._append("error", message)

    # Config callback adapters ------------------------------------------------

    def progress_cb(self, message: str) -> None:
        self.info(message)

    def llm_event_cb(self, event: Dict[str, Any]) -> None:
        summary = f"llm:{event.get('mode', 'unknown')}:{event.get('event', 'update')}"
        if event.get("indexes"):
            summary += f" idx={event['indexes']}"
        status = event.get("status")
        if status:
            summary += f" status={status}"
        self._append("debug", summary, event)

    def batch_result_cb(self, payload: Dict[str, Any]) -> None:
        count = len(payload.get("items", [])) if isinstance(payload.get("items"), list) else 0
        self._append("info", f"batch completed with {count} item(s)", payload)

    def batch_confirm_cb(self, batch: List[Dict[str, Any]]) -> bool:
        self._append("debug", f"confirming batch of {len(batch or [])} item(s)")
        return True

    # ------------------------------------------------------------------

    def export(self) -> List[Dict[str, Any]]:
        return self._entries


def _as_item_dict(item: Any) -> Optional[Dict[str, Any]]:
    if item is None:
        return None
    if is_dataclass(item):
        return asdict(item)
    if isinstance(item, dict):
        return dict(item)
    return None


def _normalize_candidates(candidates: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    if not candidates:
        return normalized
    for cand in candidates:
        if not isinstance(cand, dict):
            continue
        normalized.append(
            {
                "name": cand.get("title") or cand.get("name") or "",
                "strategy": cand.get("strategy"),
                "reason": cand.get("reason") or "",
                "confidence": cand.get("confidence", 0.0),
            }
        )
    return normalized


def _serialize_item(raw_item: Any) -> Optional[Dict[str, Any]]:
    item = _as_item_dict(raw_item)
    if not item:
        return None
    serialized: Dict[str, Any] = {
        "index": item.get("index"),
        "kind": item.get("kind"),
        "src": item.get("src"),
        "display_name": item.get("display_name") or item.get("suggested_name"),
        "block_index": item.get("block_index"),
        "image_index": item.get("image_index"),
        "normalized_title": item.get("normalized_title"),
        "suggested_name": item.get("suggested_name"),
        "best": item.get("best"),
        "request_mode": item.get("request_mode"),
        "ai_error": item.get("ai_error"),
        "ai_raw": item.get("ai_raw"),
        "above_text": item.get("above_text") or "",
        "below_text": item.get("below_text") or "",
        "between_text": item.get("between_text") or "",
        "explicit_refs": item.get("explicit_refs") or [],
        "alt": item.get("alt"),
        "title_attr": item.get("title_attr"),
    }
    serialized["candidates"] = _normalize_candidates(item.get("candidates"))
    return serialized


def _serialize_preview_result(result: Dict[str, Any], logs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    items = [
        item
        for item in (
            _serialize_item(raw_item) for raw_item in result.get("items", [])
        )
        if item is not None
    ]
    payload: Dict[str, Any] = {
        "document": result.get("document"),
        "title": result.get("title"),
        "count": result.get("count", len(items)),
        "items": items,
    }
    if logs:
        payload["logs"] = logs
    return payload
# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class AISettings(BaseModel):
    base_url: str = Field(..., description="LLM endpoint base URL")
    api_key: str = Field(..., description="LLM API key")
    model: str = Field(..., description="Primary LLM model name")
    timeout: int = Field(120, ge=10, le=600)
    max_retries: int = Field(3, ge=0, le=10)
    rate_limit: float = Field(0.4, ge=0.0)
    vision: bool = True
    batch_size: int = Field(5, ge=1, le=32)


class NamingSettings(BaseModel):
    strategy: str = Field("above", description="Candidate strategy key")
    template: str = Field(DEFAULT_NAME_TEMPLATE, description="Filename template")
    seq_width: int = Field(2, ge=1, le=6)
    max_name_len: int = Field(80, ge=10, le=255)
    intent_language: str = Field(DEFAULT_INTENT_LANGUAGE)
    reason_language: Optional[str] = None

    @validator("reason_language", always=True)
    def _default_reason_language(
        cls, value: Optional[str], values: Dict[str, object]
    ) -> str:
        if value:
            return value
        lang = str(values.get("intent_language") or DEFAULT_INTENT_LANGUAGE)
        return "en" if lang.startswith("en") else DEFAULT_REASON_LANGUAGE


class RuntimeSettings(BaseModel):
    attach_dir_name: str = Field(DEFAULT_ATTACH_DIR)
    download: bool = False
    verbose: bool = True
    backup: bool = True


class PreviewRequest(BaseModel):
    md_path: Path = Field(..., description="Markdown document to analyse")
    ai: AISettings
    naming: NamingSettings
    runtime: RuntimeSettings


class CandidateRequest(BaseModel):
    document_title: str = Field(..., description="Document title for context")
    above_text: str = ""
    below_text: str = ""
    between_text: str = ""
    explicit_refs: List[str] = []
    alt_text: Optional[str] = None
    title_attr: Optional[str] = None
    vision_src: Optional[str] = None
    ai: AISettings
    verbose: bool = False


class ApplyRequest(BaseModel):
    md_path: Path
    chosen_map: Dict[int, str] = Field(
        ..., description="Mapping of image index to selected intent"
    )
    skip_indexes: Set[int] = Field(default_factory=set)
    ai: AISettings
    naming: NamingSettings
    runtime: RuntimeSettings


class TextProcessingRequest(BaseModel):
    prompt_template: str = Field(..., description="Prompt to send to LLM")
    content: str = Field(..., description="Source text")
    ai: AISettings
    verbose: bool = False


class PrefetchRequest(BaseModel):
    md_path: Path
    runtime: RuntimeSettings
    backup: bool = True


class NormalizeHtmlRequest(BaseModel):
    md_path: Path
    backup: bool = True


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="AI Image Intent Naming API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _config_from_request(
    mode: str,
    ai: AISettings,
    naming: NamingSettings,
    runtime: RuntimeSettings,
    log_collector: Optional[LogCollector] = None,
) -> Config:
    cfg = Config(
        mode=mode,
        strategy=naming.strategy,
        base_url=ai.base_url.strip(),
        api_key=ai.api_key.strip(),
        model=ai.model.strip(),
        timeout=ai.timeout,
        max_retries=ai.max_retries,
        rate_limit=ai.rate_limit,
        attach_dir_name=runtime.attach_dir_name.strip() or DEFAULT_ATTACH_DIR,
        download=runtime.download,
        name_template=naming.template.strip() or DEFAULT_NAME_TEMPLATE,
        seq_width=naming.seq_width,
        max_name_len=naming.max_name_len,
        save_report=None,
        verbose=runtime.verbose,
        backup=runtime.backup,
        vision=ai.vision,
        chunk_size=ai.batch_size,
        intent_language=naming.intent_language,
        reason_language=naming.reason_language,
    )
    if log_collector:
        cfg.progress_cb = log_collector.progress_cb
        cfg.llm_event_cb = log_collector.llm_event_cb
        cfg.batch_result_cb = log_collector.batch_result_cb
        cfg.batch_confirm_cb = log_collector.batch_confirm_cb
    return cfg


def _ensure_markdown_exists(path: Path) -> Path:
    md_path = path.expanduser().resolve()
    if not md_path.exists():
        raise HTTPException(status_code=404, detail=f"Markdown file not found: {md_path}")
    if md_path.suffix.lower() != ".md":
        raise HTTPException(status_code=400, detail="Only Markdown (.md) files are supported")
    return md_path


def _load_json_file(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return core.safe_parse_json(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=500, detail=f"Failed to read {path.name}: {exc}"
        ) from exc


def _dump_json_file(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/v1/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/profiles")
def list_profiles() -> Dict:
    return _load_json_file(PROFILES_PATH)


@app.put("/api/v1/profiles/{profile_name}")
def upsert_profile(profile_name: str, payload: Dict) -> Dict:
    data = _load_json_file(PROFILES_PATH)
    data[profile_name] = payload
    _dump_json_file(PROFILES_PATH, data)
    return {"ok": True, "profile": profile_name}


@app.delete("/api/v1/profiles/{profile_name}")
def delete_profile(profile_name: str) -> Dict:
    data = _load_json_file(PROFILES_PATH)
    if profile_name in data:
        del data[profile_name]
        _dump_json_file(PROFILES_PATH, data)
    return {"ok": True}


@app.get("/api/v1/templates")
def list_templates() -> Dict:
    return _load_json_file(TEMPLATE_PRESETS_PATH)


@app.put("/api/v1/templates/{template_name}")
def upsert_template(template_name: str, payload: Dict) -> Dict:
    data = _load_json_file(TEMPLATE_PRESETS_PATH)
    data[template_name] = payload
    _dump_json_file(TEMPLATE_PRESETS_PATH, data)
    return {"ok": True, "template": template_name}


@app.delete("/api/v1/templates/{template_name}")
def delete_template(template_name: str) -> Dict:
    data = _load_json_file(TEMPLATE_PRESETS_PATH)
    if template_name in data:
        del data[template_name]
        _dump_json_file(TEMPLATE_PRESETS_PATH, data)
    return {"ok": True}


@app.post("/api/v1/documents/preview")
async def preview_document(payload: PreviewRequest) -> Dict:
    md_path = _ensure_markdown_exists(payload.md_path)
    log_collector = LogCollector()
    cfg = _config_from_request(
        mode="dry-run",
        ai=payload.ai,
        naming=payload.naming,
        runtime=payload.runtime,
        log_collector=log_collector,
    )
    try:
        result = await run_in_threadpool(process_document, md_path, cfg)
    except Exception as exc:
        log_collector.error(str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    serialized = _serialize_preview_result(result, log_collector.export())
    return serialized


@app.post("/api/v1/candidates")
async def generate_candidates(payload: CandidateRequest) -> Dict:
    try:
        msgs = build_ai_messages(
            payload.document_title,
            payload.above_text,
            payload.below_text,
            payload.between_text,
            payload.explicit_refs,
            payload.alt_text,
            payload.title_attr,
            vision_src=payload.vision_src,
            base_url=payload.ai.base_url,
        )
        raw = await run_in_threadpool(
            call_openai_chat,
            payload.ai.base_url,
            payload.ai.api_key,
            payload.ai.model,
            msgs,
            payload.ai.timeout,
            payload.ai.max_retries,
            payload.ai.rate_limit,
            payload.verbose,
        )
        if not raw:
            raise HTTPException(
                status_code=502,
                detail=get_last_llm_error() or "Empty response from LLM",
            )
        data = safe_parse_json(raw)
        result = validate_ai_result(data)
        if not result:
            raise HTTPException(
                status_code=502,
                detail="LLM response did not contain valid candidates",
            )
        return {
            "normalized_title": result.get("normalized_title"),
            "best": result.get("best"),
            "candidates": _normalize_candidates(result.get("candidates")),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/text/process")
async def process_text(payload: TextProcessingRequest) -> Dict:
    log_collector = LogCollector()
    log_collector.info("processing text via LLM")
    prompt = payload.prompt_template.format(text=payload.content)
    try:
        response = await run_in_threadpool(
            call_openai_chat,
            payload.ai.base_url,
            payload.ai.api_key,
            payload.ai.model,
            [{"role": "user", "content": prompt}],
            payload.ai.timeout,
            payload.ai.max_retries,
            payload.ai.rate_limit,
            payload.verbose,
        )
        if not response:
            raise HTTPException(
                status_code=502,
                detail=get_last_llm_error() or "Empty response from LLM",
            )
        return {"result": response, "logs": log_collector.export()}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/documents/apply")
async def apply_document(payload: ApplyRequest) -> Dict:
    md_path = _ensure_markdown_exists(payload.md_path)
    log_collector = LogCollector()
    cfg = _config_from_request(
        mode="apply",
        ai=payload.ai,
        naming=payload.naming,
        runtime=payload.runtime,
        log_collector=log_collector,
    )

    def worker() -> Dict:
        log_collector.info(f"开始写回：{md_path.name}")
        text = read_text(md_path)
        refs = collect_images(text)
        attach_dir = md_path.parent / cfg.attach_dir_name
        attach_dir.mkdir(parents=True, exist_ok=True)
        mapping = load_image_mapping(attach_dir)
        plan = load_attachment_plan(attach_dir)
        skip_set = set(payload.skip_indexes or set())

        reused_plan = False
        if plan and plan.get("document") == str(md_path) and not skip_set:
            statuses = [
                item.get("status")
                for item in plan.get("items", [])
                if isinstance(item, dict)
            ]
            if statuses and all(status in ("pending", "done") for status in statuses):
                reused_plan = True

        chosen_map = {
            int(idx): sanitize_filename(name or "image")
            for idx, name in payload.chosen_map.items()
            if int(idx) not in skip_set
        }

        if not reused_plan:
            plan = build_attachment_plan(
                md_path,
                text,
                refs,
                chosen_map,
                extract_doc_title(text, md_path),
                attach_dir,
                cfg.name_template,
                cfg.seq_width,
                cfg.max_name_len,
                skip_indexes=skip_set,
                intent_language=cfg.intent_language,
            )
            if plan.get("items"):
                save_attachment_plan(attach_dir, plan)

        def step_logger(info: Dict) -> None:
            log_collector.info(f"计划步骤：{info.get('action', 'unknown')} #{info.get('index')} -> {info.get('target')}")

        success, mapping_changed = execute_attachment_plan(
            plan,
            md_path,
            attach_dir,
            cfg.timeout,
            mapping,
            logger=step_logger,
            prefer_move=True,
        )
        if not success:
            raise RuntimeError("Attachment plan execution failed")

        if mapping_changed:
            save_image_mapping(attach_dir, mapping)

        new_text = text
        if plan and plan.get("items"):
            new_text = plan.get("rewritten_text", text)
        if new_text != text:
            if cfg.backup:
                backup_path = md_path.with_suffix(md_path.suffix + ".bak")
                backup_path.write_text(text, encoding="utf-8", newline="\n")
            write_text_utf8(md_path, new_text)

        plan["completed"] = True
        plan["completed_at"] = time.time()
        save_attachment_plan(attach_dir, plan)

        log_collector.info(f"写回完成：{md_path.name}")
        return {
            "document": str(md_path),
            "updated": True,
            "skip_indexes": sorted(skip_set),
            "applied": sorted(chosen_map.keys()),
            "logs": log_collector.export(),
        }

    try:
        result = await run_in_threadpool(worker)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        log_collector.error(str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/attachments/prefetch")
async def prefetch_attachments(payload: PrefetchRequest) -> Dict:
    md_path = _ensure_markdown_exists(payload.md_path)
    log_collector = LogCollector()
    try:
        log_collector.info("collecting images to attachment dir")
        stats = await run_in_threadpool(
            collect_images_to_attachment,
            md_path,
            payload.runtime.attach_dir_name or DEFAULT_ATTACH_DIR,
            payload.runtime.timeout,
            payload.backup,
        )
        return {"ok": True, "stats": stats, "logs": log_collector.export()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/documents/normalize_html")
async def normalize_html_images(payload: NormalizeHtmlRequest) -> Dict:
    md_path = _ensure_markdown_exists(payload.md_path)
    log_collector = LogCollector()
    try:
        text = read_text(md_path)
        new_text, count = normalize_embedded_html_images(text)
        updated = False
        if count > 0 and new_text != text:
            if payload.backup:
                backup_path = md_path.with_suffix(md_path.suffix + ".bak")
                backup_path.write_text(text, encoding="utf-8", newline="\n")
            write_text_utf8(md_path, new_text)
            updated = True
        return {"ok": True, "updated": updated, "count": count, "logs": log_collector.export()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Dev helper: run with `uvicorn desktop_app.backend.main:app --reload`
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("desktop_app.backend.main:app", host="127.0.0.1", port=8000, reload=True)
