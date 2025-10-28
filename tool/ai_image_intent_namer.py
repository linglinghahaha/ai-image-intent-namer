#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 图片“图意”命名器（单文件、开箱即用，Windows/中文友好）

功能概述：
- 读取 Markdown 文档，解析图片与上下文文本块，生成多种“图意”候选（上文摘要 / 下文摘要 / 区间摘要 / 显式引用融合 / 视觉理解）
- 支持调用 OpenAI 兼容接口（Chat Completions），从命令行或环境变量读取 base-url、api-key、model
- 提供多种命名策略：seq（纯顺序不调用AI）、above（仅上文）、below（仅下文）、between（区间）、intent（融合/智能）、hybrid（多方案，交互或自动选择）、sci（论文图注强化）
- 支持 dry-run（预览）、apply（实际重命名并回写链接）、no-rename（仅生成报告不改文档）、interactive（逐图选择）、save-report（输出 JSON 报告）
- 可选下载远程图片到文档同级 attachment 目录，并将链接改为相对路径
- 命名模板支持变量：{title}、{block}、{idx}、{intent}，默认格式类似“文档标题1_图意01”，序号宽度可配置
- 文件名保留中文、去非法字符、空白压缩为下划线、自动去重
- 解析 Markdown 块级结构：标题、段落、列表、表格、代码块、引用块、图片块、HTML块；识别“图注/表注”与显式引用模式（如“如上图所示”“如下图所示”“见图X”“如图X”“上图/下图/如上/如下”）
- 遇到 AI 出错或超时自动重试 / 降级为 seq 策略；写回失败支持备份与回滚

依赖与环境：
- Python 3.9+
- requests（HTTP 调用）
如果缺少 requests，请先安装：pip install requests

环境变量（可选）：
- OPENAI_BASE_URL
- OPENAI_API_KEY
- OPENAI_MODEL

使用示例（Windows CMD）：
1) 仅预览（不改文件），智能融合策略，生成报告：
   python tool\\ai_image_intent_namer.py "第四次课\\zotero4\\动物篇(7)·软体动物门(中)+VVZHWZPI.md" --mode dry-run --strategy intent --base-url https://api.openai.com --api-key sk-xxx --model gpt-4o-mini --save-report tool\\out\\names.json

2) 实际应用（下载并重命名，改写链接，融合策略）：
   python tool\\ai_image_intent_namer.py "路径\\目标.md" --mode apply --download --attach-dir-name attachments --strategy intent --base-url https://api.openai.com --api-key sk-xxx --model gpt-4o-mini

3) 交互选择（逐图手动选方案），不下载，仅重命名与改链：
   python tool\\ai_image_intent_namer.py "路径\\目标.md" --mode interactive --strategy hybrid

4) 仅报告（不改名、不下载）：
   python tool\\ai_image_intent_namer.py "路径\\目标.md" --mode no-rename --strategy intent --save-report tool\\out\\report.json

5) 纯顺序（不调用AI），两位编号、模板自定义：
   python tool\\ai_image_intent_namer.py "路径\\目标.md" --mode apply --strategy seq --seq-width 2 --name-template "{title}{block:02d}_图意{idx:02d}"

"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
from collections import defaultdict
import copy
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import unquote, urlparse

try:
    import requests
except Exception:
    requests = None

# 控制台编码（Windows/中文友好）
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# -----------------------------
# 通用工具与清洗
# -----------------------------

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".tiff", ".ico", ".heic", ".tif"}

DEFAULT_INTENT_LANGUAGE = "auto"
DEFAULT_REASON_LANGUAGE = "zh"
LANGUAGE_LOCALES = {
    "auto": None,
    "zh": "zh-CN",
    "en": "en-US",
}
REASON_LANGUAGE_CHOICES = ("zh", "en")

MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(((?:[^()\\]|\\.|(?:\([^()]*\)))+)\)")
HTML_IMG_RE = re.compile(r'<img\b[^>]*\bsrc=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)
WIKILINK_EMBED_RE = re.compile(r"!\[\[(.*?)\]\]")

REF_DEF_RE = re.compile(r'^\s*\[([^\]]+)\]:\s*(\S+)(?:\s+(".*?"|\'.*?\'|\(.*?\)))?\s*$', re.MULTILINE)

CAPTION_CLUES = [
    "图注", "图示", "示意图", "如图所示", "如上图所示", "如下图所示", "见图", "如图", "Figure", "Fig.", "Caption", "表注", "表", "图"
]
EXPLICIT_REF_PATTERNS = [
    r"如上图所示", r"如下图所示", r"如图\s*\d+", r"见图\s*\d+", r"上图", r"下图", r"如上", r"如下", r"如前图", r"见前图"
]

FORBIDDEN_CHARS = '\\/:*?"<>|'
WHITESPACE_RE = re.compile(r"\s+")
MAPPING_FILENAME = ".image_moves.json"
PLAN_FILENAME = ".image_plan.json"

def sanitize_filename(name: str) -> str:
    if not name:
        return "image"
    name = "".join(ch for ch in name if ch.isprintable())
    for ch in ("（", "）", "(", ")", "“", "”", "'", '"'):
        name = name.replace(ch, "")
    name = "".join(ch for ch in name if ch not in FORBIDDEN_CHARS)
    name = name.strip(" .")
    name = WHITESPACE_RE.sub("_", name)
    return name or "image"
def sanitize_intent_for_language(text: str, intent_language: str = DEFAULT_INTENT_LANGUAGE) -> str:
    raw = (text or '').strip()
    lang = (intent_language or DEFAULT_INTENT_LANGUAGE).lower()
    if lang.startswith('en'):
        raw = raw.replace('-', ' ')
        raw = WHITESPACE_RE.sub(' ', raw)
    return sanitize_filename(raw)

def ensure_unique_path(dest_dir: Path, filename: str) -> Path:
    base = Path(filename).stem
    ext = Path(filename).suffix
    candidate = dest_dir / (base + ext)
    idx = 1
    while candidate.exists():
        candidate = dest_dir / f"{base} ({idx}){ext}"
        idx += 1
    return candidate

def is_remote_url(url: str) -> bool:
    s = (url or "").strip().lower()
    return s.startswith("http://") or s.startswith("https://")

def resolve_local_image(md_dir: Path, src: str) -> Optional[Path]:
    """
    解析/定位本地图片路径，容错以下情况：
    - 链接含引号、反斜杠或 URL 编码（空格等）
    - 目标文件不在预期子目录时，在文档同级或其子目录递归搜索
    - 名称包含中文与括号等特殊字符
    返回存在的 Path 或 None。
    """
    try:
        s = (src or "").strip().strip('"').strip("'")
        if not s:
            return None
        s = s.replace("\\", "/")
        # 直接解析
        p = (md_dir / Path(s)).resolve()
        if p.exists():
            return p
        # URL 解码后重试
        s2 = unquote(s)
        p2 = (md_dir / Path(s2)).resolve()
        if p2.exists():
            return p2
        # 基于文件名递归搜索（先精确名称，再前缀匹配）
        basename = Path(s2).name or Path(s).name
        if basename:
            for cand in md_dir.rglob(basename):
                if cand.is_file():
                    return cand
            stem = Path(basename).stem
            exts = IMAGE_EXTS
            for cand in md_dir.rglob(f"{stem}*"):
                if cand.is_file() and cand.suffix.lower() in exts:
                    return cand
        return None
    except Exception:
        return None


def _make_rel(path: Path, root: Path) -> str:
    try:
        return os.path.relpath(path, root).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _try_move_file(src: Path, dest: Path) -> bool:
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dest)
        return True
    except Exception:
        try:
            data = src.read_bytes()
            dest.write_bytes(data)
            try:
                src.unlink()
            except Exception:
                pass
            return True
        except Exception:
            return False


def reserve_unique_path(attach_dir: Path, filename: str, reserved: set) -> Path:
    base = Path(filename).stem
    ext = Path(filename).suffix
    idx = 0
    while True:
        name = base if idx == 0 else f"{base} ({idx})"
        candidate = attach_dir / f"{name}{ext}"
        if str(candidate.resolve()) not in reserved and not candidate.exists():
            reserved.add(str(candidate.resolve()))
            return candidate
        idx += 1


def mapping_file_path(attach_dir: Path) -> Path:
    return attach_dir / MAPPING_FILENAME


def load_image_mapping(attach_dir: Path) -> Dict[str, Dict]:
    try:
        path = mapping_file_path(attach_dir)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def save_image_mapping(attach_dir: Path, mapping: Dict[str, Dict]) -> None:
    try:
        attach_dir.mkdir(parents=True, exist_ok=True)
        path = mapping_file_path(attach_dir)
        path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def plan_file_path(attach_dir: Path) -> Path:
    return attach_dir / PLAN_FILENAME


def load_attachment_plan(attach_dir: Path) -> Dict:
    try:
        path = plan_file_path(attach_dir)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def save_attachment_plan(attach_dir: Path, plan: Dict) -> None:
    try:
        attach_dir.mkdir(parents=True, exist_ok=True)
        path = plan_file_path(attach_dir)
        path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

def read_text(path: Path) -> str:
    encodings = ["utf-8", "utf-16", "gb18030"]
    for enc in encodings:
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
        except OSError:
            break
    return path.read_text(encoding="utf-8", errors="ignore")

def write_text_utf8(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")

def normalize_base_url(base_url: str) -> str:
    """规范化 Base URL，避免用户填写了 /v1 导致拼接成 /v1/v1/chat/completions"""
    s = (base_url or "").strip()
    if s.endswith("/v1") or s.endswith("/v1/"):
        try:
            idx = s.rfind("/v1")
            s = s[:idx]
        except Exception:
            pass
    return s

def is_siliconflow(base_url: str) -> bool:
    """判断是否为 SiliconFlow 平台（用于 VLM 消息格式）"""
    try:
        return "siliconflow.cn" in (base_url or "").lower()
    except Exception:
        return False

def guess_mime_from_ext(ext: str) -> str:
    ext = (ext or "").lower()
    mapping = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif",
        ".webp": "image/webp", ".bmp": "image/bmp",
        ".svg": "image/svg+xml", ".tif": "image/tiff", ".tiff": "image/tiff",
        ".heic": "image/heic", ".ico": "image/x-icon",
    }
    return mapping.get(ext, "application/octet-stream")

def build_vision_src(md_path: Path, img_src: str) -> Optional[str]:
    """
    返回用于 VLM 的 image_url：
    - 远程：直接使用原始 URL
    - 本地：转换为 data URL（data:<mime>;base64,<payload>）
    """
    try:
        if is_remote_url(img_src):
            return img_src
        # 更稳健的本地路径解析
        p = resolve_local_image(md_path.parent, img_src)
        if not p or not p.exists():
            return None
        data = p.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        mime = guess_mime_from_ext(p.suffix)
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None

def split_md_target(raw: str) -> Tuple[str, str]:
    s = raw.strip()
    if s.startswith("<") and ">" in s:
        end = s.find(">")
        url = s[1:end].strip()
        trailing = s[end + 1:].rstrip()
        return url, (" " + trailing) if trailing else ""
    parts = s.split()
    if not parts:
        return "", ""
    url = parts[0].strip()
    trailing = s[len(parts[0]):].rstrip()
    return url, trailing if trailing.startswith(" ") else ((" " + trailing) if trailing else "")

def extract_doc_title(text: str, md_path: Path) -> str:
    m = re.match(r"^---\s*(.*?)\s*---", text, flags=re.DOTALL)
    if m:
        fm = m.group(1)
        for key in ["parent", "title", "Parent", "Title"]:
            km = re.search(rf"^\s*{key}\s*:\s*(.+)$", fm, flags=re.MULTILINE)
            if km:
                candidate = km.group(1).strip().strip("'\"")
                if candidate:
                    return sanitize_intent_for_language(candidate)
    for line in text.splitlines():
        l = line.strip()
        if l.startswith("#"):
            ttl = l.lstrip("#").strip()
            if ttl:
                return sanitize_intent_for_language(ttl)
    return sanitize_intent_for_language(md_path.stem)

# -----------------------------
# 块级解析（简化 parser）
# -----------------------------

@dataclass
class Block:
    kind: str         # heading / paragraph / list / table / code / quote / image / html / blank
    start: int        # 文本起始偏移
    end: int          # 文本结束偏移
    text: str         # 块原文
    line_start: int   # 起始行号（1-based）
    line_end: int     # 结束行号（1-based）

@dataclass
class ImageRef:
    kind: str   # md / html / wikilink
    src: str
    start: int
    end: int
    line: int
    alt: Optional[str] = None
    title: Optional[str] = None

def classify_line(line: str) -> str:
    s = line.strip()
    if not s:
        return "blank"
    if s.startswith("#"):
        return "heading"
    if s.startswith("```"):
        return "code_fence"
    if s.startswith(">"):
        return "quote"
    if s.startswith("<img") or s.startswith("<figure") or s.startswith("<table"):
        return "html"
    if re.match(r"^\s*[-*+]\s+", s) or re.match(r"^\s*\d+\.\s+", s):
        return "list"
    if s.startswith("|") and s.endswith("|"):
        return "table"
    # 图片语法行（粗略）
    if "![“" in line or "![" in line or re.search(r"<img\b", line, re.IGNORECASE):
        return "maybe_image"
    return "paragraph"

