
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 Markdown 文档中的远程图片下载到文档同级目录下的 attachment 子文件夹，并把文档中的图片引用改为本地相对路径。
- 支持处理单个 .md 文件，或指定文件夹内（可递归）所有 .md 文件
- 兼容 Obsidian（相对路径形式，如 attachment/xxx.png）
- 处理以下图片引用形式：
  * Markdown 内联图片语法: ![alt](url "title")
  * HTML <img src="..."/> 标签
  * Obsidian 嵌入: ![[...]]（若为 http/https 则下载并替换为本地路径；若为本地则保持）
  * Markdown 引用式定义: [id]: url "title"（会更新 url 为本地路径）
注意：
- 已为本地文件（相对路径存在）或 data: / obsidian:// / file:// 的引用将跳过
- 如下载文件名冲突，将自动加 (1), (2), ... 后缀
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
import json
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse, unquote
from urllib.request import Request, urlopen

ATTACH_DIR_NAME_DEFAULT = "attachment"
DEFAULT_TIMEOUT = 25
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) md-image-localizer/1.0"
ACCEPT_HEADER = "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"

# 常见 Content-Type 到扩展名的映射
CONTENT_TYPE_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "image/svg+xml": ".svg",
    "image/tiff": ".tiff",
    "image/x-icon": ".ico",
    "image/heic": ".heic",
}

# 支持的图片扩展名集合
IMAGE_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".tif", ".tiff", ".ico", ".heic",
}

# 正则模式
MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(((?:[^()\\]|\\.|(?:\([^()]*\)))+)\)")
HTML_IMG_RE = re.compile(r'(<img\b[^>]*\bsrc=["\'])([^"\']+)(["\'][^>]*>)', re.IGNORECASE)
WIKILINK_EMBED_RE = re.compile(r"!\[\[(.*?)\]\]")
# Markdown 引用式定义，如: [id]: https://example.com/img.png "title"
REF_DEF_RE = re.compile(r'^\s*\[([^\]]+)\]:\s*(\S+)(?:\s+(".*?"|\'.*?\'|\(.*?\)))?\s*$', re.MULTILINE)


def is_remote_url(url: str) -> bool:
    low = url.strip().lower()
    return low.startswith("http://") or low.startswith("https://")


def is_skippable_scheme(url: str) -> bool:
    low = url.strip().lower()
    return (
        low.startswith("data:")
        or low.startswith("obsidian://")
        or low.startswith("file://")
    )


def guess_ext_from_content_type(content_type: Optional[str]) -> Optional[str]:
    if not content_type:
        return None
    ct = content_type.split(";")[0].strip().lower()
    return CONTENT_TYPE_TO_EXT.get(ct)


def sanitize_filename(name: str) -> str:
    # Windows 不允许的字符: \ / : * ? " < > |
    forbidden = '\\/:*?"<>|'
    safe = "".join(ch for ch in name if ch not in forbidden)
    # 清理控制字符和尾部空格/点（Windows）
    safe = "".join(ch for ch in safe if ch.isprintable())
    safe = safe.strip(" .")
    return safe or "image"


def ensure_unique_path(dest_dir: Path, filename: str) -> Path:
    base = Path(filename).stem
    ext = Path(filename).suffix
    candidate = dest_dir / (base + ext)
    idx = 1
    while candidate.exists():
        candidate = dest_dir / f"{base} ({idx}){ext}"
        idx += 1
    return candidate


def extract_filename_from_url(url: str) -> Tuple[str, Optional[str]]:
    """
    从 URL 提取原始文件名（去除查询/片段），返回 (basename_without_query, ext_if_any)
    """
    parsed = urlparse(url)
    path = parsed.path or ""
    name = os.path.basename(path)
    name = unquote(name)
    # 去除可能残留的非法字符
    name = sanitize_filename(name)
    base, ext = os.path.splitext(name)
    return (name if name else "image", ext if ext else None)


def read_text_with_fallback(path: Path) -> str:
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


def split_md_target(raw: str) -> Tuple[str, str]:
    """
    解析 Markdown () 内的 target，拆出 url 与尾随 title/参数片段
    例如：
      'https://a/b.png "title"' -> ('https://a/b.png', ' "title"')
      '<https://a/b.png> "t"' -> ('https://a/b.png', ' "t"')
    """
    s = raw.strip()
    # 尖括号包裹的 URL，例如 <https://a/b.png> "title"
    if s.startswith("<") and ">" in s:
        end = s.find(">")
        url = s[1:end].strip()
        trailing = s[end + 1 :].rstrip()
        return url, (" " + trailing) if trailing else ""
    # 非尖括号，取第一个空白前为 URL
    parts = s.split()
    if not parts:
        return "", ""
    url = parts[0].strip()
    trailing = s[len(parts[0]) :].rstrip()
    return url, trailing if trailing.startswith(" ") else ((" " + trailing) if trailing else "")