def parse_blocks(md_text: str) -> List[Block]:
    blocks: List[Block] = []
    lines = md_text.splitlines()
    pos = 0
    i = 0
    in_code = False
    block_start_pos = 0
    block_start_line = 1
    block_kind = None
    buff: List[str] = []

    def flush(kind: str, start_p: int, end_p: int, start_l: int, end_l: int, text: str):
        blocks.append(Block(kind=kind, start=start_p, end=end_p, text=text, line_start=start_l, line_end=end_l))

    while i < len(lines):
        line = lines[i]
        line_len = len(line) + 1  # include newline
        lc = classify_line(line)

        if lc == "code_fence":
            if not in_code:
                if buff:
                    flush(block_kind or "paragraph", block_start_pos, pos, block_start_line, i, "\n".join(buff))
                    buff = []
                in_code = True
                block_kind = "code"
                block_start_pos = pos
                block_start_line = i + 1
                buff.append(line)
            else:
                buff.append(line)
                flush("code", block_start_pos, pos + line_len, block_start_line, i + 1, "\n".join(buff))
                buff = []
                in_code = False
                block_kind = None
            pos += line_len
            i += 1
            continue

        if in_code:
            buff.append(line)
            pos += line_len
            i += 1
            continue

        if lc in ("heading", "html", "table", "quote", "list", "paragraph", "maybe_image"):
            if not buff:
                block_kind = lc if lc != "maybe_image" else "paragraph"
                block_start_pos = pos
                block_start_line = i + 1
            buff.append(line)
        else:  # blank
            if buff:
                flush(block_kind or "paragraph", block_start_pos, pos, block_start_line, i, "\n".join(buff))
                buff = []
                block_kind = None
            # 记录空白块也可帮助章节划分
            flush("blank", pos, pos + line_len, i + 1, i + 1, line)

        pos += line_len
        i += 1

    if buff:
        flush(block_kind or "paragraph", block_start_pos, pos, block_start_line, i, "\n".join(buff))

    return blocks

def collect_images(md_text: str) -> List[ImageRef]:
    refs: List[ImageRef] = []
    for m in MD_IMAGE_RE.finditer(md_text):
        alt = m.group(1).strip() or None
        raw_target = m.group(2)
        url, trailing = split_md_target(raw_target)
        title = None
        tm = re.search(r'(".*?"|\'.*?\')', trailing or "")
        if tm:
            title = tm.group(0).strip('"').strip("'")
        refs.append(ImageRef("md", url, m.start(), m.end(), md_text[:m.start()].count("\n") + 1, alt=alt, title=title))
    for m in HTML_IMG_RE.finditer(md_text):
        start = m.start()
        prev = md_text[max(0, start - 3):start]
        if prev.endswith("![") or prev.endswith("![\\"):
            continue
        refs.append(ImageRef("html", m.group(1).strip(), start, m.end(), md_text[:start].count("\n") + 1))
    for m in WIKILINK_EMBED_RE.finditer(md_text):
        inside = m.group(1).strip()
        target = inside.split("|", 1)[0].strip()
        refs.append(ImageRef("wikilink", target, m.start(), m.end(), md_text[:m.start()].count("\n") + 1))
    return refs


def normalize_embedded_html_images(md_text: str) -> Tuple[str, int]:
    pattern = re.compile(r'!\[(?:\\?<img[^>]*data-attachment-key="([^"]+)"[^>]*>)\s*\|[^]]*\]\(([^)]+)\)')
    def repl(match: re.Match) -> str:
        key = match.group(1) or "image"
        target = match.group(2)
        return f"![{key}]({target})"
    new_text, count = pattern.subn(repl, md_text)
    return new_text, count

def text_between(md_text: str, start: int, end: int) -> str:
    raw = md_text[start:end]
    # 去除 YAML Front Matter（避免把 tags/parent/collections 等元数据混入“上文/下文”）
    raw = re.sub(r"^---\s*.*?\s*---\s*", "", raw, flags=re.DOTALL)
    # 去除代码块
    raw = re.sub(r"```.*?```", "", raw, flags=re.DOTALL)
    # 去除 HTML 标签与 <img>（保底）
    raw = re.sub(r"<[^>]+>", "", raw)
    # 去除 Markdown 普通链接 [text](url)
    raw = re.sub(r"\[[^\]]+\]\([^)]+\)", "", raw)
    # 关键：去除 Markdown 图片语法与 Obsidian 图片嵌入，避免图片语句进入“上/下文”
    # ![alt](url "title") / ![alt](<url> "title")
    raw = MD_IMAGE_RE.sub("", raw)
    # ![[path|alias]] / ![[path]]
    raw = WIKILINK_EMBED_RE.sub("", raw)
    # 去除疑似图片地址（裸露的 *.png/jpg/...），避免如 “attachment/xxx.jpg” 进入文本
    raw = re.sub(r"(?i)\b\S+\.(?:png|jpe?g|gif|webp|bmp|svg|tiff?|ico|heic)\b", "", raw)
    # 去除常见元数据行与分隔线
    raw = re.sub(r"(?mi)^(tags\s*:.*|parent\s*:.*|collections\s*:.*|\$version\s*:.*|\$libraryID\s*:.*|\$itemKey\s*:.*)\s*$", "", raw)
    raw = re.sub(r"(?m)^\s*(\*{3,}|-{3,}|_{3,})\s*$", "", raw)
    # 压缩空白
    raw = WHITESPACE_RE.sub(" ", raw).strip()
    return raw

def has_caption_clues(s: str) -> bool:
    if not s:
        return False
    return any(c in s for c in CAPTION_CLUES)

def find_explicit_refs(s: str) -> List[str]:
    out = []
    for pat in EXPLICIT_REF_PATTERNS:
        for m in re.finditer(pat, s):
            out.append(m.group(0))
    return out

def find_neighbor_text(md_text: str, refs: List[ImageRef], idx: int) -> Tuple[str, str, str, List[str]]:
    """返回 (above_text, below_text, between_text, explicit_refs)"""
    this = refs[idx]
    prev_end = refs[idx - 1].end if idx > 0 else 0
    next_start = refs[idx + 1].start if idx + 1 < len(refs) else len(md_text)
    above = text_between(md_text, prev_end, this.start)
    below = text_between(md_text, this.end, next_start)
    between = above  # 定义区间 = 上一图到当前图的文字
    explicit = find_explicit_refs(above + " " + below)
    return above, below, between, explicit

def _collect_explicit_matches_with_spans(s: str) -> List[Tuple[int, int, str]]:
    """收集显式引用短语的 span，用于“按文字指示”决定侧向与句子聚焦。"""
    matches: List[Tuple[int, int, str]] = []
    if not s:
        return matches
    for pat in EXPLICIT_REF_PATTERNS:
        for m in re.finditer(pat, s):
            matches.append((m.start(), m.end(), pat))
    return matches

def _extract_sentence_around(s: str, start: int, end: int) -> str:
    """提取包含显式引用的句子（以中英文句号/问号/感叹号/分号或换行为边界）。"""
    if not s:
        return ""
    left = start
    right = end
    # 向左找到句子起点
    while left > 0 and s[left - 1] not in "。！？；;.!?\n":
        left -= 1
    # 向右找到句子终点
    while right < len(s) and s[right] not in "。！？；;.!?\n":
        right += 1
    sent = s[left:right].strip()
    if sent:
        return WHITESPACE_RE.sub(" ", sent).strip()
    # 兜底：取附近片段
    l2 = max(0, start - 50)
    r2 = min(len(s), end + 200)
    return WHITESPACE_RE.sub(" ", s[l2:r2]).strip()

def explicit_override_and_focus(default_strategy: str, above: str, below: str) -> Tuple[Optional[str], str, str]:
    """
    依据显式引用短语决定“方案一/方案二”的智能覆盖，并将被指示侧的文本聚焦到包含短语的句子：
    - default_strategy 为用户选择的方案（"above" 或 "below"）
    - 返回 (override_side, above_focus, below_focus)
      - override_side: "above"/"below"/None（None 表示不覆盖，沿用默认）
      - above_focus/below_focus: 若某侧有显式短语，则仅取包含该短语的句子；否则保留原文本
    """
    m_above = _collect_explicit_matches_with_spans(above)
    m_below = _collect_explicit_matches_with_spans(below)

    above_focus = above
    below_focus = below
    override_side: Optional[str] = None

    if m_above or m_below:
        if len(m_below) > len(m_above):
            override_side = "below"
            s = _extract_sentence_around(below, m_below[0][0], m_below[0][1])
            if s:
                below_focus = s
        elif len(m_above) > len(m_below):
            override_side = "above"
            s = _extract_sentence_around(above, m_above[0][0], m_above[0][1])
            if s:
                above_focus = s
        else:
            # 数量相同：按默认方案优先侧
            if default_strategy == "below" and m_below:
                override_side = "below"
                s = _extract_sentence_around(below, m_below[0][0], m_below[0][1])
                if s:
                    below_focus = s
            elif default_strategy == "above" and m_above:
                override_side = "above"
                s = _extract_sentence_around(above, m_above[0][0], m_above[0][1])
                if s:
                    above_focus = s
            else:
                # 兜底：优先下面（常见“如下图所示”），否则上面
                if m_below:
                    override_side = "below"
                    s = _extract_sentence_around(below, m_below[0][0], m_below[0][1])
                    if s:
                        below_focus = s
                elif m_above:
                    override_side = "above"
                    s = _extract_sentence_around(above, m_above[0][0], m_above[0][1])
                    if s:
                        above_focus = s

    return override_side, above_focus, below_focus

# -----------------------------
# SCI 图注分析辅助
# -----------------------------

SCI_FIG_LABEL_RE = re.compile(r"\bFig(?:ure)?\.?\s*(?P<prefix>[Ss])?\s*(?P<num>\d+)(?P<letter>[A-Za-z])?", re.IGNORECASE)
SCI_FIG_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9])([sS]?)(?:fig|figure)[_\-\s]*(\d+)([a-z])?(?![A-Za-z0-9])",
    re.IGNORECASE,
)
SCI_PANEL_MARK_RE = re.compile(r"[\(\[]\s*([A-Z])\s*[\)\]]")
SCI_PANEL_INLINE_RE = re.compile(r"(?:^|[;,\.\s])([A-H])(?:[\.:]\s*|,\s+)", re.IGNORECASE)


def _normalize_fig_identifier(prefix: Optional[str], number: str) -> Optional[str]:
    if not number:
        return None
    clean_num = re.sub(r"[^0-9A-Za-z\-]+", "", number)
    if not clean_num:
        return None
    prefix_clean = (prefix or "").strip().upper()
    clean_num = clean_num.upper()
    return f"{prefix_clean}{clean_num}" if prefix_clean else clean_num


def _extract_fig_from_text(text: Optional[str]) -> Optional[Tuple[str, Optional[str]]]:
    if not text:
        return None
    match = SCI_FIG_LABEL_RE.search(text)
    if not match:
        return None
    figure = _normalize_fig_identifier(match.group("prefix"), match.group("num"))
    if not figure:
        return None
    letter = match.group("letter")
    panel = letter.upper() if letter else None
    return figure, panel


def _extract_fig_from_name(name: Optional[str]) -> Optional[Tuple[str, Optional[str]]]:
    if not name:
        return None
    match = SCI_FIG_TOKEN_RE.search(name)
    if not match:
        return None
    prefix_flag = match.group(1) or ""
    number = match.group(2) or ""
    letter = match.group(3)
    figure = _normalize_fig_identifier("S" if prefix_flag.lower() == "s" else "", number)
    if not figure:
        return None
    panel = letter.upper() if letter else None
    return figure, panel


def _extract_panel_letter_hint(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    normalized = text.replace("（", "(").replace("）", ")")
    mark = SCI_PANEL_MARK_RE.search(normalized)
    if mark:
        return mark.group(1).upper()
    inline = SCI_PANEL_INLINE_RE.search(normalized)
    if inline:
        return inline.group(1).upper()
    return None


def _collect_panel_markers(text: Optional[str]) -> Tuple[List[str], Dict[str, str]]:
    markers: List[str] = []
    segments: Dict[str, str] = {}
    if not text:
        return markers, segments
    normalized = text.replace("（", "(").replace("）", ")")
    matches = list(SCI_PANEL_MARK_RE.finditer(normalized))
    if matches:
        for idx, match in enumerate(matches):
            letter = match.group(1).upper()
            if letter not in markers:
                markers.append(letter)
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(normalized)
            segment = normalized[start:end].strip()
            segment = re.sub(r"^[\s\u3000\.;:,\-]+", "", segment)
            segment = re.sub(r"\s+", " ", segment)
            if segment:
                segments[letter] = segment
    else:
        matches_inline = list(SCI_PANEL_INLINE_RE.finditer(normalized))
        if matches_inline:
            for idx, match in enumerate(matches_inline):
                letter = match.group(1).upper()
                if letter not in markers:
                    markers.append(letter)
                start = match.end()
                end = matches_inline[idx + 1].start() if idx + 1 < len(matches_inline) else len(normalized)
                segment = normalized[start:end].strip()
                segment = re.sub(r"^[\s\u3000\.;:,\-]+", "", segment)
                segment = re.sub(r"\s+", " ", segment)
                if segment:
                    segments[letter] = segment
    return markers, segments


def _extract_src_stem(src: Optional[str]) -> Optional[str]:
    if not src:
        return None
    cleaned = src.strip().split("#", 1)[0].split("?", 1)[0]
    cleaned = cleaned.replace("\\", "/")
    if "/" in cleaned:
        cleaned = cleaned.rsplit("/", 1)[-1]
    if not cleaned:
        return None
    try:
        return Path(cleaned).stem
    except Exception:
        return cleaned


def _clean_sci_summary(summary: Optional[str]) -> str:
    if not summary:
        return ""
    text = WHITESPACE_RE.sub(" ", summary).strip()
    text = re.sub(r"^(?:fig(?:ure)?\.?\s*[Ss]?\s*\d+[A-Za-z]?\s*[:\-\.,]*)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^[\s:;,\-\.]+", "", text)
    text = text.strip()
    return text[:80]


def build_sci_metadata(
    ref_src: Optional[str],
    alt: Optional[str],
    title_attr: Optional[str],
    above: str,
    below: str,
    above_focus: str,
    below_focus: str,
    block_index: int,
    image_index: int,
) -> Dict[str, object]:
    figure: Optional[str] = None
    panel: Optional[str] = None

    for candidate in (below_focus, below, above_focus, above, alt or "", title_attr or ""):
        info = _extract_fig_from_text(candidate)
        if info:
            fig_val, panel_val = info
            if fig_val and not figure:
                figure = fig_val
            if panel_val and not panel:
                panel = panel_val
            if figure and panel:
                break

    stem = _extract_src_stem(ref_src)
    if stem:
        info_name = _extract_fig_from_name(stem)
        if info_name:
            fig_val, panel_val = info_name
            if fig_val and not figure:
                figure = fig_val
            if panel_val and not panel:
                panel = panel_val
        info_text = _extract_fig_from_text(stem)
        if info_text:
            fig_val, panel_val = info_text
            if fig_val and not figure:
                figure = fig_val
            if panel_val and not panel:
                panel = panel_val
        if not figure:
            digits = re.search(r"(\d+)", stem)
            if digits:
                figure = digits.group(1)

    panel_sequence, panel_segments = _collect_panel_markers(below or below_focus)
    if panel_sequence and (not panel):
        idx = (image_index - 1) if image_index and image_index > 0 else 0
        if 0 <= idx < len(panel_sequence):
            panel = panel_sequence[idx]

    if not panel:
        panel_hint = _extract_panel_letter_hint(alt) or _extract_panel_letter_hint(title_attr)
        if panel_hint:
            panel = panel_hint

    fallback_block = str(block_index) if block_index else None

    return {
        "figure": figure,
        "panel": panel,
        "panel_sequence": panel_sequence,
        "panel_segments": panel_segments,
        "fallback_block": fallback_block,
    }

# -----------------------------
# OpenAI 兼容调用与 JSON 解析
# -----------------------------

def getenv_default(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name)
    return v if v else default

def prompt_for_api_key_if_missing(api_key: Optional[str]) -> str:
    if api_key:
        return api_key
    print("请输入 OpenAI API Key（按回车确认）：", end="", flush=True)
    try:
        return input().strip()
    except Exception:
        return ""

# 记录最近一次 LLM 调用错误，便于 GUI/报告展示
_LAST_LLM_ERROR: Optional[str] = None

def set_last_llm_error(msg: Optional[str]) -> None:
    global _LAST_LLM_ERROR
    _LAST_LLM_ERROR = msg

def get_last_llm_error() -> Optional[str]:
    return _LAST_LLM_ERROR

def call_openai_chat(base_url: str, api_key: str, model: str, messages: List[Dict], timeout: int = 90, max_retries: int = 3, rate_limit: float = 0.0, verbose: bool = False, expect_json: bool = True) -> Optional[str]:
    if requests is None:
        print("⚠️ 缺少 requests 库，请先安装：pip install requests")
        return None
    base = normalize_base_url(base_url)
    url = base.rstrip('/') + '/v1/chat/completions'
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    set_last_llm_error(None)
    payload = {"model": model, "messages": messages, "temperature": 0.0, "max_tokens": 512}
    if expect_json and is_siliconflow(base):
        payload['response_format'] = {"type": "json_object"}

    def flatten_text(value: object) -> List[str]:
        acc: List[str] = []

        def _collect(v: object) -> None:
            if isinstance(v, str):
                s = v.strip()
                if s:
                    acc.append(s)
            elif isinstance(v, list):
                for item in v:
                    _collect(item)
            elif isinstance(v, dict):
                for key in ("text", "content", "output", "message", "value"):
                    if key in v:
                        _collect(v[key])

        _collect(value)
        return acc

    last_err = None
    for attempt in range(max_retries + 1):
        try:
            if rate_limit > 0:
                time.sleep(rate_limit)
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            try:
                parsed = data.get('choices', [{}])[0].get('message', {}).get('parsed')
            except Exception:
                parsed = None
            if expect_json and isinstance(parsed, (dict, list)):
                try:
                    return json.dumps(parsed, ensure_ascii=False)
                except Exception:
                    pass

            content_obj = None
            try:
                content_obj = data.get('choices', [{}])[0].get('message', {}).get('content')
            except Exception:
                content_obj = None
            content = ""
            if isinstance(content_obj, str):
                content = content_obj
            elif isinstance(content_obj, list):
                parts: List[str] = []
                for part in content_obj:
                    parts.extend(flatten_text(part))
                content = "\n".join(parts)
            else:
                content = data.get('choices', [{}])[0].get('text') or data.get('content') or ""

            if not expect_json:
                if isinstance(content, str) and content.strip():
                    return content
                if parsed is not None:
                    try:
                        if isinstance(parsed, str) and parsed.strip():
                            return parsed
                        if isinstance(parsed, list):
                            texts: List[str] = []
                            for x in parsed:
                                if isinstance(x, str) and x.strip():
                                    texts.append(x.strip())
                                elif isinstance(x, dict):
                                    t = x.get('text') or x.get('content') or x.get('output') or ''
                                    if isinstance(t, str) and t.strip():
                                        texts.append(t.strip())
                                else:
                                    s = str(x).strip()
                                    if s:
                                        texts.append(s)
                            flat = "\n".join(texts).strip()
                            if flat:
                                return flat
                        if isinstance(parsed, dict):
                            for k in ('text', 'content', 'output', 'message'):
                                v = parsed.get(k)
                                if isinstance(v, str) and v.strip():
                                    return v
                            return json.dumps(parsed, ensure_ascii=False)
                    except Exception:
                        pass

            return content if content is not None else None
        except Exception as e:
            last_err = e
            detail = f"{type(e).__name__}: {e}"
            resp = getattr(e, 'response', None)
            status = None
            body_snip = ''
            err_payload: Optional[Dict] = None
            if resp is not None:
                status = getattr(resp, 'status_code', None)
                try:
                    err_payload = resp.json()
                    body_snip = json.dumps(err_payload, ensure_ascii=False)[:300]
                except Exception:
                    try:
                        body_snip = resp.text[:300]
                    except Exception:
                        body_snip = ''
            if (
                is_siliconflow(base)
                and payload.get('response_format')
                and isinstance(err_payload, dict)
                and err_payload.get('code') in {20012, 20015, 20016, 20024, 20029}
            ):
                payload.pop('response_format', None)
                if verbose:
                    print('⚙️ 检测到 SiliconFlow 不支持 response_format，退回普通解析后重试')
                time.sleep(0.6)
                continue
            if status is not None:
                detail = f"{detail} | status={status} body={body_snip}"
            set_last_llm_error(detail)
            if verbose:
                print(f"⚠️ 模型调用失败（第{attempt + 1}次）：{detail}")
            time.sleep(0.8)
    if verbose:
        print(f"⚠️ 模型连续失败，最后错误：{last_err}")
    if last_err is not None and not get_last_llm_error():
        set_last_llm_error(str(last_err))
    return None


def build_ai_messages(
    doc_title: str,
    above: str,
    below: str,
    between: str,
    explicit_refs: List[str],
    alt: Optional[str],
    title: Optional[str],
    vision_src: Optional[str] = None,
    base_url: Optional[str] = None,
    intent_language: str = DEFAULT_INTENT_LANGUAGE,
    reason_language: str = DEFAULT_REASON_LANGUAGE,
) -> List[Dict]:
    """
    消息构造（文本与多模态）：
    - OpenAI/兼容（纯文本）：messages[].content 为字符串（JSON 载荷）
    - SiliconFlow VLM（视觉理解开启时）：messages[].content 为数组
      - 文本：{"type":"text","text": "...JSON 载荷字符串..."}
      - 视觉（仅在启用时附加）：{"type":"image_url","image_url":{"url": "...", "detail": "auto"}}
    要求模型输出严格 JSON：
    {
      "candidates": [
        {"strategy": "above", "title": "短语", "reason": "依据", "confidence": 0.0},
        {"strategy": "below", "title": "短语", "reason": "依据", "confidence": 0.0},
        {"strategy": "intent", "title": "短语", "reason": "依据", "confidence": 0.0}
      ],
      "best": "intent",
      "normalized_title": "用于文件名的清洗版"
    }
    """
    intent_language = (intent_language or DEFAULT_INTENT_LANGUAGE).lower()
    reason_language = (reason_language or DEFAULT_REASON_LANGUAGE).lower()
    english_mode = intent_language.startswith("en")
    sys_prompt = (
        "你是教材风格的命名助手。严格遵循：只输出一个 JSON 对象，不得包含任何说明性文字、前后缀、代码块围栏`、注释或省略号（.../……）。"
        "基于提供的上下文与线索，输出严格 JSON（不含多余文本）。"
        "根据 instructions.title_language 生成 normalized_title，根据 instructions.reason_language 编写 candidates[].reason，确保语义准确、语言一致。"
        "为图片生成不少于三种“图意”候选，字段 candidates[].strategy/title/reason/confidence。"
        "best 为建议采用策略；normalized_title 应满足 instructions.term_length_range 限制，突出核心术语或对象关系，避免标点、引号、编号和冗余修饰。"
        "请充分利用 context_hints：其中 above.sentences 按 priority 排列（priority=1 表示最靠近图片上方的句子，数字越大越远，可结合多条说明理由；若上文仅保留单条，则视为该图片最可能的主要语义）。"
    )
    if english_mode:
        sys_prompt += '当 title_language 为 en-US 时，请输出自然的英文短语，单词之间使用空格，避免连字符或多余标点。'
    if intent_language == "auto":
        sys_prompt += "当 title_language 为 'match_source' 时，请保持输出与参考文本一致的语言，不要擅自翻译。"
    # 将文本截断到合理长度，避免提示过长
    def clip(s: str, n: int) -> str:
        s = s.strip()
        if len(s) <= n:
            return s
        return s[: n - 3] + "..."
    above_c = clip(above, 800)
    below_c = clip(below, 800)
    between_c = clip(between, 800)
    explicit_c = ", ".join(explicit_refs[:5]) if explicit_refs else ""
    alt_c = alt or ""
    title_c = title or ""
    sentence_split_re = re.compile(r"[。！？!?；;]+|\n+")

    def make_priority_list(text: str, prefer_tail: bool) -> List[Dict[str, object]]:
        text = (text or "").strip()
        if not text:
            return []
        segments = [seg.strip() for seg in sentence_split_re.split(text) if seg.strip()]
        if not segments:
            return []
        limit = 6
        if prefer_tail:
            segments = segments[-limit:]
            segments = list(reversed(segments))
        else:
            segments = segments[:limit]
        return [{"priority": idx, "text": seg} for idx, seg in enumerate(segments, start=1)]

    above_segments = make_priority_list(above_c, prefer_tail=True)
    below_segments = make_priority_list(below_c, prefer_tail=False)
    intent_locale = LANGUAGE_LOCALES.get(intent_language)
    if intent_locale is None and intent_language != "auto":
        intent_locale = LANGUAGE_LOCALES.get("zh")
    reason_locale = LANGUAGE_LOCALES.get(reason_language, LANGUAGE_LOCALES.get('zh'))
    term_length_range = [6, 32] if english_mode else [6, 16]
    if intent_language == "auto":
        title_language_instr = "match_source"
    else:
        title_language_instr = intent_locale or LANGUAGE_LOCALES.get("zh")

    user_payload = {
        "document_title": doc_title,
        "above_text": above_c,
        "below_text": below_c,
        "between_text": between_c,
        "explicit_refs": explicit_c,
        "alt_text": alt_c,
        "title_text": title_c,
        "instructions": {
            "strategies_required": ["above", "below", "intent"],
            "caption_priority": True,
            "title_language": title_language_instr,
            "reason_language": reason_locale,
            "term_length_range": term_length_range,
        },
        "context_hints": {
            "above": {
                "note": "priority=1 表示最靠近图片上方的句子，数字越大越远，可结合多条说明理由。",
                "sentences": above_segments,
            },
            "below": {
                "note": "priority=1 表示紧挨图片后的句子，数字越大越远。",
                "sentences": below_segments,
            },
            "between": {
                "text": between_c,
            },
        },
    }
    # 仅在 SiliconFlow 且启用视觉理解时，使用数组 content；否则退回纯文本消息
    use_sf_vlm = bool(base_url and is_siliconflow(base_url) and vision_src)
    if use_sf_vlm:
        image_part: Dict[str, object] = {
            "type": "image_url",
            "image_url": {"url": vision_src, "detail": "auto"},
        }
        user_content = [
            {"type": "text", "text": json.dumps(user_payload, ensure_ascii=False)},
            image_part,
        ]
        messages = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_content}]
    else:
        messages = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}]
    return messages


def truncate_text(s: str, limit: int = 200) -> str:
    if not isinstance(s, str):
        s = str(s)
    s = s.strip()
    return s if len(s) <= limit else s[: limit - 1] + "…"


def summarize_messages(messages: List[Dict]) -> List[Dict]:
    """
    为日志/调试生成消息摘要，避免输出过长或泄露二进制数据。
    """
    summary: List[Dict] = []
    for msg in messages:
        entry: Dict[str, object] = {"role": msg.get("role", "")}
        content = msg.get("content")
        if isinstance(content, str):
            entry["text"] = truncate_text(content, 240)
        elif isinstance(content, list):
            parts_summary: List[Dict[str, object]] = []
            for part in content:
                if not isinstance(part, dict):
                    parts_summary.append({"type": "unknown"})
                    continue
                p_type = part.get("type", "unknown")
                if p_type == "text":
                    parts_summary.append(
                        {"type": "text", "text": truncate_text(part.get("text", ""), 200)}
                    )
                elif p_type in {"image_url", "video_url", "audio_url"}:
                    payload = part.get(p_type)
                    url = ""
                    detail = None
                    if isinstance(payload, dict):
                        url = payload.get("url", "")
                        detail = payload.get("detail")
                    else:
                        url = payload
                    if isinstance(url, str) and url.startswith("data:"):
                        meta = url.split(",", 1)[0]
                        url_summary = f"{meta}...(len={len(url)})"
                    else:
                        url_summary = url
                    part_info: Dict[str, object] = {"type": p_type, "url": truncate_text(url_summary, 200)}
                    if detail:
                        part_info["detail"] = detail
                    parts_summary.append(part_info)
                else:
                    parts_summary.append({"type": p_type})
            entry["parts"] = parts_summary
        summary.append(entry)
    return summary