def download_image(
    url: str,
    dest_dir: Path,
    timeout: int,
    preferred_basename: Optional[str] = None,
    ext_hint: Optional[str] = None,
    retries: int = 2,
    retry_delay: float = 1.2,
) -> Optional[Path]:
    """
    下载图片到 dest_dir，返回最终保存的 Path（唯一文件名）。失败返回 None。
    支持重试与退避；统一 UA/Accept 头；按 Content-Type 猜扩展。
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": ACCEPT_HEADER})
            with urlopen(req, timeout=timeout) as resp:
                content = resp.read()
                content_type = resp.headers.get("Content-Type", "")

                # 文件名与扩展名处理
                raw_name, ext_from_url = extract_filename_from_url(url)
                ext = None
                if ext_hint and ext_hint.startswith("."):
                    ext = ext_hint
                elif ext_from_url:
                    ext = ext_from_url
                else:
                    guessed = guess_ext_from_content_type(content_type)
                    if guessed:
                        ext = guessed
                # 如果最终仍无扩展名，给个默认 .img
                if not ext:
                    ext = ".img"

                base = preferred_basename if preferred_basename else sanitize_filename(os.path.splitext(raw_name)[0])
                base = base.strip(" .")
                filename = f"{base}{ext}"
                final_path = ensure_unique_path(dest_dir, filename)
                final_path.write_bytes(content)
                if attempt > 0:
                    print(f"ℹ️ 重试成功：{url}")
                return final_path
        except Exception as e:
            last_err = e
            if attempt < retries:
                try:
                    time.sleep(retry_delay)
                except Exception:
                    pass
            else:
                print(f"❌ 下载失败：{url} -> {e}")
    return None


class FileProcessor:
    def __init__(
        self,
        md_path: Path,
        attach_dir_name: str,
        timeout: int,
        dry_run: bool,
        rename_images: bool = False,
        rename_strategy: str = "context",
        max_name_len: int = 80,
        retry: int = 2,
        retry_delay: float = 1.2,
    ):
        self.md_path = md_path
        self.md_dir = md_path.parent
        self.attach_dir = self.md_dir / attach_dir_name
        self.timeout = timeout
        self.dry_run = dry_run
        self.rename_images = rename_images
        self.rename_strategy = rename_strategy
        self.max_name_len = max_name_len
        self.retry = retry
        self.retry_delay = retry_delay
        # 相同 URL 在同一文件内重复出现时共用一次下载
        self.url_cache: Dict[str, Path] = {}
        # 处理时上下文
        self.current_text: str = ""
        self.doc_title: Optional[str] = None
        self.image_seq: int = 0
        # 位置与命名状态（用于“上一图到当前图之间的文字”图意提取）
        self.last_image_pos: int = 0
        self.last_intent: Optional[str] = None
        self.block_index: int = 0
        self.block_image_index: int = 0
        # 监控数据
        self.remote_expected: int = 0
        self.remaining_remote: list[Dict] = []

    def is_local_existing(self, src: str) -> bool:
        # 相对路径或绝对路径（位于库内）是否已存在
        if is_remote_url(src) or is_skippable_scheme(src):
            return False
        # 规范化到文件所在目录
        try:
            candidate = (self.md_dir / Path(src)).resolve()
        except Exception:
            return False
        return candidate.exists()

    def url_to_local_rel(
        self,
        url: str,
        *,
        alt: Optional[str] = None,
        alias: Optional[str] = None,
        trailing_title: Optional[str] = None,
        html_tag: Optional[str] = None,
        match_pos: Optional[int] = None,
    ) -> str:
        """
        将远程 URL 下载为本地文件，返回相对路径（以 md 文件所在目录为基准，posix 分隔）。
        会根据配置选择是否重命名图片文件。
        """
        if url in self.url_cache:
            local_path = self.url_cache[url]
        else:
            preferred_basename: Optional[str] = None
            # 扩展名提示来自 URL
            _, ext_from_url = extract_filename_from_url(url)
            ext_hint = ext_from_url

            if self.rename_images:
                if not self.doc_title:
                    self.doc_title = self._extract_doc_title(self.current_text)
                preferred_basename = self._suggest_image_basename(
                    url=url,
                    alt=alt,
                    alias=alias,
                    trailing_title=trailing_title,
                    html_tag=html_tag,
                    match_pos=match_pos,
                )

            if self.dry_run:
                # 预览模式：构造一个预期的文件名（不落盘）
                base = preferred_basename if preferred_basename else sanitize_filename(os.path.splitext(extract_filename_from_url(url)[0])[0])
                base = base[: self.max_name_len].strip(" .")
                ext = ext_hint if ext_hint else ".img"
                if not ext.startswith("."):
                    ext = "." + ext
                filename = f"{base}{ext}"
                local_path = self.attach_dir / filename
            else:
                # 实际下载，带重试与容错
                try:
                    local_path_opt = download_image(
                        url,
                        self.attach_dir,
                        self.timeout,
                        preferred_basename=preferred_basename[: self.max_name_len] if preferred_basename else None,
                        ext_hint=ext_hint,
                        retries=self.retry,
                        retry_delay=self.retry_delay,
                    )
                    if local_path_opt is None:
                        # 下载失败：返回原始 url（不改写，不纳入缓存/计数）
                        return url
                    local_path = local_path_opt
                    # 仅在实际下载成功时增加序号并缓存
                    self.image_seq += 1
                    self.url_cache[url] = local_path
                except Exception as e:
                    print(f"⚠️ 下载异常：{url} -> {e}")
                    return url

        rel = os.path.relpath(local_path, self.md_dir).replace("\\", "/")
        return rel

    def relocate_or_rename_local(
        self,
        src: str,
        *,
        alt: Optional[str] = None,
        alias: Optional[str] = None,
        trailing_title: Optional[str] = None,
        html_tag: Optional[str] = None,
        match_pos: Optional[int] = None,
    ) -> str:
        """
        将已有本地图片移动/重命名到 attachment 并返回新的相对路径。
        - 若已在 attachment 且文件名符合期望，则保持不变
        - dry-run 模式下仅返回预期路径，不实际变更
        """
        # 解析本地路径
        try:
            src_path = (self.md_dir / Path(src)).resolve()
        except Exception:
            return src
        if not src_path.exists():
            return src

        # 扩展名
        ext = src_path.suffix
        if not ext:
            ext = ".img"
        if not ext.startswith("."):
            ext = "." + ext

        # 目标基本名
        if self.rename_images:
            if not self.doc_title:
                self.doc_title = self._extract_doc_title(self.current_text)
            base = self._suggest_image_basename(
                url=str(src_path),
                alt=alt,
                alias=alias,
                trailing_title=trailing_title,
                html_tag=html_tag,
                match_pos=match_pos,
            )
        else:
            base = sanitize_filename(src_path.stem)

        base = base[: self.max_name_len].strip(" .")
        filename = f"{base}{ext}"
        dest_dir = self.attach_dir

        if self.dry_run:
            dest_path = dest_dir / filename
            return os.path.relpath(dest_path, self.md_dir).replace("\\", "/")

        # 实际重命名/搬移
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = ensure_unique_path(dest_dir, filename)

        try:
            if src_path == dest_path:
                pass
            elif src_path.parent == dest_dir:
                src_path.rename(dest_path)
            else:
                # 若不在 attachment，则复制到 attachment（避免破坏外部原始资源）
                dest_path.write_bytes(src_path.read_bytes())
            self.image_seq += 1
        except Exception:
            # 失败则返回原始相对路径
            return os.path.relpath(src_path, self.md_dir).replace("\\", "/")

        return os.path.relpath(dest_path, self.md_dir).replace("\\", "/")

    def _extract_doc_title(self, text: str) -> str:
        """
        提取文档标题：
        - 优先 YAML frontmatter 中的 parent 或 title
        - 否则取第一条 Markdown 标题行（# 或 ##）
        - 再否则用文件名（不含扩展名）
        """
        # YAML frontmatter
        m = re.match(r"^---\s*(.*?)\s*---", text, flags=re.DOTALL)
        if m:
            fm = m.group(1)
            # 简单查找 parent/title 字段
            for key in ["parent", "title", "Parent", "Title"]:
                km = re.search(rf"^\s*{key}\s*:\s*(.+)$", fm, flags=re.MULTILINE)
                if km:
                    candidate = km.group(1).strip().strip("'\"")
                    if candidate:
                        return sanitize_filename(candidate)
        # Markdown 标题
        for line in text.splitlines():
            l = line.strip()
            if l.startswith("#"):
                ttl = l.lstrip("#").strip()
                if ttl:
                    return sanitize_filename(ttl)
        # 文件名
        return sanitize_filename(self.md_path.stem)

    def _tokenize_keywords(self, s: str) -> list[str]:
        """
        提取上下文关键词（中英文），去重保序。
        """
        if not s:
            return []
        chinese = re.findall(r"[\u4e00-\u9fff]{2,}", s)
        english = re.findall(r"[A-Za-z]{4,}", s)
        tokens = chinese + english
        seen = set()
        unique = []
        for t in tokens:
            if t not in seen:
                seen.add(t)
                unique.append(t)
        return unique

    def _clean_title_fragment(self, s: Optional[str]) -> str:
        if not s:
            return ""
        s = s.strip()
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            s = s[1:-1]
        if s.startswith("(") and s.endswith(")"):
            s = s[1:-1]
        return s.strip()

    def _suggest_image_basename(
        self,
        url: str,
        alt: Optional[str],
        alias: Optional[str],
        trailing_title: Optional[str],
        html_tag: Optional[str],
        match_pos: Optional[int],
    ) -> str:
        """
        依据重命名策略生成图片基名。
        - seq：文件标题 + 两位出现序号（示例：标题_01）
        - context：段落摘要 + 图意编号（示例：标题_段落摘要_图意01）
        - simple/semantic：沿用 context 生成逻辑
        """
        idx = self.image_seq + 1  # 预估序号（下载后会自增）
        doc_title = self.doc_title or self._extract_doc_title(self.current_text)

        def _strip_trailing_image_ext(s: str) -> str:
            if not s:
                return s
            s2 = re.sub(r"(?i)(?:[._\-\s])?(?:png|jpe?g|gif|webp|bmp|svg|tiff?|ico|heic)$", "", s)
            return s2.rstrip(" ._")

        if (self.rename_strategy or "").lower() == "seq":
            # 固定格式：<文档标题> + 两位全局序号（示例：标题_01）
            base = f"{doc_title}_{idx:02d}"
            base = sanitize_filename(base)
            base = _strip_trailing_image_ext(base)
            if len(base) > self.max_name_len:
                base = base[: self.max_name_len].rstrip(" ._")
            return base

        # 默认/其它策略：原“段落摘要 + 图意编号”
        context_desc = self._analyze_paragraph_context(match_pos)
        if context_desc:
            clean_desc = re.sub(r'[^\w\u4e00-\u9fff]+', '_', context_desc).strip('_')
            base = f"{doc_title}_{clean_desc}_图意{idx}"
        else:
            base = f"{doc_title}_图意{idx}"
        base = sanitize_filename(base)
        base = _strip_trailing_image_ext(base)
        if len(base) > self.max_name_len:
            base = base[: self.max_name_len].rstrip(" ._")
        return base

    def _analyze_paragraph_context(self, match_pos: Optional[int]) -> str:
        """
        分析图片所在段落的上下文，返回简洁的段落内容总结。
        """
        if match_pos is None or not self.current_text:
            return ""

        lines = self.current_text.splitlines()
        if match_pos >= len(self.current_text):
            return ""

        # 找到图片所在的行
        current_line_idx = 0
        current_pos = 0
        for i, line in enumerate(lines):
            if current_pos <= match_pos < current_pos + len(line) + 1:  # +1 for newline
                current_line_idx = i
                break
            current_pos += len(line) + 1

        # 向上查找最近的非空段落（跳过标题行）
        paragraph_lines = []
        for i in range(current_line_idx, -1, -1):
            line = lines[i].strip()
            if not line:
                if paragraph_lines:  # 遇到空行且已有内容，停止
                    break
                continue

            # 跳过标题行（以#开头或全大写标题）
            if line.startswith('#') or (line.isupper() and len(line) < 50):
                if not paragraph_lines:  # 如果还没找到内容，继续找
                    continue
                break

            paragraph_lines.insert(0, line)

            # 如果找到足够的内容（超过100字符），停止
            if sum(len(l) for l in paragraph_lines) > 100:
                break

        # 向下查找补充内容
        for i in range(current_line_idx + 1, len(lines)):
            line = lines[i].strip()
            if not line:
                break

            if line.startswith('#') or (line.isupper() and len(line) < 50):
                break

            paragraph_lines.append(line)

            if sum(len(l) for l in paragraph_lines) > 200:
                break

        # 合并段落内容
        paragraph_text = ' '.join(paragraph_lines)

        # 提取关键词并生成简洁描述
        return self._summarize_paragraph(paragraph_text)

    def _summarize_paragraph(self, text: str) -> str:
        """
        从段落文本中提取关键信息生成简洁描述。
        - 先清理图片语法/标签与裸露的图片文件名，避免把“png/jpg”等噪声混入摘要
        """
        if not text.strip():
            return ""

        # 1) 清理 HTML 标签与 Markdown/Obsidian 图片语法
        try:
            text2 = re.sub(r"<[^>]+>", "", text)
        except Exception:
            text2 = text
        try:
            text2 = MD_IMAGE_RE.sub("", text2)
        except Exception:
            pass
        try:
            text2 = WIKILINK_EMBED_RE.sub("", text2)
        except Exception:
            pass
        # 2) 清理裸露的图片链接/文件名（*.png/jpg/...）
        text2 = re.sub(r"(?i)\b\S+\.(?:png|jpe?g|gif|webp|bmp|svg|tiff?|ico|heic)\b", "", text2)

        # 3) 移除常见的文章标记和多余符号
        text2 = re.sub(r'[『』「」【】《》()（）\*\-\+\=\[\]{}|\\]', '', text2)

        # 4) 分句
        sentences = re.split(r'[。！？；]', text2)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return ""

        # 5) 优先选择包含关键生物学术语的句子
        key_terms = ['双壳纲', '船蛆', '巨型船蛆', '足丝', '鳃', '壳', '钻木', '习性', '外观', '结构', '照片', '示意图']

        selected_sentences = []
        for sentence in sentences:
            if any(term in sentence for term in key_terms):
                selected_sentences.append(sentence)
                if len(selected_sentences) >= 2:  # 最多选2句
                    break

        if not selected_sentences:
            selected_sentences = sentences[:2]

        # 6) 合并并截断
        summary = ' '.join(selected_sentences)
        if len(summary) > 50:
            summary = summary[:47] + "..."
        return summary.strip()

    def _derive_intent_between(self, prev_pos: int, curr_pos: int) -> str:
        """
        提取“上一张图片到当前图片之间”的文本意图摘要。
        - 过滤掉过短或只有标点/空白的片段
        - 使用现有段落摘要器生成简洁图意
        """
        if not self.current_text:
            return ""
        try:
            raw = self.current_text[prev_pos:curr_pos]
        except Exception:
            return ""
        snippet = re.sub(r"\s+", " ", raw).strip()
        # 至少包含若干可见字符（中文/英文/数字）
        visible_chars = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", snippet)
        if len(visible_chars) < 4:
            return ""
        return self._summarize_paragraph(snippet)

    def _update_intent_and_counters(self, match_pos: Optional[int]) -> tuple[str, int, int]:
        """
        根据当前位置更新图意与计数器：
        - 若有新图意：块序号 +1，块内图片序号置 1，更新 last_intent
        - 若无新文字但已有 last_intent：沿用图意，块内图片序号 +1
        - 若无任何图意：使用占位“图意”，初始化块序与序号
        返回 (intent_str, block_index, block_image_index)
        """
        curr = match_pos or 0
        intent = self._derive_intent_between(self.last_image_pos, curr)
        if intent:
            clean_intent = re.sub(r'[^\w\u4e00-\u9fff]+', '_', intent).strip('_')
            if self.last_intent != clean_intent:
                self.block_index += 1
                self.block_image_index = 1
                self.last_intent = clean_intent
            else:
                self.block_image_index += 1
            self.last_image_pos = curr
            return self.last_intent or "", self.block_index, self.block_image_index

        # 无实际文字：沿用上一图意（若有）
        if self.last_intent:
            self.block_image_index += 1
            self.last_image_pos = curr
            return self.last_intent, self.block_index, self.block_image_index

        # 首次且没有可提取的图意：初始化为占位块
        if self.block_index == 0:
            self.block_index = 1
        self.block_image_index = max(self.block_image_index, 1)
        self.last_image_pos = curr
        return "", self.block_index, self.block_image_index

    def replace_md_inline(self, m: re.Match) -> str:
        alt = m.group(1)
        raw_target = m.group(2)
        url, trailing = split_md_target(raw_target)
        if not url or is_skippable_scheme(url):
            return m.group(0)

        # 从 trailing 中尝试提取 "title"
        title_match = re.search(r'(".*?"|\'.*?\')', trailing or "")
        title = None
        if title_match:
            title = title_match.group(0)

        def _clean_alt(a: Optional[str]) -> str:
            alt_raw = a or ""
            alt_clean = re.sub(r"<[^>]+>", "", alt_raw)
            alt_clean = alt_clean.replace("|", " ").strip()
            alt_clean = re.sub(r"\s+", " ", alt_clean).strip()
            return alt_clean

        def _title_trailing(t: Optional[str]) -> str:
            ttext = (t or "").strip().strip('"').strip("'")
            return f' "{ttext}"' if ttext else ""

        if is_remote_url(url):
            new_rel = self.url_to_local_rel(
                url,
                alt=alt if alt else None,
                trailing_title=title,
                match_pos=m.start(),
            )
            return f"![{_clean_alt(alt)}]({new_rel}{_title_trailing(title)})"
        else:
            # 本地图片：如启用重命名，则进行重命名/搬移并更新链接
            if self.rename_images and self.is_local_existing(url):
                new_rel = self.relocate_or_rename_local(
                    url,
                    alt=alt if alt else None,
                    trailing_title=title,
                    match_pos=m.start(),
                )
                return f"![{_clean_alt(alt)}]({new_rel}{_title_trailing(title)})"
            return m.group(0)

    def replace_html_img(self, m: re.Match) -> str:
        head, src, tail = m.groups()
        if not src or is_skippable_scheme(src):
            return m.group(0)

        full_tag = f"{head}{src}{tail}"
        alt_attr = None
        alt_m = re.search(r'\balt=["\']([^"\']+)["\']', full_tag, flags=re.IGNORECASE)
        if alt_m:
            alt_attr = alt_m.group(1)

        if is_remote_url(src):
            new_rel = self.url_to_local_rel(
                src,
                alt=alt_attr,
                html_tag=full_tag,
                match_pos=m.start(),
            )
            return f'{head}{new_rel}{tail}'
        else:
            # 本地图片：如启用重命名，则进行重命名/搬移并更新链接
            if self.rename_images and self.is_local_existing(src):
                new_rel = self.relocate_or_rename_local(
                    src,
                    alt=alt_attr,
                    html_tag=full_tag,
                    match_pos=m.start(),
                )
                return f'{head}{new_rel}{tail}'
            return m.group(0)

    def replace_wikilink_embed(self, m: re.Match) -> str:
        inside = m.group(1).strip()
        # 可能带别名，如 target|alias
        if "|" in inside:
            target, alias = inside.split("|", 1)
            target = target.strip()
            alias = alias.strip()
        else:
            target, alias = inside, None

        if not target or is_skippable_scheme(target):
            return m.group(0)
        if is_remote_url(target):
            new_rel = self.url_to_local_rel(
                target,
                alias=alias,
                match_pos=m.start(),
            )
            return f"![[{new_rel}|{alias}]]" if alias else f"![[{new_rel}]]"
        else:
            # 本地图片的 wikilink：仅对图片扩展名进行重命名处理
            suffix = Path(target).suffix.lower()
            if self.rename_images and suffix in IMAGE_EXTS and self.is_local_existing(target):
                new_rel = self.relocate_or_rename_local(
                    target,
                    alias=alias,
                    match_pos=m.start(),
                )
                return f"![[{new_rel}|{alias}]]" if alias else f"![[{new_rel}]]"
            return m.group(0)

    def replace_ref_defs(self, text: str) -> str:
        """
        处理引用式图片/链接定义，把远程 URL 下载到本地并改写为本地路径。
        """
        def _rep(m: re.Match) -> str:
            key = m.group(1)
            url = m.group(2)
            title = m.group(3) or ""
            if url and is_remote_url(url) and not is_skippable_scheme(url):
                new_rel = self.url_to_local_rel(url)
                return f"[{key}]: {new_rel}{(' ' + title) if title else ''}"
            return m.group(0)
        return REF_DEF_RE.sub(_rep, text)

    def process(self) -> Tuple[int, int, int]:
        """
        处理单个 md 文件，返回 (下载数, 替换数, 引用式定义替换数)
        """
        original = read_text_with_fallback(self.md_path)
        text = original

        # 统计预期远程图片数量（用于二次校验）
        remote_expected = 0
        try:
            # Markdown 内联
            for m in MD_IMAGE_RE.finditer(original):
                url, _ = split_md_target(m.group(2))
                if url and is_remote_url(url) and not is_skippable_scheme(url):
                    remote_expected += 1
            # HTML <img>
            for m in HTML_IMG_RE.finditer(original):
                src = m.group(2)
                if src and is_remote_url(src) and not is_skippable_scheme(src):
                    remote_expected += 1
            # Obsidian 嵌入
            for m in WIKILINK_EMBED_RE.finditer(original):
                inside = m.group(1).strip()
                tgt = inside.split("|", 1)[0].strip()
                if tgt and is_remote_url(tgt) and not is_skippable_scheme(tgt):
                    remote_expected += 1
        except Exception:
            remote_expected = 0
        # 记录到实例，便于二次校验与报告
        self.remote_expected = remote_expected

        # 为替换阶段准备上下文
        self.current_text = original
        self.doc_title = self._extract_doc_title(original)
        self.image_seq = 0
        # 初始化图意/分组计数器
        self.last_image_pos = 0
        self.last_intent = None
        self.block_index = 0
        self.block_image_index = 0
        self.url_cache.clear()

        # 先处理引用式定义
        before = text
        text = self.replace_ref_defs(text)
        ref_repl = 0 if text == before else len(list(REF_DEF_RE.finditer(before)))  # 近似

        # 处理 Markdown 内联
        before = text
        text = MD_IMAGE_RE.sub(self.replace_md_inline, text)
        inline_repl = 0 if text == before else 1  # 统计粗略为是否发生变化

        # 处理 HTML <img>
        before = text
        text = HTML_IMG_RE.sub(self.replace_html_img, text)
        html_repl = 0 if text == before else 1

        # 处理 Obsidian 嵌入
        before = text
        text = WIKILINK_EMBED_RE.sub(self.replace_wikilink_embed, text)
        embed_repl = 0 if text == before else 1

        # 下载总数 = 实际缓存的远程 url 个数（dry-run 为 0）
        download_count = 0 if self.dry_run else len(self.url_cache)

        # 扫描剩余远程引用（行号/类型/URL），用于核验报告
        remaining: list[Dict] = []
        try:
            # MD 内联
            for m in MD_IMAGE_RE.finditer(text):
                url, _ = split_md_target(m.group(2))
                if url and is_remote_url(url) and not is_skippable_scheme(url):
                    remaining.append({"kind": "md", "url": url, "line": text[:m.start()].count("\n") + 1})
            # HTML <img>
            for m in HTML_IMG_RE.finditer(text):
                src = m.group(2)
                if src and is_remote_url(src) and not is_skippable_scheme(src):
                    remaining.append({"kind": "html", "url": src, "line": text[:m.start()].count("\n") + 1})
            # Obsidian 嵌入
            for m in WIKILINK_EMBED_RE.finditer(text):
                inside = m.group(1).strip()
                tgt = inside.split("|", 1)[0].strip()
                if tgt and is_remote_url(tgt) and not is_skippable_scheme(tgt):
                    remaining.append({"kind": "wikilink", "url": tgt, "line": text[:m.start()].count("\n") + 1})
        except Exception:
            remaining = []
        self.remaining_remote = remaining

        # 二次校验与提示（仅在非 dry-run 下）
        if not self.dry_run and self.remote_expected > 0 and download_count < self.remote_expected:
            try:
                print(f"⚠️ 远程图片下载不完全：预期 {self.remote_expected}，实际下载 {download_count}。剩余远程 {len(self.remaining_remote)} 处。")
                for r in self.remaining_remote[:10]:
                    print(f"   • [{r['kind']}] line {r['line']}: {r['url']}")
                if len(self.remaining_remote) > 10:
                    print(f"   • 其余 {len(self.remaining_remote) - 10} 处已省略…")
            except Exception:
                pass

        # 如内容变化则写回
        if text != original and not self.dry_run:
            write_text_utf8(self.md_path, text)

        replace_total = (inline_repl + html_repl + embed_repl)
        return download_count, replace_total, ref_repl


def find_md_files(target: Path, recursive: bool) -> list[Path]:
    results: list[Path] = []
    if target.is_file() and target.suffix.lower() == ".md":
        return [target.resolve()]
    if target.is_dir():
        if recursive:
            for p in target.rglob("*.md"):
                if p.is_file():
                    results.append(p.resolve())
        else:
            for p in target.glob("*.md"):
                if p.is_file():
                    results.append(p.resolve())
    return sorted(results)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download remote images referenced in Markdown into a local 'attachment' folder next to each Markdown file, then rewrite references to local relative paths (Obsidian-compatible).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("path", type=Path, help="Path to a Markdown file or a folder containing Markdown files")
    parser.add_argument("-r", "--recursive", action="store_true", help="Recursively process subfolders when 'path' is a folder")
    parser.add_argument("--attach-dir-name", default=ATTACH_DIR_NAME_DEFAULT, help="Attachment folder name to create next to each Markdown file")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="HTTP timeout (seconds) when downloading images")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without downloading or modifying files")
    parser.add_argument("--rename-images", action="store_true", help="Rename downloaded images using document title and nearby context")
    parser.add_argument("--rename-strategy", choices=["simple", "context", "semantic", "seq"], default="seq", help="Strategy when renaming images (seq: 标题+两位全局编号，如 {title}_{index:02d})")
    parser.add_argument("--max-name-len", type=int, default=80, help="Maximum base filename length when renaming images")
    parser.add_argument("--retry", type=int, default=2, help="Retry count for image downloads")
    parser.add_argument("--retry-delay", type=float, default=1.2, help="Delay (seconds) between retries")
    parser.add_argument("--report", type=Path, default=None, help="Write an aggregated JSON report of processing results")
    return parser

def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = build_parser()
    args = parser.parse_args()

    target: Path = args.path.expanduser()
    if not target.exists():
        print(f"❌ Path not found: {target}")
        sys.exit(1)

    md_files = find_md_files(target, args.recursive)
    if not md_files:
        print("⚠️ No Markdown files found to process.")
        sys.exit(0)

    total_would_dl = 0
    total_repl = 0
    total_ref = 0
    processed = 0

    print(f"🔍 Found {len(md_files)} Markdown file(s). {'[dry-run]' if args.dry_run else ''}")
    reports: list[Dict] = []
    for md in md_files:
        try:
            processor = FileProcessor(
                md,
                args.attach_dir_name,
                args.timeout,
                args.dry_run,
                args.rename_images,
                args.rename_strategy,
                args.max_name_len,
                retry=args.retry,
                retry_delay=args.retry_delay,
            )
            dl, repl, ref = processor.process()
            processed += 1
            total_would_dl += len(processor.url_cache)
            total_repl += repl
            total_ref += ref
            rel_md = os.path.relpath(md, Path.cwd())
            if args.dry_run:
                print(f"  • {rel_md} -> would download {len(processor.url_cache)} image(s), replace {repl} block(s), update {ref} reference(s)")
            else:
                print(f"  • {rel_md} -> downloaded {dl} image(s), replaced {repl} block(s), updated {ref} reference(s)")
                # 智能核验：剩余远程引用逐条列出（最多 10 条）
                if getattr(processor, "remaining_remote", []):
                    print(f"    Remaining remote refs ({len(processor.remaining_remote)}):")
                    for r in processor.remaining_remote[:10]:
                        print(f"      - [{r.get('kind')}] line {r.get('line')}: {r.get('url')}")
                    if len(processor.remaining_remote) > 10:
                        print(f"      - ... {len(processor.remaining_remote) - 10} more")
            # 汇总报告
            reports.append({
                "md": str(md),
                "downloaded": dl,
                "replaced_blocks": repl,
                "updated_ref_defs": ref,
                "remote_expected": getattr(processor, "remote_expected", 0),
                "remaining_remote_count": len(getattr(processor, "remaining_remote", [])),
                "remaining_remote": getattr(processor, "remaining_remote", []),
            })
        except Exception as e:
            print(f"  • {md} -> Error: {e}")

    print("——")
    if args.dry_run:
        print(f"✅ Dry-run complete. Processed {processed} file(s). Would download {total_would_dl} image(s). Would replace {total_repl} block(s). Would update {total_ref} reference definition(s).")
    else:
        print(f"✅ Done. Processed {processed} file(s). Downloaded {total_would_dl} image(s). Replaced {total_repl} block(s). Updated {total_ref} reference definition(s).")
        # 写报告（如指定）
        if args.report:
            try:
                report_path = args.report.expanduser().resolve()
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"📝 Report written: {report_path}")
            except Exception as e:
                print(f"⚠️ Failed to write report: {e}")

if __name__ == "__main__":
    main()