def build_ai_batch_messages(
    doc_title: str,
    batch_items: List[Dict],
    base_url: Optional[str] = None,
    intent_language: str = DEFAULT_INTENT_LANGUAGE,
    reason_language: str = DEFAULT_REASON_LANGUAGE,
) -> List[Dict]:
    intent_language = (intent_language or DEFAULT_INTENT_LANGUAGE).lower()
    reason_language = (reason_language or DEFAULT_REASON_LANGUAGE).lower()
    intent_locale = LANGUAGE_LOCALES.get(intent_language)
    if intent_locale is None and intent_language != "auto":
        intent_locale = LANGUAGE_LOCALES.get("zh")
    reason_locale = LANGUAGE_LOCALES.get(reason_language, LANGUAGE_LOCALES.get("zh"))
    english_mode = intent_language.startswith("en")
    term_length_range = [6, 32] if english_mode else [6, 16]
    if intent_language == "auto":
        title_language_instr = "match_source"
    else:
        title_language_instr = intent_locale or LANGUAGE_LOCALES.get("zh")

    """
    构造多张图片批量请求的 messages（仅文本模式）。
    要求模型返回 JSON 对象：{"items": [ {...}, ... ]}
    其中每个元素结构与单张图片时的返回一致，并携带 index 字段。
    """
    sys_prompt = (
        "你是教材风格的命名助手。严格遵循：只输出一个 JSON 对象 items，不得额外添加说明文字。"
        "为每张图片生成 candidates[].strategy/title/reason/confidence，best 为建议采用策略。"
        "normalized_title 应使用 instructions.title_language 指定的语言，并满足 instructions.term_length_range 限制。"
        "candidates[].reason 必须使用 instructions.reason_language 指定的语言，语言风格保持一致。"
        "返回格式为 {\"items\":[{...}]}，items 中每个元素带有 index。"
    )
    if english_mode:
        sys_prompt += '当 title_language 为 en-US 时，请输出自然的英文短语，单词之间使用空格，避免连字符或多余标点。'
    if intent_language == "auto":
        sys_prompt += "当 title_language 为 'match_source' 时，请保持输出与原文语言一致。"
    def clip(s: str, n: int) -> str:
        s = s.strip()
        if len(s) <= n:
            return s
        return s[: n - 3] + "..."

    images_payload: List[Dict] = []
    for item in batch_items:
        explicit_refs = item.get("explicit_refs", [])
        payload = {
            "index": item["index"],
            "strategy_hint": item.get("effective_strategy"),
            "above_text": clip(item.get("above_focus", ""), 800),
            "below_text": clip(item.get("below_focus", ""), 800),
            "between_text": clip(item.get("between", ""), 800),
            "explicit_refs": ", ".join(explicit_refs[:5]) if explicit_refs else "",
            "alt_text": item.get("alt") or "",
            "title_text": item.get("title_attr") or ""
        }
        images_payload.append(payload)

    user_payload = {
        "document_title": doc_title,
        "images": images_payload,
        "instructions": {
            "strategies_required": ["above", "below", "intent"],
            "caption_priority": True,
            "title_language": title_language_instr,
            "reason_language": reason_locale,
            "term_length_range": term_length_range
        },
    }
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}
    ]
    return messages
def safe_parse_json(s: Optional[str]) -> Optional[Dict]:
    """
    更健壮的 JSON 解析：
    - 去除 Markdown 代码块围栏（```json ... ``` / ``` ... ```）
    - 剔除前后非 JSON 文本，基于花括号平衡提取首个对象
    - 修复尾随逗号（,} / ,]）等常见非严格 JSON
    """
    if not s:
        return None

    raw = s.lstrip("\ufeff").strip()

    # 1) 优先提取任意位置的代码围栏 ```json ... ``` 或 ``` ... ``` 内的 JSON
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, flags=re.IGNORECASE)
    if fence:
        inner = fence.group(1)
        try:
            return json.loads(inner)
        except Exception:
            # 容错：修复尾随逗号后再试
            inner_fixed = re.sub(r",\s*([}\]])", r"\1", inner)
            try:
                return json.loads(inner_fixed)
            except Exception:
                pass

    # 2) 去除首尾围栏（典型包裹场景）
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)

    # 3) 尝试直接解析
    try:
        return json.loads(raw)
    except Exception:
        pass

    # 2) 基于花括号平衡提取第一个对象子串（忽略引号内的括号）
    def extract_first_object(text: str) -> Optional[str]:
        in_str = False
        esc = False
        depth = 0
        start = -1
        for i, ch in enumerate(text):
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    if depth == 0:
                        start = i
                    depth += 1
                elif ch == "}":
                    if depth > 0:
                        depth -= 1
                        if depth == 0 and start != -1:
                            return text[start : i + 1]
        return None

    candidate = extract_first_object(raw)
    if not candidate:
        # 回退到非贪婪匹配（可能失败于嵌套/字符串内花括号）
        m = re.search(r"\{[\s\S]*?\}", raw)
        candidate = m.group(0) if m else None

    if candidate:
        # 3) 修复尾随逗号
        fixed = re.sub(r",\s*([}\]])", r"\1", candidate)
        # 4) 再尝试解析
        try:
            return json.loads(fixed)
        except Exception:
            # 最后回退：尝试原始片段
            try:
                return json.loads(candidate)
            except Exception:
                return None

    return None

def validate_ai_result(d: Optional[Dict], intent_language: str = DEFAULT_INTENT_LANGUAGE) -> Optional[Dict]:
    """
    接受以下变体：
    - 直接对象：{"candidates":[...], "best":"...", "normalized_title":"..."}
    - 包裹一层：{"result": {...}} 或 {"data": {...}} 或 {"output": {...}}
    - candidates 列表项缺少可选字段时进行填充与清洗
    """
    if not isinstance(d, dict):
        return None

    # 解包常见外层容器
    for key in ("result", "data", "output"):
        if key in d and isinstance(d[key], dict):
            if "candidates" in d[key]:
                d = d[key]
                break

    if "candidates" not in d or not isinstance(d["candidates"], list) or len(d["candidates"]) < 1:
        return None


    for c in d["candidates"]:
        if not isinstance(c, dict):
            return None
        if "strategy" not in c or "title" not in c:
            return None
        c.setdefault("reason", "")
        try:
            conf = float(c.get("confidence", 0.5))
        except Exception:
            conf = 0.5
        c["confidence"] = max(0.0, min(1.0, conf))
        c["title"] = sanitize_intent_for_language(c["title"], intent_language)

    best = d.get("best") or d["candidates"][0].get("strategy", "intent")
    d["best"] = str(best)

    nt = d.get("normalized_title") or d["candidates"][0].get("title") or "图意"
    d["normalized_title"] = sanitize_intent_for_language(nt, intent_language)

    return d

# -----------------------------
# 命名方案与模板
# -----------------------------

def name_with_template(
    template: str,
    title: str,
    block_idx: int,
    img_idx: int,
    intent_phrase: str,
    seq_width: int,
    max_len: int,
    intent_language: str = DEFAULT_INTENT_LANGUAGE,
    global_index: Optional[int] = None,
    dup_index: Optional[int] = None,
) -> str:
    # 支持 {title}、{block}、{idx}、{intent}、{index}、{dup}，其中数字类占位符支持宽度控制
    def fmt_num(n: int, w: int) -> str:
        return f"{n:0{w}d}"
    # 兼容旧模板中 {block:02d}/{idx:02d}/{index:02d} 风格
    def replace_num_fields(tmpl: str) -> str:
        tmpl = re.sub(r"\{block:(\d+)d\}", lambda m: fmt_num(block_idx, int(m.group(1))), tmpl)
        tmpl = re.sub(r"\{idx:(\d+)d\}", lambda m: fmt_num(img_idx, int(m.group(1))), tmpl)
        if global_index is not None:
            tmpl = re.sub(r"\{index:(\d+)d\}", lambda m: fmt_num(global_index, int(m.group(1))), tmpl)
        else:
            tmpl = re.sub(r"\{index:(\d+)d\}", lambda m: fmt_num(img_idx, int(m.group(1))), tmpl)
        if dup_index is not None:
            tmpl = re.sub(r"\{dup:(\d+)d\}", lambda m: fmt_num(dup_index, int(m.group(1))), tmpl)
        else:
            tmpl = re.sub(r"\{dup:(\d+)d\}", lambda m: fmt_num(img_idx, int(m.group(1))), tmpl)
        return tmpl
    tmpl = replace_num_fields(template)
    # 若模板包含裸 {index}，在映射中提供格式化后的值
    index_formatted = fmt_num(global_index if global_index is not None else img_idx, seq_width)
    dup_formatted = fmt_num(dup_index if dup_index is not None else img_idx, seq_width)
    # 清理意图短语中可能混入的图片扩展名，避免出现 “...png.png”
    intent_clean = re.sub(r"(?i)\.(?:png|jpe?g|gif|webp|bmp|svg|tiff?|ico|heic)\b", "", intent_phrase)
    mapping = {
        "title": title,
        "intent": intent_clean,
        "block": fmt_num(block_idx, seq_width),
        "idx": fmt_num(img_idx, seq_width),
        "index": index_formatted,
        "dup": dup_formatted,
    }

    text_field_pattern = re.compile(r"\{(?P<key>title|intent)(?::\.?(?P<limit>\d+))?\}")

    def replace_text_fields(tmpl: str) -> str:
        def repl(match: re.Match) -> str:
            key = match.group("key")
            limit = match.group("limit")
            value = mapping.get(key, "")
            if limit:
                try:
                    n = max(0, int(limit))
                    value = value[:n]
                except Exception:
                    pass
            return value

        return text_field_pattern.sub(repl, tmpl)

    out = replace_text_fields(tmpl)
    for k, v in mapping.items():
        if k in ("title", "intent"):
            continue
        out = out.replace("{" + k + "}", v)
    out = sanitize_intent_for_language(out, intent_language)
    # 如模板或意图末尾仍出现扩展名，去除以防重复扩展
    out = re.sub(r"(?i)\.(?:png|jpe?g|gif|webp|bmp|svg|tiff?|ico|heic)$", "", out)
    return out[:max_len].rstrip(" ._")

# -----------------------------
# 下载与重写链接
# -----------------------------

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ai-image-intent-namer/1.0"
ACCEPT_HEADER = "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"

def guess_ext_from_url_or_headers(url: str, content_type: Optional[str]) -> str:
    ext = Path(url).suffix.lower()
    if ext in IMAGE_EXTS:
        return ext
    ct_map = {
        "image/jpeg": ".jpg", "image/jpg": ".jpg",
        "image/png": ".png", "image/gif": ".gif",
        "image/webp": ".webp", "image/bmp": ".bmp",
        "image/svg+xml": ".svg", "image/tiff": ".tiff",
        "image/x-icon": ".ico", "image/heic": ".heic",
    }
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        if ct in ct_map:
            return ct_map[ct]
    return ".img"

def download_image(url: str, dest_dir: Path, timeout: int) -> Optional[Path]:
    if requests is None:
        print("❌ 缺少 requests 库，请先安装：pip install requests")
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": USER_AGENT, "Accept": ACCEPT_HEADER}
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        ext = guess_ext_from_url_or_headers(url, r.headers.get("Content-Type"))
        name = sanitize_intent_for_language(Path(url).stem) + ext
        final = ensure_unique_path(dest_dir, name)
        final.write_bytes(r.content)
        return final
    except Exception as e:
        print(f"❌ 下载失败：{url} -> {e}")
        return None


def ensure_attachment_for_src(
    md_path: Path,
    src: str,
    attach_dir: Path,
    timeout: int,
    mapping: Dict[str, Dict],
    prefer_move: bool = True,
) -> Tuple[str, str, Optional[str]]:
    """
    确保图片资源位于附件目录，返回 (新相对路径, 动作, 映射键)：
    动作为 moved / copied / downloaded / reused / already / skipped / error；
    映射键用于后续更新 target 名称。
    """
    md_root = md_path.parent
    attach_dir.mkdir(parents=True, exist_ok=True)
    cleaned_src = (src or "").strip()
    if not cleaned_src:
        return src, "error"
    if is_remote_url(cleaned_src):
        key = f"remote:{cleaned_src}"
        entry = mapping.get(key)
        if entry:
            target_rel = entry.get("target_rel")
            if target_rel:
                target_path = (md_root / Path(target_rel)).resolve()
                if target_path.exists():
                    return target_rel, "reused", key
                else:
                    mapping.pop(key, None)
        saved = download_image(cleaned_src, attach_dir, timeout)
        if not saved:
            return src, "error", key
        target_path = saved.resolve()
        target_rel = _make_rel(target_path, md_root)
        mapping[key] = {
            "type": "remote",
            "url": cleaned_src,
            "target": str(target_path),
            "target_rel": target_rel,
            "hash": _hash_file(target_path),
            "downloaded_at": time.time(),
        }
        return target_rel, "downloaded", key

    # 本地图片
    src_path = resolve_local_image(md_root, cleaned_src)
    if not src_path or not src_path.exists():
        return src, "error", None
    src_path = src_path.resolve()
    try:
        src_path.relative_to(attach_dir.resolve())
        return _make_rel(src_path, md_root), "already", None
    except ValueError:
        pass

    key = f"local:{str(src_path)}"
    entry = mapping.get(key)
    if entry:
        target_rel = entry.get("target_rel")
        if target_rel:
            target_path = (md_root / Path(target_rel)).resolve()
            if target_path.exists():
                return target_rel, "reused", key
            else:
                mapping.pop(key, None)

    original_rel = _make_rel(src_path, md_root)
    target_path = ensure_unique_path(attach_dir, src_path.name).resolve()
    moved = False
    if prefer_move:
        moved = _try_move_file(src_path, target_path)
    if not moved:
        try:
            data = src_path.read_bytes()
            target_path.write_bytes(data)
            try:
                src_path.unlink()
            except Exception:
                pass
            moved = True
            action = "copied"
        except Exception:
            return src, "error", key
    else:
        action = "moved"

    target_rel = _make_rel(target_path, md_root)
    mapping[key] = {
        "type": "local",
        "original": str(src_path),
        "original_rel": original_rel,
        "target": str(target_path),
        "target_rel": target_rel,
        "hash": _hash_file(target_path),
        "moved_at": time.time(),
    }
    return target_rel, action, key


def build_attachment_plan(
    md_path: Path,
    md_text: str,
    refs: List,
    chosen_map: Dict[int, str],
    title: str,
    attach_dir: Path,
    name_template: str,
    seq_width: int,
    max_len: int,
    skip_indexes: Optional[Set[int]] = None,
    intent_language: str = DEFAULT_INTENT_LANGUAGE,
) -> Dict:
    skip_indexes = set(skip_indexes or set())
    attach_dir.mkdir(parents=True, exist_ok=True)
    plan = {
        "document": str(md_path),
        "title": title,
        "attach_dir": str(attach_dir),
        "created_at": time.time(),
        "items": [],
        "completed": False,
    }
    reserved: set = set()
    md_root = md_path.parent
    block_idx = 0
    img_idx = 0
    for i, ref in enumerate(refs):
        above, below, between, explicit_refs = find_neighbor_text(md_text, refs, i)
        visible_above = re.findall(r"[一-鿿A-Za-z0-9]", above)
        is_new_block = len(visible_above) >= 4
        if is_new_block:
            above_wo_refs = above
            try:
                for pat in EXPLICIT_REF_PATTERNS:
                    above_wo_refs = re.sub(pat, "", above_wo_refs)
            except Exception:
                pass
            try:
                above_wo_refs = re.sub(r"(?m)^\s*#+\s+.*$", "", above_wo_refs)
                above_wo_refs = re.sub(r"(?m)^\s*(?:[-*+]\s+|\d+\.\s+).*$", "", above_wo_refs)
                above_wo_refs = re.sub(r"(?:图\s*\d+|Figure\s*\d+|Fig\.\s*\d+)", "", above_wo_refs, flags=re.IGNORECASE)
            except Exception:
                pass
            letters_only = re.sub(r"[\d\W_]+", "", above_wo_refs, flags=re.UNICODE)
            if len(letters_only) < 8:
                is_new_block = False
        prev_end = refs[i - 1].end if i > 0 else 0
        gap = max(0, ref.start - prev_end)
        if gap <= 3 or explicit_refs:
            is_new_block = False
        if is_new_block:
            block_idx += 1
            img_idx = 1
        else:
            if block_idx == 0:
                block_idx = 1
            img_idx += 1

        index = i + 1
        if index in skip_indexes:
            continue
        chosen = sanitize_intent_for_language(chosen_map.get(index) or "图意", intent_language)
        final_base = name_with_template(
            name_template,
            title,
            block_idx,
            img_idx,
            chosen,
            seq_width,
            max_len,
            intent_language=intent_language,
            global_index=index,
        )

        action = "move"
        original_abs = None
        ext = ""
        mapping_key = None
        cleaned_src = (ref.src or "").strip()
        if is_remote_url(cleaned_src):
            action = "download"
            parsed = urlparse(cleaned_src)
            ext = Path(unquote(parsed.path or "")).suffix
            if not ext:
                ext = Path(cleaned_src).suffix
            if not ext:
                ext = ".img"
            mapping_key = f"remote:{cleaned_src}"
        else:
            src_path = resolve_local_image(md_root, cleaned_src)
            if not src_path or not src_path.exists():
                plan["items"].append(
                    {
                        "index": index,
                        "original_src": cleaned_src,
                        "action": "error",
                        "status": "error",
                        "error": "source_missing",
                        "logs": [],
                    }
                )
                continue
            original_abs = str(src_path.resolve())
            ext = src_path.suffix or ".img"
            mapping_key = f"local:{original_abs}"

        target_path = reserve_unique_path(attach_dir, f"{final_base}{ext}", reserved)
        target_rel = _make_rel(target_path, md_root)
        plan_item = {
            "index": index,
            "block_index": block_idx,
            "image_index": img_idx,
            "original_src": cleaned_src,
            "original_abs": original_abs,
            "action": action,
            "final_base": final_base,
            "target_abs": str(target_path),
            "target_rel": target_rel,
            "status": "pending",
            "mapping_key": mapping_key,
            "logs": [],
        }
        plan["items"].append(plan_item)
    return plan


def execute_attachment_plan(
    plan: Dict,
    md_path: Path,
    attach_dir: Path,
    timeout: int,
    mapping: Dict[str, Dict],
    logger: Optional[Callable[[Dict], None]] = None,
    prefer_move: bool = True,
) -> Tuple[bool, bool]:
    md_root = md_path.parent
    items = plan.get("items", [])
    if not items:
        return True, False
    mapping_changed = False
    for item in items:
        status = item.get("status")
        if status == "done":
            continue
        if status == "error":
            return False, mapping_changed
        action = item.get("action")
        target_path = Path(item.get("target_abs", "")).resolve()
        original_src = item.get("original_src")
        mapping_key = item.get("mapping_key")
        try:
            if action == "download":
                if target_path.exists():
                    update_mapping_target(mapping, mapping_key, target_path, md_root)
                    item["status"] = "done"
                    item.setdefault("logs", []).append("exists")
                    mapping_changed = True
                else:
                    saved = download_image(original_src, attach_dir, timeout)
                    if not saved:
                        item["status"] = "error"
                        item["error"] = "download_failed"
                        save_attachment_plan(attach_dir, plan)
                        return False, mapping_changed
                    if not _try_move_file(saved, target_path):
                        item["status"] = "error"
                        item["error"] = "move_failed"
                        save_attachment_plan(attach_dir, plan)
                        return False, mapping_changed
                    update_mapping_target(mapping, mapping_key, target_path, md_root)
                    item["status"] = "done"
                    mapping_changed = True
            elif action == "move":
                original_abs = item.get("original_abs")
                if not original_abs:
                    item["status"] = "error"
                    item["error"] = "source_missing"
                    save_attachment_plan(attach_dir, plan)
                    return False, mapping_changed
                src_path = Path(original_abs)
                if target_path.exists() and not src_path.exists():
                    update_mapping_target(mapping, mapping_key, target_path, md_root)
                    item["status"] = "done"
                    item.setdefault("logs", []).append("exists")
                    mapping_changed = True
                else:
                    if not src_path.exists():
                        item["status"] = "error"
                        item["error"] = "source_missing"
                        save_attachment_plan(attach_dir, plan)
                        return False, mapping_changed
                    if not _try_move_file(src_path, target_path):
                        item["status"] = "error"
                        item["error"] = "move_failed"
                        save_attachment_plan(attach_dir, plan)
                        return False, mapping_changed
                    update_mapping_target(mapping, mapping_key, target_path, md_root)
                    item["status"] = "done"
                    mapping_changed = True
            else:
                item["status"] = "error"
                item["error"] = f"unsupported action: {action}"
                save_attachment_plan(attach_dir, plan)
                return False, mapping_changed
            item["completed_at"] = time.time()
            if logger:
                try:
                    logger(
                        {
                            "index": item.get("index"),
                            "action": action,
                            "target": item.get("target_rel"),
                            "status": item.get("status"),
                        }
                    )
                except Exception:
                    pass
            save_attachment_plan(attach_dir, plan)
            save_image_mapping(attach_dir, mapping)
        except Exception as exc:
            item["status"] = "error"
            item["error"] = str(exc)
            save_attachment_plan(attach_dir, plan)
            return False, mapping_changed
    plan["completed"] = True
    save_attachment_plan(attach_dir, plan)
    return True, mapping_changed



def update_mapping_target(mapping: Dict[str, Dict], key: Optional[str], target_path: Path, md_root: Path) -> None:
    if not key or key not in mapping:
        return
    target_path = target_path.resolve()
    entry = mapping[key]
    entry["target"] = str(target_path)
    entry["target_rel"] = _make_rel(target_path, md_root)
    entry["hash"] = _hash_file(target_path)


def collect_images_to_attachment(
    md_path: Path,
    attach_dir_name: str,
    timeout: int,
    backup: bool = True,
) -> Dict:
    """
    将 Markdown 中引用的图片统一收集到指定附件目录。

    - 远程图片会先下载到附件目录。
    - 本地图片若不在附件目录，会复制/移动到附件目录（保持原文件名，如遇重名自动去重）。
    - Markdown 内的引用会重写为附件目录下的相对路径。

    返回统计信息（包含 total/downloaded/moved/copied/skipped/missing/errors/details 等）。
    """

    text = read_text(md_path)
    refs = collect_images(text)
    attach_dir = md_path.parent / (attach_dir_name or "attachment")

    stats: Dict[str, object] = {
        "total": len(refs),
        "downloaded": 0,
        "moved": 0,
        "copied": 0,
        "skipped": 0,
        "missing": 0,
        "reused": 0,
        "errors": [],
        "updated": False,
        "details": [],
    }

    if not refs:
        return stats

    new_parts: List[str] = []
    cursor = 0
    attach_dir = md_path.parent / (attach_dir_name or "attachment")
    mapping = load_image_mapping(attach_dir)
    mapping_changed = False

    for i, ref in enumerate(refs, start=1):
        new_parts.append(text[cursor:ref.start])
        segment = text[ref.start:ref.end]
        new_rel = ref.src
        action = "skipped"

        try:
            new_rel_candidate, action, _ = ensure_attachment_for_src(md_path, ref.src, attach_dir, timeout, mapping, prefer_move=True)
            if action != "error" and new_rel_candidate:
                new_rel = new_rel_candidate
            if action == "downloaded":
                stats["downloaded"] = int(stats["downloaded"]) + 1
                mapping_changed = True
            elif action == "moved":
                stats["moved"] = int(stats["moved"]) + 1
                mapping_changed = True
            elif action == "copied":
                stats["copied"] = int(stats["copied"]) + 1
                mapping_changed = True
            elif action in ("reused", "already"):
                stats["reused"] = int(stats["reused"]) + 1
            elif action == "skipped":
                stats["skipped"] = int(stats["skipped"]) + 1
            elif action == "error":
                stats["missing"] = int(stats["missing"]) + 1
        except Exception as exc:
            stats.setdefault("errors", []).append(f"{ref.src} -> {exc}")
            action = f"error:{exc}"
            new_rel = ref.src

        if new_rel != ref.src:
            segment = segment.replace(ref.src, new_rel)
            stats["updated"] = True

        new_parts.append(segment)
        cursor = ref.end

        stats["details"].append(
            {
                "index": i,
                "original": ref.src,
                "final": new_rel,
                "action": action,
            }
        )

    new_parts.append(text[cursor:])
    new_text = "".join(new_parts)

    if new_text != text:
        if backup:
            backup_path = md_path.with_suffix(md_path.suffix + ".bak")
            try:
                backup_path.write_text(text, encoding="utf-8", newline="\n")
            except Exception as exc:
                stats.setdefault("errors", []).append(f"backup -> {exc}")
        try:
            write_text_utf8(md_path, new_text)
        except Exception as exc:
            stats.setdefault("errors", []).append(f"write -> {exc}")

    if mapping_changed:
        save_image_mapping(attach_dir, mapping)

    return stats


def restore_moved_images(md_path: Path, attach_dir_name: str, apply_changes: bool = True) -> Dict:
    """
    将附件目录中的搬运图片还原回原路径，并更新 Markdown 引用。
    """
    md_root = md_path.parent
    attach_dir = md_root / (attach_dir_name or "attachment")
    mapping = load_image_mapping(attach_dir)
    stats: Dict[str, object] = {
        "total": len(mapping),
        "restored": 0,
        "skipped": 0,
        "missing": 0,
        "errors": [],
        "details": [],
    }
    if not mapping:
        return stats

    text = read_text(md_path)
    new_text = text
    mapping_changed = False

    for key, entry in list(mapping.items()):
        if entry.get("type") != "local":
            stats["skipped"] = int(stats["skipped"]) + 1
            continue
        target_rel = entry.get("target_rel")
        original_rel = entry.get("original_rel")
        original_abs = entry.get("original")
        if not target_rel or not original_rel:
            stats["skipped"] = int(stats["skipped"]) + 1
            continue
        target_path = (md_root / Path(target_rel)).resolve()
        if original_abs:
            original_path = Path(original_abs)
        else:
            original_path = (md_root / Path(original_rel)).resolve()
        if not target_path.exists():
            stats["missing"] = int(stats["missing"]) + 1
            continue
        try:
            original_path.parent.mkdir(parents=True, exist_ok=True)
            if not _try_move_file(target_path, original_path):
                stats.setdefault("errors", []).append(f"无法还原：{target_path}")
                continue
            mapping.pop(key, None)
            mapping_changed = True
            stats["restored"] = int(stats["restored"]) + 1
            if apply_changes:
                new_text = new_text.replace(target_rel, original_rel)
            stats["details"].append(
                {
                    "original": original_rel,
                    "target": target_rel,
                }
            )
        except Exception as exc:
            stats.setdefault("errors", []).append(f"{target_rel} -> {exc}")

    if apply_changes and new_text != text:
        try:
            write_text_utf8(md_path, new_text)
        except Exception as exc:
            stats.setdefault("errors", []).append(f"写回失败：{exc}")

    if mapping_changed:
        save_image_mapping(attach_dir, mapping)

    return stats

# -----------------------------
# 主处理流程
# -----------------------------

@dataclass
class ItemResult:
    index: int
    kind: str
    src: str
    block_index: int
    image_index: int
    above_text: str
    below_text: str
    between_text: str
    explicit_refs: List[str]
    candidates: List[Dict]
    best: str
    normalized_title: str
    suggested_name: str
    ai_error: Optional[str] = None
    ai_raw: Optional[str] = None
    request_mode: Optional[str] = None  # openai_text / sf_text / sf_vlm

@dataclass
class Config:
    mode: str                         # dry-run / apply / no-rename / interactive
    strategy: str                     # seq / above / below / between / intent / hybrid / sci
    base_url: Optional[str]
    api_key: Optional[str]
    model: Optional[str]
    timeout: int
    max_retries: int
    rate_limit: float
    attach_dir_name: str
    download: bool
    name_template: str
    seq_width: int
    max_name_len: int
    save_report: Optional[Path]
    verbose: bool
    backup: bool
    vision: bool                      # 是否启用视觉理解（SiliconFlow VLM 格式）
    chunk_size: int                   # 每次聚合提交给模型的图片数量
    intent_language: str
    reason_language: str
    progress_cb: Optional[Callable[[str], None]] = None
    batch_confirm_cb: Optional[Callable[[List[Dict]], bool]] = None
    batch_result_cb: Optional[Callable[[Dict], None]] = None
    llm_event_cb: Optional[Callable[[Dict], None]] = None

def pick_intent_phrase(strategy: str, ai: Optional[Dict], above: str, below: str, between: str, *, context: Optional[Dict] = None) -> Tuple[str, str]:
    """返回 (intent_phrase, used_strategy)"""
    ctx = context or {}

    def simple_terms(s: str) -> str:
        if not s.strip():
            return "图意"
        # 简单截取中文术语片段
        s = re.sub(r"[『』「」【】《》()（）\*\-\+\=\[\]{}|\\]", "", s)
        sentences = re.split(r"[。！？；.]", s)
        sentences = [x.strip() for x in sentences if x.strip()]
        if not sentences:
            return "图意"
        # 选含术语的句子
        key_terms = ["双壳纲", "船蛆", "足丝", "鳃", "壳", "结构", "示意图", "系统发育", "演化", "解剖", "过滤进食"]
        sel = None
        for sen in sentences:
            if any(t in sen for t in key_terms):
                sel = sen
                break
        sel = sel or sentences[0]
        # 截取名词短语（粗略）
        sel = re.sub(r"\s+", "", sel)
        sel = sel[:16]
        return sel or "图意"
    if strategy == "seq":
        return "图意", "seq"

    if strategy == "sci":
        meta = ctx.get("sci_meta")
        if not isinstance(meta, dict):
            ref = ctx.get("ref")
            block_idx_val = ctx.get("block_index")
            image_idx_val = ctx.get("image_index")
            try:
                block_idx_int = int(block_idx_val)
            except Exception:
                block_idx_int = 0
            try:
                image_idx_int = int(image_idx_val)
            except Exception:
                image_idx_int = 1
            meta = build_sci_metadata(
                getattr(ref, "src", None),
                getattr(ref, "alt", None),
                getattr(ref, "title", None),
                above,
                below,
                ctx.get("above_focus", above),
                ctx.get("below_focus", below),
                block_idx_int,
                image_idx_int if image_idx_int > 0 else 1,
            )
            ctx["sci_meta"] = meta

        figure = meta.get("figure") if isinstance(meta, dict) else None
        panel = meta.get("panel") if isinstance(meta, dict) else None
        panel_sequence = list((meta.get("panel_sequence") or [])) if isinstance(meta, dict) else []
        panel_segments = dict(meta.get("panel_segments") or {}) if isinstance(meta, dict) else {}
        fallback_block = meta.get("fallback_block") if isinstance(meta, dict) else None
        if not figure and fallback_block:
            figure = fallback_block

        try:
            image_idx = int(ctx.get("image_index", 1))
        except Exception:
            image_idx = 1
        if image_idx <= 0:
            image_idx = 1

        if not panel and panel_sequence:
            seq_idx = image_idx - 1
            if 0 <= seq_idx < len(panel_sequence):
                panel = panel_sequence[seq_idx]

        summary_source: Optional[str] = None
        panel_key = (panel or "").upper() if panel else None
        if panel_key and panel_key in panel_segments:
            summary_source = panel_segments.get(panel_key)

        if not summary_source and ai:
            cands = ai.get("candidates", [])
            for c in cands:
                if c.get("strategy") == "below" and c.get("title"):
                    summary_source = c["title"]
                    break
            if not summary_source:
                summary_source = ai.get("normalized_title")

        if not summary_source:
            summary_source = below or between or above

        summary_clean = _clean_sci_summary(summary_source)
        if not summary_clean:
            summary_clean = simple_terms(below or between or above)

        info_from_summary = _extract_fig_from_text(summary_source or "")
        if info_from_summary:
            fig_from_summary, panel_from_summary = info_from_summary
            if fig_from_summary and not figure:
                figure = fig_from_summary
            if panel_from_summary and not panel:
                panel = panel_from_summary

        block_idx = ctx.get("block_index")
        if not figure and isinstance(block_idx, int) and block_idx > 0:
            figure = str(block_idx)
        elif not figure and isinstance(block_idx, str) and block_idx.isdigit():
            figure = block_idx

        figure_id: Optional[str] = None
        if figure:
            figure_id = re.sub(r"[^0-9A-Za-z\-]+", "", str(figure)).upper()
            if not figure_id:
                figure_id = None

        if not figure_id:
            fallback_phrase, fallback_used = pick_intent_phrase("below", ai, above, below, between, context=ctx)
            return fallback_phrase, f"sci->{fallback_used}"

        panel_letter = panel
        if panel_letter:
            panel_letter = re.sub(r"[^A-Za-z]", "", str(panel_letter).upper())[:1]
        elif panel_sequence and len(panel_sequence) > 1:
            seq_idx = image_idx - 1
            if 0 <= seq_idx < len(panel_sequence):
                seq_letter = re.sub(r"[^A-Za-z]", "", str(panel_sequence[seq_idx]).upper())
                if seq_letter:
                    panel_letter = seq_letter[:1]

        label = f"fig{figure_id}"
        if panel_letter and not label.endswith(panel_letter):
            label = f"{label}{panel_letter}"

        phrase = label if not summary_clean else f"{label}_{summary_clean}"
        return phrase, "sci"

    if ai:
        cands = ai.get("candidates", [])
        if strategy == "above":
            # 找到 above 候选并替换为 normalized_title
            for c in cands:
                if c.get("strategy") == "above" and c.get("title"):
                    return c["title"], "above"
            return ai.get("normalized_title", "图意"), "above"
        if strategy == "below":
            for c in cands:
                if c.get("strategy") == "below" and c.get("title"):
                    return c["title"], "below"
            return ai.get("normalized_title", "图意"), "below"
        if strategy == "between":
            # 无专属 between 时退回 intent/normalized
            for c in cands:
                if c.get("strategy") in ("intent", "between") and c.get("title"):
                    return c["title"], c.get("strategy")
            return ai.get("normalized_title", "图意"), "between"
        if strategy in ("intent", "hybrid"):
            # 遵循 best 或 normalized_title
            best = ai.get("best")
            if best:
                for c in cands:
                    if c.get("strategy") == best and c.get("title"):
                        return c["title"], best
            return ai.get("normalized_title", "图意"), "intent"
    if strategy == "above":
        return simple_terms(above), "above"
    if strategy == "below":
        return simple_terms(below), "below"
    if strategy == "between":
        return simple_terms(between), "between"
    return simple_terms(above or below or between), "seq"
def process_document(md_path: Path, cfg: Config) -> Dict:
    text = read_text(md_path)
    title = extract_doc_title(text, md_path)
    refs = collect_images(text)
    total_images = len(refs)
    results: Dict = {"document": str(md_path), "title": title, "count": total_images, "items": []}
    cb = cfg.progress_cb
    if cb:
        cb(f"🔍 正在处理《{title}》，共 {total_images} 张图片")
    if cfg.verbose:
        print(f"✅ 发现图片 {total_images} 张")

    doc_base = sanitize_intent_for_language(title, cfg.intent_language) or "document"
    seq_width_doc = max(cfg.seq_width, len(str(max(1, total_images))))
    intent_counters: Dict[str, int] = defaultdict(int)
    last_intent: Optional[str] = None

    block_idx = 0
    img_idx = 0
    current_block_intent: Optional[str] = None

    backup_path = None
    if cfg.mode in ("apply", "interactive") and cfg.backup:
        backup_path = md_path.with_suffix(md_path.suffix + ".bak")
        try:
            backup_path.write_text(text, encoding="utf-8", newline="\n")
            if cfg.verbose:
                print(f"🗂 已备份原文件 -> {backup_path}")
        except Exception as e:
            print(f"⚠️ 备份失败：{e}")

    new_parts: List[str] = []
    cursor = 0

    chunk_size = max(1, getattr(cfg, "chunk_size", 5))
    if cfg.strategy == "sci":
        chunk_size = max(1, total_images)
    pending: List[Dict] = []
    cancelled = False
    attach_dir = md_path.parent / (cfg.attach_dir_name or "attachment")
    mapping: Dict[str, Dict] = {}
    mapping_changed = False
    if cfg.mode in ("apply", "interactive"):
        mapping = load_image_mapping(attach_dir)

    def _propagate_sci_within_block(contexts: List[Dict], block_index: int) -> None:
        block_contexts = [ctx for ctx in contexts if ctx.get("block_index") == block_index]
        if len(block_contexts) <= 1:
            return
        anchor_meta: Optional[Dict[str, object]] = None
        for ctx in reversed(block_contexts):
            meta = ctx.get("sci_meta") or {}
            seq = meta.get("panel_sequence")
            if seq and isinstance(seq, list) and len(seq) > 1:
                anchor_meta = meta  # type: ignore[assignment]
                break
        if not anchor_meta:
            return
        figure = anchor_meta.get("figure") or anchor_meta.get("fallback_block")
        seq_list = anchor_meta.get("panel_sequence") or []
        segments = anchor_meta.get("panel_segments") or {}
        if not isinstance(seq_list, list):
            return
        for idx, ctx in enumerate(block_contexts):
            meta = ctx.get("sci_meta") or {}
            if figure and not meta.get("figure"):
                meta["figure"] = figure
            if idx < len(seq_list):
                panel_letter = seq_list[idx]
                if panel_letter and not meta.get("panel"):
                    meta["panel"] = panel_letter
                if (
                    isinstance(panel_letter, str)
                    and isinstance(segments, dict)
                    and panel_letter in segments
                ):
                    meta.setdefault("panel_segments", {})
                    if isinstance(meta["panel_segments"], dict):
                        meta["panel_segments"].setdefault(panel_letter, segments[panel_letter])
            ctx["sci_meta"] = meta

    def emit_llm_event(event: Dict) -> None:
        if cfg.llm_event_cb:
            try:
                cfg.llm_event_cb(copy.deepcopy(event))
            except Exception:
                pass

    def emit_batch_result(payload: Dict) -> None:
        if cfg.batch_result_cb:
            try:
                cfg.batch_result_cb(copy.deepcopy(payload))
            except Exception:
                pass

    def build_batch_preview(contexts: List[Dict]) -> List[Dict]:
        preview: List[Dict] = []
        for ctx in contexts:
            ref = ctx["ref"]
            src_value = ref.src
            if is_remote_url(src_value):
                parsed = urlparse(src_value)
                name = Path(unquote(parsed.path or "")).name or src_value
            else:
                name = Path(src_value).name or src_value
            preview.append(
                {
                    "index": ctx["index"],
                    "src": src_value,
                    "display_name": name,
                    "remote": is_remote_url(src_value),
                    "block_index": ctx["block_index"],
                    "image_index": ctx["image_index"],
                }
            )
        return preview

    def make_ai_result(error: Optional[str] = None, raw: Optional[str] = None, req_mode: Optional[str] = None, ai_json: Optional[Dict] = None) -> Dict:
        return {"ai_json": ai_json, "ai_error": error, "ai_raw": raw, "req_mode": req_mode}

    def call_single(context: Dict) -> Dict:
        if cfg.strategy == "seq":
            return make_ai_result(req_mode="seq")
        vision_src = context.get("vision_src")
        is_sf = is_siliconflow(cfg.base_url or "")
        req_mode = "sf_vlm" if (is_sf and vision_src) else ("sf_text" if is_sf else "openai_text")
        msgs = build_ai_messages(
            title,
            context["above_focus"],
            context["below_focus"],
            context["between"],
            context["explicit_refs"],
            context.get("alt"),
            context.get("title_attr"),
            vision_src=vision_src,
            base_url=cfg.base_url or "",
            intent_language=cfg.intent_language,
            reason_language=cfg.reason_language,
        )
        emit_llm_event(
            {
                "event": "request",
                "mode": "single",
                "strategy": cfg.strategy,
                "indexes": [context["index"]],
                "vision": bool(vision_src),
                "messages": summarize_messages(msgs),
            }
        )
        ai_out = call_openai_chat(
            cfg.base_url or "",
            cfg.api_key or "",
            cfg.model or "gpt-4o-mini",
            msgs,
            timeout=cfg.timeout,
            max_retries=cfg.max_retries,
            rate_limit=cfg.rate_limit,
            verbose=cfg.verbose,
        )
        if ai_out is None:
            emit_llm_event(
                {
                    "event": "response",
                    "mode": "single",
                    "strategy": cfg.strategy,
                    "indexes": [context["index"]],
                    "status": "error",
                    "error": truncate_text(get_last_llm_error() or "模型返回为空", 280),
                }
            )
            return make_ai_result("llm_call_failed", (get_last_llm_error() or "")[:400], req_mode)
        emit_llm_event(
            {
                "event": "response",
                "mode": "single",
                "strategy": cfg.strategy,
                "indexes": [context["index"]],
                "status": "ok",
                "raw_length": len(ai_out),
                "snippet": truncate_text(ai_out, 400),
            }
        )
        parsed = safe_parse_json(ai_out)
        if parsed is None:
            return make_ai_result("llm_parse_failed", (ai_out or "")[:400], req_mode)
        validated = validate_ai_result(parsed, intent_language=cfg.intent_language)
        if validated is None:
            return make_ai_result("llm_validate_failed", (ai_out or "")[:400], req_mode)
        return make_ai_result(None, None, req_mode, validated)

    def call_batch(contexts: List[Dict]) -> Dict[int, Dict]:
        if not contexts:
            return {}
        if cfg.strategy == "seq":
            return {ctx["index"]: make_ai_result(req_mode="seq") for ctx in contexts}
        if cfg.vision:
            # 视觉模式暂不支持批量聚合，依次调用单图
            return {ctx["index"]: call_single(ctx) for ctx in contexts}
        msgs = build_ai_batch_messages(
            title,
            contexts,
            base_url=cfg.base_url or "",
            intent_language=cfg.intent_language,
            reason_language=cfg.reason_language,
        )
        is_sf = is_siliconflow(cfg.base_url or "")
        req_mode = "sf_text_batch" if is_sf else "openai_text_batch"
        emit_llm_event(
            {
                "event": "request",
                "mode": "batch",
                "strategy": cfg.strategy,
                "indexes": [ctx["index"] for ctx in contexts],
                "vision": False,
                "messages": summarize_messages(msgs),
            }
        )
        ai_out = call_openai_chat(
            cfg.base_url or "",
            cfg.api_key or "",
            cfg.model or "gpt-4o-mini",
            msgs,
            timeout=cfg.timeout,
            max_retries=cfg.max_retries,
            rate_limit=cfg.rate_limit,
            verbose=cfg.verbose,
        )
        result_map = {ctx["index"]: make_ai_result("llm_call_failed", (get_last_llm_error() or "")[:400], req_mode) for ctx in contexts}
        if ai_out is None:
            emit_llm_event(
                {
                    "event": "response",
                    "mode": "batch",
                    "strategy": cfg.strategy,
                    "indexes": [ctx["index"] for ctx in contexts],
                    "status": "error",
                    "error": truncate_text(get_last_llm_error() or "模型返回为空", 280),
                }
            )
            return result_map
        parsed = safe_parse_json(ai_out)
        emit_llm_event(
            {
                "event": "response",
                "mode": "batch",
                "strategy": cfg.strategy,
                "indexes": [ctx["index"] for ctx in contexts],
                "status": "ok",
                "raw_length": len(ai_out),
                "snippet": truncate_text(ai_out, 400),
            }
        )
        items = parsed.get("items") if isinstance(parsed, dict) else None
        if not isinstance(items, list):
            snippet = (ai_out or "")[:400]
            for idx in result_map:
                result_map[idx]["ai_error"] = "llm_parse_failed"
                result_map[idx]["ai_raw"] = snippet
            return result_map
        for entry in items:
            idx = entry.get("index")
            if idx is None:
                continue
            validated = validate_ai_result(entry, intent_language=cfg.intent_language)
            if validated is None:
                snippet = json.dumps(entry, ensure_ascii=False)[:400]
                if idx in result_map:
                    result_map[idx]["ai_error"] = "llm_validate_failed"
                    result_map[idx]["ai_raw"] = snippet
                continue
            result_map[idx] = make_ai_result(None, None, req_mode, validated)
        return result_map

    def finalize_context(context: Dict, ai_info: Dict) -> None:
        nonlocal cursor, current_block_intent, last_intent

        ref = context["ref"]
        ai_json = ai_info.get("ai_json") if ai_info else None
        ai_error = ai_info.get("ai_error") if ai_info else None
        ai_raw = ai_info.get("ai_raw") if ai_info else None
        req_mode = ai_info.get("req_mode") if ai_info else None

        intent_phrase, used_strategy = pick_intent_phrase(
            context["effective_strategy"],
            ai_json,
            context["above_focus"],
            context["below_focus"],
            context["between"],
            context=context,
        )
        normalized_for_item = sanitize_intent_for_language(intent_phrase, cfg.intent_language)
        if len(normalized_for_item.strip()) < 3:
            if last_intent:
                normalized_for_item = last_intent
                used_strategy = "copied_prev"
            else:
                normalized_for_item = "图意"
        if context["image_index"] == 1:
            current_block_intent = normalized_for_item
        elif current_block_intent:
            normalized_for_item = current_block_intent
            used_strategy = "block_same"
        last_intent = normalized_for_item

        intent_counters[normalized_for_item] += 1
        intent_index = intent_counters[normalized_for_item]
        suggested_name = sanitize_intent_for_language(
            f"{doc_base}{context['index']:0{seq_width_doc}d}_{normalized_for_item}{intent_index:02d}",
            cfg.intent_language,
        ) or f"image_{context['index']:0{seq_width_doc}d}"

        candidates: List[Dict] = []
        if ai_json and isinstance(ai_json.get("candidates"), list):
            candidates = ai_json["candidates"]
        else:
            fallback_reason = f"fallback({ai_error or 'no_ai'})"
            candidates = [
                {"strategy": "above", "title": normalized_for_item, "reason": fallback_reason, "confidence": 0.6},
                {"strategy": "below", "title": normalized_for_item, "reason": fallback_reason, "confidence": 0.6},
                {"strategy": "intent", "title": normalized_for_item, "reason": fallback_reason, "confidence": 0.6},
            ]

        item = ItemResult(
            index=context["index"],
            kind=context["ref"].kind,
            src=context["ref"].src,
            block_index=context["block_index"],
            image_index=context["image_index"],
            above_text=context["above"],
            below_text=context["below"],
            between_text=context["between"],
            explicit_refs=context["explicit_refs"],
            candidates=candidates,
            best=ai_json.get("best") if (ai_json and used_strategy != "block_same") else used_strategy,
            normalized_title=normalized_for_item,
            suggested_name=suggested_name,
            ai_error=ai_error,
            ai_raw=ai_raw,
            request_mode=req_mode,
        )
        results["items"].append(item.__dict__)
        emit_batch_result({"index": context["index"], "item": item.__dict__})

        if cfg.mode in ("apply", "interactive"):
            new_rel = ref.src
            action = "skipped"
            mapping_key: Optional[str] = None
            try:
                if is_remote_url(ref.src):
                    if cfg.download:
                        new_rel_candidate, action, mapping_key = ensure_attachment_for_src(
                            md_path,
                            ref.src,
                            attach_dir,
                            cfg.timeout,
                            mapping,
                            prefer_move=False,
                        )
                        if action != "error" and new_rel_candidate:
                            new_rel = new_rel_candidate
                    else:
                        action = "skipped"
                else:
                    new_rel_candidate, action, mapping_key = ensure_attachment_for_src(
                        md_path,
                        ref.src,
                        attach_dir,
                        cfg.timeout,
                        mapping,
                        prefer_move=True,
                    )
                    if action != "error" and new_rel_candidate:
                        new_rel = new_rel_candidate
                if action == "error" and cfg.verbose:
                    print(f"⚠️ 处理单图失败：{ref.src}")
                asset_path = (md_path.parent / Path(new_rel)).resolve()
                if asset_path.exists():
                    suffix = asset_path.suffix or Path(ref.src).suffix or ".img"
                    target_path = ensure_unique_path(attach_dir, f"{suggested_name}{suffix}")
                    if asset_path != target_path:
                        if _try_move_file(asset_path, target_path):
                            new_rel = _make_rel(target_path, md_path.parent)
                            update_mapping_target(mapping, mapping_key, target_path, md_path.parent)
                            mapping_changed = True
                        else:
                            if cfg.verbose:
                                print(f"⚠️ 重命名失败：{asset_path}")
                    elif action in {"moved", "copied", "downloaded"}:
                        update_mapping_target(mapping, mapping_key, asset_path, md_path.parent)
                        mapping_changed = True
                else:
                    if action in {"moved", "copied", "downloaded"} and cfg.verbose:
                        print(f"⚠️ 目标文件不存在：{new_rel}")
            except Exception as exc:
                if cfg.verbose:
                    print(f"⚠️ 处理单图失败：{exc}")

            new_parts.append(text[cursor:ref.start])
            original_seg = text[ref.start:ref.end]
            new_seg = original_seg.replace(ref.src, new_rel)
            if ref.kind == "md":
                m2 = MD_IMAGE_RE.search(original_seg)
                if m2:
                    alt_raw = m2.group(1)
                    title_text = (ref.title or "").strip().strip('"').strip("'")
                    alt_clean = re.sub(r"<[^>]+>", "", alt_raw or "")
                    alt_clean = alt_clean.replace("|", " ").strip()
                    alt_clean = WHITESPACE_RE.sub(" ", alt_clean).strip()
                    trailing_title = f' "{title_text}"' if title_text else ""
                    new_seg = f'![{alt_clean}]({new_rel}{trailing_title})'
            new_parts.append(new_seg)
            cursor = ref.end

    for i, ref in enumerate(refs):
        above, below, between, explicit_refs = find_neighbor_text(text, refs, i)
        override_side, above_focus, below_focus = explicit_override_and_focus(cfg.strategy, above, below)
        effective_strategy = cfg.strategy
        if cfg.strategy in ("above", "below") and override_side in ("above", "below"):
            effective_strategy = override_side
        elif cfg.strategy == "sci" and override_side == "above":
            effective_strategy = "above"
        visible_above = re.findall(r"[一-鿿A-Za-z0-9]", above)
        is_new_block = False
        if len(visible_above) >= 4:
            above_wo_refs = above
            try:
                for pat in EXPLICIT_REF_PATTERNS:
                    above_wo_refs = re.sub(pat, "", above_wo_refs)
            except Exception:
                pass
            try:
                above_wo_refs = re.sub(r"(?m)^\s*#+\s+.*$", "", above_wo_refs)
                above_wo_refs = re.sub(r"(?m)^\s*(?:[-*+]\s+|\d+\.\s+).*$", "", above_wo_refs)
                above_wo_refs = re.sub(r"(?:图\s*\d+|Figure\s*\d+|Fig\.\s*\d+)", "", above_wo_refs, flags=re.IGNORECASE)
            except Exception:
                pass
            letters_only = re.sub(r"[\d\W_]+", "", above_wo_refs, flags=re.UNICODE)
            if len(letters_only) >= 8:
                is_new_block = True
        prev_end = refs[i - 1].end if i > 0 else 0
        gap = max(0, ref.start - prev_end)
        if gap <= 3 or explicit_refs:
            is_new_block = False

        if is_new_block:
            block_idx += 1
            img_idx = 1
            current_block_intent = None
        else:
            if block_idx == 0:
                block_idx = 1
            img_idx += 1

        vision_src = build_vision_src(md_path, ref.src) if cfg.vision else None

        sci_meta = build_sci_metadata(
            ref.src,
            ref.alt,
            ref.title,
            above,
            below,
            above_focus,
            below_focus,
            block_idx,
            img_idx,
        )
        context = {
            "index": i + 1,
            "ref": ref,
            "block_index": block_idx,
            "image_index": img_idx,
            "above": above,
            "below": below,
            "between": between,
            "explicit_refs": explicit_refs,
            "above_focus": above_focus,
            "below_focus": below_focus,
            "effective_strategy": effective_strategy,
            "vision_src": vision_src,
            "alt": ref.alt,
            "title_attr": ref.title,
            "sci_meta": sci_meta,
            "sci_override": override_side,
        }
        pending.append(context)
        if cfg.strategy == "sci":
            _propagate_sci_within_block(pending, block_idx)

        should_flush = len(pending) == chunk_size or i == total_images - 1
        if should_flush:
            batch_contexts = list(pending)
            if cfg.batch_confirm_cb:
                try:
                    proceed = bool(cfg.batch_confirm_cb(build_batch_preview(batch_contexts)))
                except Exception as exc:
                    if cfg.progress_cb:
                        cfg.progress_cb(f"⚠️ 批次确认失败：{exc}")
                    proceed = False
                if not proceed:
                    cancelled = True
                    break
            if len(batch_contexts) == 1:
                ai_map = {batch_contexts[0]["index"]: call_single(batch_contexts[0])}
            else:
                ord_contexts = list(reversed(batch_contexts)) if cfg.strategy == "sci" else batch_contexts
                ai_map = call_batch(ord_contexts)
            for ctx in batch_contexts:
                finalize_context(ctx, ai_map.get(ctx["index"]))
            pending.clear()

        if cancelled:
            break

    if cancelled:
        results["cancelled"] = True

    if cfg.mode in ("apply", "interactive"):
        new_parts.append(text[cursor:])
        new_text = "".join(new_parts)
        if cfg.mode == "apply":
            if new_text != text:
                try:
                    write_text_utf8(md_path, new_text)
                    if cfg.verbose:
                        print(f"✅ 已写回：{md_path}")
                except Exception as e:
                    print(f"❌ 写回失败：{e}")
            else:
                if cfg.verbose:
                    print("ℹ️ 文档未发生变化（可能未能生成新路径或处理失败）。")
        else:
            results["new_text"] = new_text

    if cfg.mode in ("apply", "interactive") and mapping_changed:
        save_image_mapping(attach_dir, mapping)

    if cfg.save_report:
        try:
            cfg.save_report.parent.mkdir(parents=True, exist_ok=True)
            cfg.save_report.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"📝 报告已保存：{cfg.save_report}")
        except Exception as e:
            print(f"⚠️ 保存报告失败：{e}")

    if cfg.verbose:
        print(f"✅ 预览完成，将处理 {total_images} 张图片")

    return results
def process_document_pick_one(md_path: Path, cfg: Config, target_index: int) -> Dict:
    """
    单图选择（默认启用视觉理解），提供三种图意来源：
    1) 上文总结图意
    2) 下文总结图意
    3) 识图图意（VLM/LLM）
    选择后对该图执行下载/搬移重命名并改链。
    """
    text = read_text(md_path)
    title = extract_doc_title(text, md_path)
    refs = collect_images(text)
    if not refs:
        print("ℹ️ 未发现图片。")
        return {"document": str(md_path), "title": title, "count": 0, "items": []}
    if target_index < 1 or target_index > len(refs):
        print(f"❌ 指定序号超出范围：index={target_index}（有效范围 1~{len(refs)}）")
        return {"document": str(md_path), "title": title, "count": len(refs), "items": []}

    # 计算块/序号（与主流程一致的判定）
    block_idx = 0
    img_idx = 0
    current_block_intent: Optional[str] = None

    # 先迭代至目标，获得其 block/img 序号
    for i, ref in enumerate(refs):
        above, below, between, explicit_refs = find_neighbor_text(text, refs, i)
        # 分块判定（与主流程一致）
        visible_above = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", above)
        is_new_block = False
        if len(visible_above) >= 4:
            above_wo_refs = above
            try:
                for pat in EXPLICIT_REF_PATTERNS:
                    above_wo_refs = re.sub(pat, "", above_wo_refs)
            except Exception:
                pass
            try:
                above_wo_refs = re.sub(r"(?m)^\s*#+\s+.*$", "", above_wo_refs)
                above_wo_refs = re.sub(r"(?m)^\s*(?:[-*+]\s+|\d+\.\s+).*$", "", above_wo_refs)
                above_wo_refs = re.sub(r"(?:图\s*\d+|Figure\s*\d+|Fig\.\s*\d+)", "", above_wo_refs, flags=re.IGNORECASE)
            except Exception:
                pass
            letters_only = re.sub(r"[\d\W_]+", "", above_wo_refs, flags=re.UNICODE)
            if len(letters_only) >= 8:
                is_new_block = True
        try:
            prev_end_local = refs[i - 1].end if i > 0 else 0
        except Exception:
            prev_end_local = 0
        gap = max(0, ref.start - prev_end_local)
        if gap <= 3 or explicit_refs:
            is_new_block = False

        if is_new_block:
            block_idx += 1
            img_idx = 1
            current_block_intent = None
        else:
            if block_idx == 0:
                block_idx = 1
            img_idx += 1

        if (i + 1) == target_index:
            target_ref = ref
            target_above, target_below, target_between, target_explicit = above, below, between, explicit_refs
            # 单图选择也应用显式引用智能覆盖与句子聚焦（仅影响上/下文短语）
            _override_side, target_above_eff, target_below_eff = explicit_override_and_focus(cfg.strategy, target_above, target_below)
            target_block, target_img = block_idx, img_idx
            break
    else:
        print("❌ 迭代失败：未定位到目标图片。")
        return {"document": str(md_path), "title": title, "count": len(refs), "items": []}

    # 构造三种图意候选
    ai_json = None
    vision_src = None
    if cfg.vision:
        vision_src = build_vision_src(md_path, target_ref.src)
    if cfg.strategy != "seq":
        # 识图/融合：仅对目标图进行一次调用
        is_sf = is_siliconflow(cfg.base_url or "")
        msgs = build_ai_messages(
            title,
            target_above_eff,
            target_below_eff,
            target_between,
            target_explicit,
            target_ref.alt,
            target_ref.title,
            vision_src=vision_src,
            base_url=cfg.base_url or "",
            intent_language=cfg.intent_language,
            reason_language=cfg.reason_language,
        )
        ai_out = call_openai_chat(
            cfg.base_url or "",
            cfg.api_key or "",
            cfg.model or "gpt-4o-mini",
            msgs,
            timeout=cfg.timeout,
            max_retries=cfg.max_retries,
            rate_limit=cfg.rate_limit,
            verbose=cfg.verbose
        )
        if ai_out:
            parsed = safe_parse_json(ai_out)
            ai_json = validate_ai_result(parsed, intent_language=cfg.intent_language) if parsed else None

    target_context = {
        "ref": target_ref,
        "block_index": target_block,
        "image_index": target_img,
        "above": target_above,
        "below": target_below,
        "between": target_between,
        "explicit_refs": target_explicit,
        "above_focus": target_above_eff,
        "below_focus": target_below_eff,
    }
    target_context["sci_meta"] = build_sci_metadata(
        target_ref.src,
        target_ref.alt,
        target_ref.title,
        target_above,
        target_below,
        target_above_eff,
        target_below_eff,
        target_block,
        target_img,
    )

    # 提供三种选择的短语
    above_phrase, _ = pick_intent_phrase("above", ai_json, target_above_eff, target_below_eff, target_between, context=target_context)
    below_phrase, _ = pick_intent_phrase("below", ai_json, target_above_eff, target_below_eff, target_between, context=target_context)
    vision_phrase, _ = pick_intent_phrase("intent", ai_json, target_above_eff, target_below_eff, target_between, context=target_context)


    print("\n—— 单图选择 ——")
    print(f"图片 #{target_index}/{len(refs)} | src: {target_ref.src}")
    print(f"块序号: {target_block}, 块内序号: {target_img}")
    print("[1] 上文总结图意 ->", above_phrase)
    print("[2] 下文总结图意 ->", below_phrase)
    print("[3] 识图图意     ->", vision_phrase, "(默认)")
    sel = input("选择 1/2/3（回车默认3）：").strip()
    if sel not in ("1", "2", "3"):
        sel = "3"
    chosen = {"1": above_phrase, "2": below_phrase, "3": vision_phrase}[sel]
    chosen = sanitize_intent_for_language(chosen, cfg.intent_language)

    # 计算最终文件名并执行改名与回链（仅目标图片）
    final_name = name_with_template(cfg.name_template, title, target_block, target_img, chosen, cfg.seq_width, cfg.max_name_len, intent_language=cfg.intent_language)
    new_text = text
    attach_dir = md_path.parent / cfg.attach_dir_name
    mapping = load_image_mapping(attach_dir)
    mapping_changed = False
    try:
        if is_remote_url(target_ref.src):
            if cfg.download:
                new_rel, action, mapping_key = ensure_attachment_for_src(
                    md_path,
                    target_ref.src,
                    attach_dir,
                    cfg.timeout,
                    mapping,
                    prefer_move=False,
                )
            else:
                action = "skipped"
                new_rel = target_ref.src
                mapping_key = None
        else:
            new_rel, action, mapping_key = ensure_attachment_for_src(
                md_path,
                target_ref.src,
                attach_dir,
                cfg.timeout,
                mapping,
                prefer_move=True,
            )
        if action == "error":
            print(f"⚠️ 处理图片失败：{target_ref.src}")
        else:
            asset_path = (md_path.parent / Path(new_rel)).resolve()
            if asset_path.exists():
                suffix = asset_path.suffix or Path(target_ref.src).suffix or ".img"
                target_path = ensure_unique_path(attach_dir, f"{final_name}{suffix}").resolve()
                if asset_path != target_path:
                    if _try_move_file(asset_path, target_path):
                        new_rel = os.path.relpath(target_path, md_path.parent).replace("\\", "/")
                        update_mapping_target(mapping, mapping_key, target_path, md_path.parent)
                        mapping_changed = True
                    else:
                        print(f"⚠️ 重命名失败：{asset_path}")
                else:
                    if mapping_key:
                        update_mapping_target(mapping, mapping_key, asset_path, md_path.parent)
                        if action in {"moved", "copied", "downloaded"}:
                            mapping_changed = True
                new_text = new_text[:target_ref.start] + new_text[target_ref.start:target_ref.end].replace(target_ref.src, new_rel) + new_text[target_ref.end:]
            else:
                print(f"⚠️ 目标文件不存在：{new_rel}")
    except Exception as e:
        print(f"⚠️ 处理图片失败：{e}")

    if new_text != text and cfg.mode in ("apply", "pick-one"):
        # 备份与写回
        if cfg.backup:
            backup_path = md_path.with_suffix(md_path.suffix + ".bak")
            try:
                backup_path.write_text(text, encoding="utf-8", newline="\n")
                print(f"🗂 已备份原文件 -> {backup_path}")
            except Exception as e:
                print(f"⚠️ 备份失败：{e}")
        try:
            write_text_utf8(md_path, new_text)
            print(f"✅ 已写回：{md_path}")
        except Exception as e:
            print(f"❌ 写回失败：{e}")
    else:
        print("ℹ️ 文档未发生变化（可能处理失败或仅预览）。")

    if mapping_changed:
        save_image_mapping(attach_dir, mapping)

    return {
        "document": str(md_path),
        "title": title,
        "count": len(refs),
        "items": [{
            "index": target_index,
            "block_index": target_block,
            "image_index": target_img,
            "above_text": target_above,
            "below_text": target_below,
            "chosen_intent": chosen,
            "suggested_name": final_name
        }]
    }

# -----------------------------
# CLI 与入口
# -----------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="AI 命名器：为 Markdown 图片生成“图意”并重命名回写（上/下/区间/显式引用/视觉理解）。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("path", type=Path, help="目标 Markdown 文件路径")
    p.add_argument("--mode", choices=["dry-run", "apply", "no-rename", "interactive", "pick-one"], default="dry-run", help="运行模式（新增：pick-one 单图选择）")
    p.add_argument("--strategy", choices=["seq", "above", "below", "between", "intent", "hybrid", "sci"], default="intent", help="命名策略")
    p.add_argument("--attach-dir-name", default="attachments", help="附件目录名（相对文档同级）")
    p.add_argument("--download", action="store_true", help="下载远程图片到附件目录并改写链接")
    p.add_argument("--restore-moved", action="store_true", help="还原附件目录中的已搬运图片并恢复引用后立即退出")
    p.add_argument("--name-template", default="{title}_{index:02d}", help="文件名模板，可用变量 {title} {block} {idx} {index} {intent}；支持 {block:02d} {idx:02d} {index:02d} 宽度")
    p.add_argument("--seq-width", type=int, default=2, help="序号宽度（默认两位）")
    p.add_argument("--max-name-len", type=int, default=80, help="文件名最大长度")
    p.add_argument("--timeout", type=int, default=90, help="HTTP 超时秒数")
    p.add_argument("--max-retries", type=int, default=3, help="AI 调用最大重试次数")
    p.add_argument("--rate-limit", type=float, default=0.3, help="每次 AI 调用之间的延时（秒）")
    p.add_argument("--verbose", action="store_true", help="详细日志")
    p.add_argument("--backup", action="store_true", help="写回前备份原文件并支持回滚")
    p.add_argument("--save-report", type=Path, default=None, help="保存完整命名报告的 JSON 路径")
    # AI 接口
    p.add_argument("--base-url", default=getenv_default("OPENAI_BASE_URL", None), help="OpenAI 兼容 Base URL（可读 OPENAI_BASE_URL）")
    p.add_argument("--api-key", default=getenv_default("OPENAI_API_KEY", None), help="API Key（可读 OPENAI_API_KEY）")
    p.add_argument("--model", default=getenv_default("OPENAI_MODEL", "gpt-4o-mini"), help="模型名称（可读 OPENAI_MODEL）")
    # 视觉理解（SiliconFlow VLM）
    p.add_argument("--vision", action="store_true", help="启用视觉理解（为 SiliconFlow VLM 构造 image_url 消息内容）")
    p.add_argument(
        "--intent-language",
        choices=list(LANGUAGE_LOCALES.keys()),
        default=DEFAULT_INTENT_LANGUAGE,
        help="生成的图意语言（默认跟随原文，可选翻译成中文或输出英文）",
    )
    p.add_argument(
        "--reason-language",
        choices=REASON_LANGUAGE_CHOICES,
        default=DEFAULT_REASON_LANGUAGE,
        help="候选解释语言（默认中文，可选英文）",
    )
    # 单图选择：指定图片序号（1-based）
    p.add_argument("--index", type=int, default=1, help="单图选择时的图片序号（1-based），与 pick-one 模式配合使用")
    return p

def main() -> None:
    args = build_parser().parse_args()

    if not args.path.exists():
        print(f"❌ 文件不存在：{args.path}")
        sys.exit(1)

    if args.restore_moved:
        stats = restore_moved_images(args.path, args.attach_dir_name)
        restored = int(stats.get("restored", 0))
        missing = int(stats.get("missing", 0))
        skipped = int(stats.get("skipped", 0))
        print(f"🔄 已尝试恢复搬运图片：还原 {restored} 条，缺失 {missing} 条，跳过 {skipped} 条。")
        details = stats.get("details") or []
        if details:
            print("  详情：")
            for item in details:
                print(f"   • {item.get('target')} -> {item.get('original')}")
        errors = stats.get("errors") or []
        if errors:
            print("⚠️ 发生错误：")
            for err in errors:
                print(f"   • {err}")
        return

    api_key = prompt_for_api_key_if_missing(args.api_key) if args.strategy != "seq" else (args.api_key or "")
    if args.strategy != "seq":
        if not requests:
            print("❌ 需要 requests 库：pip install requests")
            sys.exit(1)
        if not args.base_url:
            print("❌ 未提供 --base-url，且环境变量 OPENAI_BASE_URL 为空")
            sys.exit(1)
        if not api_key:
            print("❌ 未提供 API Key")
            sys.exit(1)

    cfg = Config(
        mode=args.mode,
        strategy=args.strategy,
        base_url=args.base_url,
        api_key=api_key,
        model=args.model,
        timeout=args.timeout,
        max_retries=args.max_retries,
        rate_limit=args.rate_limit,
        attach_dir_name=args.attach_dir_name,
        download=bool(args.download),
        name_template=args.name_template,
        seq_width=args.seq_width,
        max_name_len=args.max_name_len,
        save_report=args.save_report,
        verbose=bool(args.verbose),
        backup=bool(args.backup),
        vision=bool(args.vision),
        chunk_size=max(1, int(args.chunk_size or 5)),
        intent_language=getattr(args, "intent_language", DEFAULT_INTENT_LANGUAGE),
        reason_language=getattr(args, "reason_language", DEFAULT_REASON_LANGUAGE),
    )

    try:
        if args.mode == "pick-one":
            # 单图选择默认开启视觉理解
            cfg.vision = True if not args.vision else bool(args.vision)
            process_document_pick_one(args.path, cfg, getattr(args, "index", 1))
        else:
            process_document(args.path, cfg)
    except KeyboardInterrupt:
        print("\n⏹️ 已中断")
    except Exception as e:
        print(f"❌ 运行失败：{e}")
        sys.exit(2)

if __name__ == "__main__":
    main()
