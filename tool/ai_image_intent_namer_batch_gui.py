#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 图片“图意”命名器 - 批量 GUI（串行调度，分标签页独立审核/应用）
"""

from __future__ import annotations

import json
import os
import random
import re
import threading
import time
import copy
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

try:
    from PIL import Image, ImageTk  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Image = None
    ImageTk = None

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    requests = None

import sys

THIS_FILE = Path(__file__).resolve()
TOOL_DIR = THIS_FILE.parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

try:
    import ai_image_intent_namer as core
    from ai_image_intent_namer import (
        Config,
        process_document,
        read_text,
        write_text_utf8,
        extract_doc_title,
        collect_images,
        find_neighbor_text,
        name_with_template,
        sanitize_filename,
        ensure_unique_path,
        is_remote_url,
        build_ai_messages,
        call_openai_chat,
        safe_parse_json,
        validate_ai_result,
        normalize_base_url,
        is_siliconflow,
        resolve_local_image,
        get_last_llm_error,
        collect_images_to_attachment,
        load_image_mapping,
        save_image_mapping,
        ensure_attachment_for_src,
        update_mapping_target,
        build_attachment_plan,
        execute_attachment_plan,
        load_attachment_plan,
        save_attachment_plan,
        plan_file_path,
        normalize_embedded_html_images,
        MD_IMAGE_RE,
        WHITESPACE_RE,
    )
except Exception as e:  # pragma: no cover - bootstrap failure
    print("❌ 无法导入后端模块 ai_image_intent_namer.py，请确认该文件位于同目录")
    print("错误:", e)
    sys.exit(1)

try:
    import md_image_localizer as mil  # type: ignore
    from md_image_localizer import FileProcessor as MILFileProcessor  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    mil = None
    MILFileProcessor = None

try:  # pragma: no cover - platform specific
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

APP_TITLE = "AI 图片“图意”命名器（批量GUI，串行调度）"
PROFILES_PATH = TOOL_DIR / "ai_image_intent_namer_gui.profiles.json"
DEFAULT_NAME_TEMPLATE = "{title}_{index:02d}_{intent}"
DEFAULT_ATTACH_DIR = "attachments"
PLAN_HISTORY_FILENAME = ".image_plan.history.log"

VISION_TEST_ASSETS = [
    {
        "name": "红色像素",
        "description": "纯红色 1x1 PNG",
        "data_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8AARgAI/wlvrWcAAAAASUVORK5CYII=",
    },
    {
        "name": "绿色像素",
        "description": "纯绿色 1x1 PNG",
        "data_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/5+BFgAHggKBr+2qAAAAAElFTkSuQmCC",
    },
]

MD_INLINE_RE = re.compile(r"(\*\*|__)(.+?)\1|`([^`]+)`")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

CONTEXT_FONT_FAMILY = "Microsoft YaHei"
CONTEXT_FONT_SIZE = 12
CONTEXT_FONT = (CONTEXT_FONT_FAMILY, CONTEXT_FONT_SIZE)
CONTEXT_HEADING_FONT_1 = (CONTEXT_FONT_FAMILY, CONTEXT_FONT_SIZE + 2, "bold")
CONTEXT_HEADING_FONT_2 = (CONTEXT_FONT_FAMILY, CONTEXT_FONT_SIZE + 1, "bold")
CONTEXT_HEADING_FONT_3 = (CONTEXT_FONT_FAMILY, CONTEXT_FONT_SIZE, "bold")
CONTEXT_BOLD_FONT = (CONTEXT_FONT_FAMILY, CONTEXT_FONT_SIZE, "bold")
CONTEXT_CHAR_PER_LINE = 35
CONTEXT_MIN_LINES = 3
CONTEXT_MAX_LINES = 10
CONTEXT_EMPTY_LINES = 2


@dataclass
class ItemUI:
    index: int
    block_index: int
    image_index: int
    src: str
    above_text: str
    below_text: str
    between_text: str
    alt: Optional[str]
    title_attr: Optional[str]
    frame: tk.Frame
    intent_var: tk.StringVar
    final_var: tk.StringVar
    apply_one_btn: ttk.Button
    skip_var: tk.BooleanVar
    skip_check: ttk.Checkbutton


@dataclass
class TabState:
    md_path: Path
    title: str
    results: Dict
    page: ttk.Frame
    canvas: tk.Canvas
    inner_frame: tk.Frame
    scrollbar: ttk.Scrollbar
    item_uis: List[ItemUI]
    btn_refresh: ttk.Button
    btn_apply_all: ttk.Button
    btn_close: ttk.Button
    recalc_job: Optional[str] = None
    processing: bool = False
    completed: bool = False


class BatchApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self._init_styles()
        self.title(APP_TITLE)
        self.geometry("1100x720")
        self.minsize(1000, 650)

        self.files: List[Path] = []
        self.stop_flag = False
        self.tabs: Dict[str, TabState] = {}
        self.profiles: Dict[str, Dict] = {}

        self._build_widgets()
        self._load_profiles()

    # ------------------------------------------------------------------ #
    # UI 构建与日志
    # ------------------------------------------------------------------ #
    def _init_styles(self) -> None:
        style = ttk.Style(self)
        try:
            if "clam" in style.theme_names():
                style.theme_use("clam")
        except Exception:
            pass
        style.configure("Heading.TLabel", font=("Microsoft YaHei", 14, "bold"))
        style.configure("Subheading.TLabel", foreground="#666666")
        style.configure("Accent.TButton", padding=(12, 6), foreground="#ffffff", background="#1e88e5")
        style.map("Accent.TButton", background=[("active", "#1565c0"), ("disabled", "#90caf9")], foreground=[("disabled", "#eeeeee")])
        style.configure("TLabelFrame", padding=(12, 8))
        style.configure("TNotebook.Tab", padding=(18, 8))

    def _build_widgets(self) -> None:
        ttk.Label(self, text="批量处理 · Markdown 图片命名助手", style="Heading.TLabel").pack(side=tk.TOP, anchor="w", padx=20, pady=(16, 4))
        ttk.Label(self, text="选择多个 Markdown 文件后串行预览，可逐张重命名并写回。", style="Subheading.TLabel").pack(side=tk.TOP, anchor="w", padx=20, pady=(0, 12))

        top_region = ttk.Frame(self)
        top_region.pack(side=tk.TOP, fill=tk.X, padx=20, pady=(0, 10))
        top_region.columnconfigure(0, weight=3)
        top_region.columnconfigure(1, weight=2)

        files_frame = ttk.LabelFrame(top_region, text="批量文件")
        files_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(0, weight=1)

        list_container = ttk.Frame(files_frame, padding=(4, 0))
        list_container.grid(row=0, column=0, sticky="nsew")
        list_container.columnconfigure(0, weight=1)
        list_container.rowconfigure(0, weight=1)

        self.files_listbox = tk.Listbox(list_container, height=5, selectmode=tk.EXTENDED, relief=tk.FLAT, borderwidth=0)
        self.files_listbox.grid(row=0, column=0, sticky="nsew")
        list_scroll = ttk.Scrollbar(list_container, orient="vertical", command=self.files_listbox.yview)
        self.files_listbox.configure(yscrollcommand=list_scroll.set)
        list_scroll.grid(row=0, column=1, sticky="ns")

        btns_col = ttk.Frame(files_frame, padding=(0, 4))
        btns_col.grid(row=0, column=1, sticky="ns", padx=(8, 12), pady=10)
        ttk.Button(btns_col, text="添加文件...", style="Accent.TButton", command=self._on_add_files).pack(fill=tk.X, pady=(0, 8))
        ttk.Button(btns_col, text="移除选中", command=self._on_remove_selected).pack(fill=tk.X, pady=4)
        ttk.Button(btns_col, text="清空列表", command=self._on_clear_list).pack(fill=tk.X, pady=4)

        ai = ttk.LabelFrame(top_region, text="AI 参数与策略")
        ai.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        ai.columnconfigure(1, weight=1)
        ai.columnconfigure(3, weight=1)

        self.base_url_var = tk.StringVar(value=os.environ.get("OPENAI_BASE_URL", "https://api.siliconflow.cn"))
        self.api_key_var = tk.StringVar(value=os.environ.get("OPENAI_API_KEY", ""))
        self.model_var = tk.StringVar(value=os.environ.get("OPENAI_MODEL", "Qwen/Qwen2.5-VL-3B-Instruct"))
        self.timeout_var = tk.IntVar(value=120)
        self.retries_var = tk.IntVar(value=3)
        self.rate_limit_var = tk.DoubleVar(value=0.4)
        self.batch_size_var = tk.IntVar(value=5)

        # 翻译/归纳 独立API与Prompt（默认回落到主模型配置）
        self.trans_base_url_var = tk.StringVar(value=os.environ.get("TRANS_BASE_URL", self.base_url_var.get()))
        self.trans_api_key_var = tk.StringVar(value=os.environ.get("TRANS_API_KEY", self.api_key_var.get()))
        self.trans_model_var = tk.StringVar(value=os.environ.get("TRANS_MODEL", self.model_var.get()))
        self.sum_base_url_var = tk.StringVar(value=os.environ.get("SUM_BASE_URL", self.base_url_var.get()))
        self.sum_api_key_var = tk.StringVar(value=os.environ.get("SUM_API_KEY", self.api_key_var.get()))
        self.sum_model_var = tk.StringVar(value=os.environ.get("SUM_MODEL", self.model_var.get()))
        self.trans_prompt_var = tk.StringVar(
            value="你是专业翻译，请将以下文本翻译为简体中文，保留术语准确，忠实原意，不添加解释。只输出译文。"
        )
        self.sum_prompt_var = tk.StringVar(
            value="你是学术写作助手，请用简洁的中文为以下内容生成摘要，条理清晰，保留关键信息，不超过150字。只输出摘要。"
        )

        # 第一行：配置档和按钮
        ttk.Label(ai, text="配置档:").grid(row=0, column=0, sticky="w", padx=(8, 4), pady=6)
        self.profile_name_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(ai, textvariable=self.profile_name_var, values=[], width=18)
        self.profile_combo.grid(row=0, column=1, sticky="we", pady=6, padx=(0, 4))

        ttk.Button(ai, text="载入", command=self._on_profile_load).grid(row=0, column=2, padx=(2, 2), pady=6, sticky="w")
        ttk.Button(ai, text="测试API", command=self._on_test_api).grid(row=0, column=3, padx=(2, 2), pady=6, sticky="e")
        ttk.Button(ai, text="测试图片识别", command=self._on_test_vision).grid(row=0, column=4, padx=(2, 2), pady=6, sticky="w")
        ttk.Button(ai, text="API/模型配置...", style="Accent.TButton", command=self._open_api_config_dialog).grid(row=0, column=5, padx=(2, 6), pady=6, sticky="e")

        self.model_summary_var = tk.StringVar()
        ttk.Label(ai, textvariable=self.model_summary_var, foreground="#575757").grid(row=1, column=0, columnspan=6, sticky="we", padx=(8, 4), pady=(0, 8))

        # 第二行：策略和模板
        ttk.Label(ai, text="策略:").grid(row=2, column=0, sticky="w", padx=(8, 4))
        self.strategy_var = tk.StringVar(value="above")
        ttk.Combobox(ai, textvariable=self.strategy_var, values=["seq", "above", "below", "between", "intent", "hybrid"], width=12, state="readonly").grid(row=2, column=1, sticky="we", padx=(0, 6))

        ttk.Label(ai, text="命名模板:").grid(row=2, column=2, sticky="w", padx=(8, 4))
        self.template_var = tk.StringVar(value=DEFAULT_NAME_TEMPLATE)
        ttk.Entry(ai, textvariable=self.template_var, width=26).grid(row=2, column=3, sticky="we", padx=(0, 6))

        ttk.Label(ai, text="序号宽度:").grid(row=2, column=4, sticky="w", padx=(8, 4))
        self.seq_width_var = tk.IntVar(value=2)
        ttk.Spinbox(ai, from_=1, to=4, textvariable=self.seq_width_var, width=5).grid(row=2, column=5, sticky="w")

        ttk.Label(ai, text="每批张数:").grid(row=3, column=0, sticky="w", padx=(8, 4), pady=6)
        ttk.Spinbox(ai, from_=1, to=20, textvariable=self.batch_size_var, width=5).grid(row=3, column=1, sticky="w", padx=(0, 8), pady=6)


        # 选项
        opts = ttk.Frame(self)
        opts.pack(side=tk.TOP, fill=tk.X, padx=20, pady=(0, 10))
        self.verbose_var = tk.BooleanVar(value=True)
        self.backup_var = tk.BooleanVar(value=True)
        self.pre_localize_var = tk.BooleanVar(value=False)
        self.vision_var = tk.BooleanVar(value=True)
        self.attach_var = tk.StringVar(value=DEFAULT_ATTACH_DIR)
        self.max_len_var = tk.IntVar(value=80)
        self.normalize_html_var = tk.BooleanVar(value=True)
        self.template_var.trace_add("write", lambda *_: self._recalc_all_tabs())
        self.seq_width_var.trace_add("write", lambda *_: self._recalc_all_tabs())
        self.max_len_var.trace_add("write", lambda *_: self._recalc_all_tabs())

        ttk.Checkbutton(opts, text="详细日志", variable=self.verbose_var).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Checkbutton(opts, text="写回前备份（推荐）", variable=self.backup_var).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Checkbutton(opts, text="预先收集图片到附件目录", variable=self.pre_localize_var).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Checkbutton(opts, text="启用视觉理解(VLM)", variable=self.vision_var).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Checkbutton(opts, text="规范嵌套HTML图片", variable=self.normalize_html_var).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Label(opts, text="附件目录:").pack(side=tk.LEFT, padx=(8, 4))
        ttk.Entry(opts, textvariable=self.attach_var, width=16).pack(side=tk.LEFT)
        ttk.Label(opts, text="文件名最大长度:").pack(side=tk.LEFT, padx=(12, 4))
        ttk.Spinbox(opts, from_=30, to=200, textvariable=self.max_len_var, width=6).pack(side=tk.LEFT)

        # 操作按钮
        actions = ttk.Frame(self, padding=(20, 8))
        actions.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
        ttk.Button(actions, text="批量预览（串行）", style="Accent.TButton", command=self._on_batch_preview).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="停止", command=self._on_stop).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="退出", command=self.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Label(
            actions,
            text="提示：SiliconFlow 上多模态建议使用 *VL-Instruct* 类模型（例 Qwen/Qwen2.5-VL-3B-Instruct）。",
            foreground="#777",
        ).pack(side=tk.LEFT, padx=16)

        self.nb = ttk.Notebook(self)
        self.nb.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=20, pady=(0, 12))

        log_frame = ttk.LabelFrame(self, text="日志")
        log_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=20, pady=(0, 16))
        self.log_text = scrolledtext.ScrolledText(log_frame, height=7, wrap=tk.WORD, relief=tk.FLAT, borderwidth=0, font=("Microsoft YaHei", 10))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self._update_model_summary()
        if self.verbose_var.get():
            self._log("✅ 系统就绪。详细日志已启用，将显示完整的处理过程。")
            self._log("💡 提示：勾选「详细日志」可查看串行处理流程，包括每张图片的LLM调用和结果返回状态。")
        else:
            self._log("就绪。选择多个 Markdown 后执行“批量预览”。")

    def _update_tab_label(self, tab: TabState) -> None:
        if not tab or not hasattr(self, "nb"):
            self.after(0, lambda p=md_path: self._clear_tab_processing(p))
            return
        base_name = tab.md_path.name
        if tab.processing:
            text = f"⏳ {base_name}"
        elif tab.completed:
            text = f"✅ {base_name}"
        else:
            text = base_name
        try:
            self.nb.tab(tab.page, text=text)
        except Exception:
            pass

    def _set_tab_processing(self, tab: TabState, processing: bool) -> None:
        tab.processing = processing
        if processing:
            tab.completed = False
        self._update_tab_label(tab)

    def _mark_tab_completed(self, md_path: Path) -> None:
        tab = self.tabs.get(str(md_path))
        if not tab:
            return
        tab.completed = True
        tab.processing = False
        self._update_tab_label(tab)

    def _clear_tab_processing(self, md_path: Path) -> None:
        tab = self.tabs.get(str(md_path))
        if not tab:
            return
        self._set_tab_processing(tab, False)

    def _log(self, s: str) -> None:
        try:
            self.log_text.insert(tk.END, s + "\n")
            self.log_text.see(tk.END)
            self.update_idletasks()
        except Exception:
            print(s)

    def _log_async(self, s: str) -> None:
        self.after(0, lambda: self._log(s))

    @staticmethod
    def _shorten_text(text: Optional[str], limit: int = 160) -> str:
        if text is None:
            return ""
        s = str(text).strip()
        return s if len(s) <= limit else s[: limit - 1] + "…"

    def _normalize_document_if_needed(self, md_path: Path) -> str:
        try:
            text = read_text(md_path)
        except Exception as exc:
            self._log_async(f"⚠️ 读取失败：{md_path} -> {exc}")
            return ""
        if not self.normalize_html_var.get():
            return text
        try:
            new_text, count = normalize_embedded_html_images(text)
        except Exception as exc:
            self._log_async(f"⚠️ 模板清洗失败：{exc}")
            return text
        if count > 0:
            try:
                write_text_utf8(md_path, new_text)
                self._log_async(f"🔧 已规范 {count} 个嵌套 HTML 图片 -> Markdown。")
            except Exception as exc:
                self._log_async(f"⚠️ 写回规范化结果失败：{exc}")
                return text
            return new_text
        return text

    def _update_model_summary(self) -> None:
        base = (self.base_url_var.get().strip() if hasattr(self, "base_url_var") else "") or "未设置"
        model = (self.model_var.get().strip() if hasattr(self, "model_var") else "") or "未设置"
        base_disp = base if len(base) <= 48 else base[:45] + "…"
        key_status = "已配置" if hasattr(self, "api_key_var") and self.api_key_var.get().strip() else "未配置"
        if hasattr(self, "model_summary_var"):
            self.model_summary_var.set(f"当前模型：{model} | Base URL：{base_disp} | API Key：{key_status}")

    def _open_api_config_dialog(self) -> None:
        dlg = tk.Toplevel(self)
        dlg.title("API / 模型配置")
        dlg.transient(self)
        dlg.grab_set()
        wrapper = ttk.Frame(dlg, padding=20)
        wrapper.pack(fill=tk.BOTH, expand=True)

        # 主命名（图意生成）模型
        ttk.Label(wrapper, text="Base URL:").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(wrapper, textvariable=self.base_url_var, width=44).grid(row=0, column=1, sticky="w", pady=6)

        ttk.Label(wrapper, text="API Key:").grid(row=1, column=0, sticky="w", pady=6)
        api_entry = ttk.Entry(wrapper, textvariable=self.api_key_var, width=44, show="*")
        api_entry.grid(row=1, column=1, sticky="w", pady=6)
        show_var = tk.BooleanVar(value=False)

        def toggle_api_visibility() -> None:
            api_entry.configure(show="" if show_var.get() else "*")

        ttk.Checkbutton(wrapper, text="显示 API Key", variable=show_var, command=toggle_api_visibility).grid(row=2, column=1, sticky="w")

        ttk.Label(wrapper, text="模型:").grid(row=3, column=0, sticky="w", pady=6)
        ttk.Entry(wrapper, textvariable=self.model_var, width=44).grid(row=3, column=1, sticky="w", pady=6)

        ttk.Label(wrapper, text="Timeout:").grid(row=4, column=0, sticky="w", pady=6)
        ttk.Spinbox(wrapper, from_=10, to=300, textvariable=self.timeout_var, width=10).grid(row=4, column=1, sticky="w", pady=6)

        ttk.Label(wrapper, text="Max Retries:").grid(row=5, column=0, sticky="w", pady=6)
        ttk.Spinbox(wrapper, from_=0, to=10, textvariable=self.retries_var, width=10).grid(row=5, column=1, sticky="w", pady=6)

        ttk.Label(wrapper, text="Rate Limit(s):").grid(row=6, column=0, sticky="w", pady=6)
        ttk.Entry(wrapper, textvariable=self.rate_limit_var, width=12).grid(row=6, column=1, sticky="w", pady=6)

        # 分隔线
        ttk.Separator(wrapper, orient="horizontal").grid(row=7, column=0, columnspan=2, sticky="we", pady=(12, 10))

        # 翻译 API
        trans_frame = ttk.LabelFrame(wrapper, text="翻译 API/模型与提示词")
        trans_frame.grid(row=8, column=0, columnspan=2, sticky="we", pady=(0, 8))
        trans_frame.columnconfigure(1, weight=1)

        ttk.Label(trans_frame, text="翻译 Base URL:").grid(row=0, column=0, sticky="w", pady=4, padx=(8, 6))
        ttk.Entry(trans_frame, textvariable=self.trans_base_url_var, width=48).grid(row=0, column=1, sticky="we", pady=4)
        ttk.Label(trans_frame, text="翻译 API Key:").grid(row=1, column=0, sticky="w", pady=4, padx=(8, 6))
        ttk.Entry(trans_frame, textvariable=self.trans_api_key_var, width=48, show="*").grid(row=1, column=1, sticky="we", pady=4)
        ttk.Label(trans_frame, text="翻译模型:").grid(row=2, column=0, sticky="w", pady=4, padx=(8, 6))
        ttk.Entry(trans_frame, textvariable=self.trans_model_var, width=48).grid(row=2, column=1, sticky="we", pady=4)
        ttk.Label(trans_frame, text="翻译提示词:").grid(row=3, column=0, sticky="nw", pady=4, padx=(8, 6))
        ttk.Entry(trans_frame, textvariable=self.trans_prompt_var, width=68).grid(row=3, column=1, sticky="we", pady=4)

        # 归纳 API
        sum_frame = ttk.LabelFrame(wrapper, text="归纳 API/模型与提示词")
        sum_frame.grid(row=9, column=0, columnspan=2, sticky="we", pady=(0, 8))
        sum_frame.columnconfigure(1, weight=1)

        ttk.Label(sum_frame, text="归纳 Base URL:").grid(row=0, column=0, sticky="w", pady=4, padx=(8, 6))
        ttk.Entry(sum_frame, textvariable=self.sum_base_url_var, width=48).grid(row=0, column=1, sticky="we", pady=4)
        ttk.Label(sum_frame, text="归纳 API Key:").grid(row=1, column=0, sticky="w", pady=4, padx=(8, 6))
        ttk.Entry(sum_frame, textvariable=self.sum_api_key_var, width=48, show="*").grid(row=1, column=1, sticky="we", pady=4)
        ttk.Label(sum_frame, text="归纳模型:").grid(row=2, column=0, sticky="w", pady=4, padx=(8, 6))
        ttk.Entry(sum_frame, textvariable=self.sum_model_var, width=48).grid(row=2, column=1, sticky="we", pady=4)
        ttk.Label(sum_frame, text="归纳提示词:").grid(row=3, column=0, sticky="nw", pady=4, padx=(8, 6))
        ttk.Entry(sum_frame, textvariable=self.sum_prompt_var, width=68).grid(row=3, column=1, sticky="we", pady=4)

        # 操作按钮
        btns = ttk.Frame(wrapper)
        btns.grid(row=10, column=0, columnspan=2, sticky="e", pady=(18, 0))

        def on_save() -> None:
            self._on_profile_save()
            self._update_model_summary()

        def on_delete() -> None:
            self._on_profile_delete()
            self._update_model_summary()

        def on_close() -> None:
            self._update_model_summary()
            dlg.destroy()

        ttk.Button(btns, text="保存/更新配置", style="Accent.TButton", command=on_save).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="删除配置", command=on_delete).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="关闭", command=on_close).pack(side=tk.LEFT, padx=4)

        dlg.protocol("WM_DELETE_WINDOW", on_close)
        dlg.resizable(False, False)
        dlg.wait_window()

    # ------------------------------------------------------------------ #
    # 配置档
    # ------------------------------------------------------------------ #
    def _profiles_path(self) -> Path:
        return PROFILES_PATH

    def _load_profiles(self) -> None:
        try:
            p = self._profiles_path()
            if p.exists():
                self.profiles = json.load(p.open("r", encoding="utf-8"))
            else:
                self.profiles = {}
        except Exception:
            self.profiles = {}
        names = sorted(self.profiles.keys())
        self.profile_combo.configure(values=names)
        if names and not self.profile_name_var.get():
            self.profile_name_var.set(names[0])
        self._update_model_summary()

    def _save_profiles(self) -> None:
        try:
            p = self._profiles_path()
            p.parent.mkdir(parents=True, exist_ok=True)
            json.dump(self.profiles, p.open("w", encoding="utf-8"), ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("错误", f"保存配置档失败：{e}")

    def _collect_current_settings(self) -> Dict:
        return {
            "strategy": self.strategy_var.get().strip(),
            "base_url": self.base_url_var.get().strip(),
            "api_key": self.api_key_var.get().strip(),
            "model": self.model_var.get().strip(),
            "timeout": int(self.timeout_var.get()),
            "max_retries": int(self.retries_var.get()),
            "rate_limit": float(self.rate_limit_var.get()),
            "template": self.template_var.get().strip(),
            "seq_width": int(self.seq_width_var.get()),
            "max_name_len": int(self.max_len_var.get()),
            "attach_dir_name": self.attach_var.get().strip(),
            "verbose": bool(self.verbose_var.get()),
            "backup": bool(self.backup_var.get()),
            "vision": bool(self.vision_var.get()),
            "batch_size": int(self.batch_size_var.get()),
            "normalize_html": bool(self.normalize_html_var.get()),

            # 翻译配置
            "trans_base_url": self.trans_base_url_var.get().strip(),
            "trans_api_key": self.trans_api_key_var.get().strip(),
            "trans_model": self.trans_model_var.get().strip(),
            "trans_prompt": self.trans_prompt_var.get().strip(),

            # 归纳配置
            "sum_base_url": self.sum_base_url_var.get().strip(),
            "sum_api_key": self.sum_api_key_var.get().strip(),
            "sum_model": self.sum_model_var.get().strip(),
            "sum_prompt": self.sum_prompt_var.get().strip(),
        }

    def _apply_profile(self, data: Dict) -> None:
        try:
            self.strategy_var.set(data.get("strategy", self.strategy_var.get()))
            self.base_url_var.set(data.get("base_url", self.base_url_var.get()))
            self.api_key_var.set(data.get("api_key", self.api_key_var.get()))
            self.model_var.set(data.get("model", self.model_var.get()))
            self.timeout_var.set(int(data.get("timeout", self.timeout_var.get())))
            self.retries_var.set(int(data.get("max_retries", self.retries_var.get())))
            self.rate_limit_var.set(float(data.get("rate_limit", self.rate_limit_var.get())))
            self.template_var.set(data.get("template", self.template_var.get()))
            self.seq_width_var.set(int(data.get("seq_width", self.seq_width_var.get())))
            self.max_len_var.set(int(data.get("max_name_len", self.max_len_var.get())))
            self.attach_var.set(data.get("attach_dir_name", self.attach_var.get()) or DEFAULT_ATTACH_DIR)
            self.verbose_var.set(bool(data.get("verbose", self.verbose_var.get())))
            self.backup_var.set(bool(data.get("backup", self.backup_var.get())))
            self.vision_var.set(bool(data.get("vision", self.vision_var.get())))
            self.batch_size_var.set(int(data.get("batch_size", self.batch_size_var.get())))
            self.normalize_html_var.set(bool(data.get("normalize_html", self.normalize_html_var.get())))

            # 翻译/归纳配置
            self.trans_base_url_var.set(data.get("trans_base_url", self.trans_base_url_var.get()))
            self.trans_api_key_var.set(data.get("trans_api_key", self.trans_api_key_var.get()))
            self.trans_model_var.set(data.get("trans_model", self.trans_model_var.get()))
            self.trans_prompt_var.set(data.get("trans_prompt", self.trans_prompt_var.get()))
            self.sum_base_url_var.set(data.get("sum_base_url", self.sum_base_url_var.get()))
            self.sum_api_key_var.set(data.get("sum_api_key", self.sum_api_key_var.get()))
            self.sum_model_var.set(data.get("sum_model", self.sum_model_var.get()))
            self.sum_prompt_var.set(data.get("sum_prompt", self.sum_prompt_var.get()))
        except Exception as e:
            messagebox.showerror("错误", f"载入配置失败：{e}")
        self._update_model_summary()

    def _on_profile_save(self) -> None:
        name = (self.profile_name_var.get() or "").strip()
        if not name:
            messagebox.showinfo("提示", "请输入配置档名称后再保存。")
            return
        self.profiles[name] = self._collect_current_settings()
        self._save_profiles()
        names = sorted(self.profiles.keys())
        self.profile_combo.configure(values=names)
        self.profile_name_var.set(name)
        messagebox.showinfo("提示", f"已保存/更新配置档：{name}")
        self._update_model_summary()

    def _on_profile_load(self) -> None:
        name = (self.profile_name_var.get() or "").strip()
        if not name or name not in self.profiles:
            messagebox.showinfo("提示", "未找到该配置档，请先保存或选择已有配置名。")
            return
        self._apply_profile(self.profiles[name])
        messagebox.showinfo("提示", f"已载入配置档：{name}")
        self._update_model_summary()

    def _on_profile_delete(self) -> None:
        name = (self.profile_name_var.get() or "").strip()
        if not name or name not in self.profiles:
            messagebox.showinfo("提示", "未找到该配置档。")
            return
        try:
            del self.profiles[name]
            self._save_profiles()
            names = sorted(self.profiles.keys())
            self.profile_combo.configure(values=names)
            self.profile_name_var.set(names[0] if names else "")
            messagebox.showinfo("提示", f"已删除配置档：{name}")
            self._update_model_summary()
        except Exception as e:
            messagebox.showerror("错误", f"删除失败：{e}")

    # ------------------------------------------------------------------ #
    # 文件列表操作
    # ------------------------------------------------------------------ #
    def _on_add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择 Markdown 文件（可多选）",
            filetypes=[("Markdown", "*.md"), ("所有文件", "*.*")]
        )
        if not paths:
            return
        added = 0
        for p in paths:
            path = Path(p).expanduser()
            if path.exists() and path.suffix.lower() == ".md" and path not in self.files:
                self.files.append(path)
                self.files_listbox.insert(tk.END, str(path))
                added += 1
        self._log(f"已添加 {added} 个文件。当前队列：{len(self.files)}")

    def _on_remove_selected(self) -> None:
        sel = list(self.files_listbox.curselection())[::-1]
        for idx in sel:
            try:
                path_str = self.files_listbox.get(idx)
                self.files_listbox.delete(idx)
                self.files = [p for p in self.files if str(p) != path_str]
            except Exception:
                pass
        self._log(f"已移除选中项。当前队列：{len(self.files)}")

    def _on_clear_list(self) -> None:
        self.files.clear()
        self.files_listbox.delete(0, tk.END)
        self._log("已清空文件列表。")

    def _gather_config(self, mode: str) -> Config:
        base = normalize_base_url(self.base_url_var.get().strip())
        return Config(
            mode=mode,
            strategy=self.strategy_var.get().strip(),
            base_url=base,
            api_key=self.api_key_var.get().strip(),
            model=self.model_var.get().strip(),
            timeout=int(self.timeout_var.get()),
            max_retries=int(self.retries_var.get()),
            rate_limit=float(self.rate_limit_var.get()),
            attach_dir_name=self.attach_var.get().strip() or DEFAULT_ATTACH_DIR,
            download=False,
            name_template=self.template_var.get().strip() or DEFAULT_NAME_TEMPLATE,
            seq_width=int(self.seq_width_var.get()),
            max_name_len=int(self.max_len_var.get()),
            save_report=None,
            verbose=bool(self.verbose_var.get()),
            backup=bool(self.backup_var.get()),
            vision=bool(self.vision_var.get()),
            chunk_size=max(1, int(self.batch_size_var.get())),
        )

    # ------------------------------------------------------------------ #
    # 预览流程（后台线程 -> 主线程更新）
    # ------------------------------------------------------------------ #
    def _on_batch_preview(self) -> None:
        if not self.files:
            messagebox.showinfo("提示", "请先添加 Markdown 文件。")
            return
        if self.strategy_var.get().strip() != "seq":
            if not self.base_url_var.get().strip() or not self.api_key_var.get().strip():
                messagebox.showerror("错误", "未提供 Base URL 与 API Key。请在 AI 参数中填写后重试，或将策略切换为 seq。")
                return
        self.stop_flag = False
        threading.Thread(target=self._batch_preview_worker, daemon=True).start()

    def _on_stop(self) -> None:
        self.stop_flag = True
        self._log("⏹️ 已请求停止（将在当前任务结束后生效）。")

    def _batch_preview_worker(self) -> None:
        cfg = self._gather_config(mode="dry-run")
        total_files = len(self.files)

        if self.verbose_var.get():
            self._log_async(f"🔄 开始批量预览串行处理，共 {total_files} 个文件")

        for i, md in enumerate(self.files, 1):
            if self.stop_flag:
                self._log_async(f"⏹️ 用户停止处理（进度 {i-1}/{total_files}）")
                break

            if self.verbose_var.get():
                self._log_async(f"📁 处理文件中... [{i}/{total_files}] {md.name}")
            self._process_file_in_worker(md, cfg)

        if self.verbose_var.get():
            self._log_async("✅ 批量预览完成。" if not self.stop_flag else "⚠️ 批量预览被用户中断。")

    def _process_file_in_worker(self, md_path: Path, cfg: Config) -> None:
        if not md_path.exists():
            self._log_async(f"❌ 文件不存在：{md_path}")
            return

        def batch_confirm(batch_items: List[Dict]) -> bool:
            if self.stop_flag:
                return False
            if self.verbose_var.get():
                names: List[str] = []
                for item in batch_items:
                    display = (item.get("display_name") or item.get("src") or "").strip()
                    if display:
                        names.append(display)
                    if len(names) >= 3:
                        break
                summary = "，".join(names)
                if len(batch_items) > 3 and summary:
                    summary = f"{summary} 等"
                description = summary or "自动批次"
                self._log_async(f"🚀 自动发送批次（{len(batch_items)} 张）：{description}")
            return True

        cfg.batch_confirm_cb = batch_confirm

        text_data = self._normalize_document_if_needed(md_path)
        if text_data == "":
            return

        if self.pre_localize_var.get():
            try:
                stats = collect_images_to_attachment(
                    md_path,
                    self.attach_var.get().strip() or DEFAULT_ATTACH_DIR,
                    int(self.timeout_var.get()),
                    backup=bool(self.backup_var.get()),
                )
                summary = (
                    f"🗂 图片收集完成：共{stats.get('total', 0)}，"
                    f"下载{stats.get('downloaded', 0)}，搬运{stats.get('moved', 0)}，"
                    f"复制{stats.get('copied', 0)}，已在附件中{stats.get('skipped', 0)}，"
                    f"缺失{stats.get('missing', 0)}"
                )
                self._log_async(summary)
                errors = stats.get("errors") or []
                if errors:
                    for err in errors:
                        self._log_async(f"⚠️ 收集异常：{err}")
            except Exception as exc:
                self._log_async(f"⚠️ 图片收集失败：{exc}")

        try:
            text_data = read_text(md_path)
        except Exception as e:
            self._log_async(f"⚠️ 读取失败：{md_path} -> {e}")
            return

        text_data = self._normalize_document_if_needed(md_path)
        if text_data == "":
            return

        if self.verbose_var.get():
            # 统计图片数量
            try:
                refs = collect_images(text_data)
                img_count = len(refs)
                self._log_async(f"📄 开始分析：{md_path.name}（发现 {img_count} 张图片）")
            except Exception:
                self._log_async(f"▶️ 预览：{md_path}")
        else:
            self._log_async(f"▶️ 预览：{md_path}")

        doc_title = extract_doc_title(text_data, md_path)
        self.after(0, lambda t=doc_title: self._prepare_processing_tab(md_path, t))

        def on_batch_result(payload: Dict) -> None:
            item = payload.get("item") or {}
            idx = payload.get("index")
            safe_item = copy.deepcopy(item)
            self.after(0, lambda it=safe_item, index=idx: self._append_processing_item(md_path, doc_title, it, index))

        def on_llm_event(event: Dict) -> None:
            safe_event = copy.deepcopy(event)
            self.after(0, lambda e=safe_event: self._log_llm_event(md_path, e))

        cfg.batch_result_cb = on_batch_result
        cfg.llm_event_cb = on_llm_event

        try:
            results = process_document(md_path, cfg)
        except Exception as e:
            self._log_async(f"❌ 预览失败：{md_path} -> {e}")
            return

        self.after(0, lambda r=results, t=text_data: self._apply_preview_results(md_path, t, r))

    def _prepare_processing_tab(self, md_path: Path, title: str) -> None:
        key = str(md_path)
        tab = self.tabs.get(key)
        if tab is None:
            tab = self._create_tab(md_path)
        self._set_tab_processing(tab, True)
        tab.title = title
        if not isinstance(tab.results, dict):
            tab.results = {}
        tab.results["title"] = title
        tab.results["items"] = []
        self.nb.select(tab.page)
        self._populate_items(tab)

    def _append_processing_item(self, md_path: Path, title: str, item: Dict, index: Optional[int]) -> None:
        key = str(md_path)
        tab = self.tabs.get(key)
        if tab is None:
            self._prepare_processing_tab(md_path, title)
            tab = self.tabs.get(key)
        if tab is None:
            return
        self._set_tab_processing(tab, True)
        tab.title = title
        if not isinstance(tab.results, dict):
            tab.results = {}
        items = tab.results.setdefault("items", [])
        tab.results["title"] = title
        target_idx = index if index is not None else item.get("index")
        replaced = False
        if target_idx is not None:
            for pos, existing in enumerate(items):
                if existing.get("index") == target_idx:
                    items[pos] = item
                    replaced = True
                    break
        if not replaced:
            items.append(item)
        self._populate_items(tab)
        if self.verbose_var.get():
            normalized = item.get("normalized_title") or "图意"
            target_disp = target_idx if target_idx is not None else "?"
            self._log_async(f"📥 已接收模型结果：{md_path.name} #{target_disp} -> {normalized}")

    def _move_file_safe(self, src: Path, dest: Path) -> bool:
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

    def _log_llm_event(self, md_path: Path, event: Dict) -> None:
        evt = event.get("event")
        indexes = event.get("indexes") or []
        idx_text = ", ".join(str(i) for i in indexes) if indexes else "-"
        mode = event.get("mode", "")
        prefix = f"[{md_path.name}]({mode}) #{idx_text}"
        if evt == "request":
            parts = []
            for msg in event.get("messages", []):
                role = msg.get("role", "")
                if "text" in msg:
                    parts.append(f"{role}:{self._shorten_text(msg.get('text', ''), 120)}")
                elif "parts" in msg:
                    sub = []
                    for part in msg["parts"]:
                        p_type = part.get("type", "")
                        if p_type == "text":
                            sub.append(f"text:{self._shorten_text(part.get('text', ''), 80)}")
                        elif p_type == "image_url":
                            sub.append(f"image:{self._shorten_text(part.get('url', ''), 80)}")
                        elif p_type:
                            sub.append(p_type)
                    parts.append(f"{role}:[{' | '.join(sub)}]")
                else:
                    parts.append(role)
            detail = " / ".join(parts)
            self._log_async(f"➡️ LLM 请求 {prefix} {detail}")
        elif evt == "response":
            status = event.get("status", "unknown")
            snippet = event.get("snippet") or event.get("error") or ""
            self._log_async(f"⬅️ LLM 响应 {prefix} {status} {self._shorten_text(snippet, 160)}")
        else:
            note = event.get("note") or ""
            self._log_async(f"ℹ️ LLM 事件 {prefix} {evt} {note}")

    def _apply_preview_results(self, md_path: Path, text_data: str, results: Dict) -> None:
        key = str(md_path)
        tab = self.tabs.get(key)
        if tab is None:
            tab = self._create_tab(md_path)
        self._set_tab_processing(tab, False)
        self.nb.select(tab.page)
        tab.title = results.get("title", extract_doc_title(text_data, md_path))
        tab.results = results
        self._populate_items(tab)

        count = len(results.get("items", [])) if isinstance(results, dict) else 0

        if self.verbose_var.get():
            # 显示详细的处理完成信息
            strategy = results.get("strategy", "未知") if isinstance(results, dict) else "未知"
            processed_count = len([item for item in results.get("items", []) if item.get("normalized_title")]) if isinstance(results, dict) else 0
            self._log(f"✅ 文件处理完成：{md_path.name}")
            self._log(f"   • 策略：{strategy} | 图片：{count}张 | 已命名：{processed_count}张")
        else:
            self._log(f"✅ 预览完成：{md_path}（共 {count} 张）")

        if isinstance(results, dict) and results.get("cancelled"):
            self._log("⚠️ 已取消后续批次，可在复核当前结果后重新执行预览。")

    def _create_tab(self, md_path: Path) -> TabState:
        page = ttk.Frame(self.nb)
        self.nb.add(page, text=md_path.name)

        bar = ttk.Frame(page)
        bar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(8, 4))

        btn_refresh = ttk.Button(bar, text="刷新预览", command=lambda p=md_path: self._refresh_tab(p))
        btn_refresh.pack(side=tk.LEFT, padx=4)

        btn_apply_all = ttk.Button(bar, text="应用本文件所有改名/回链", command=lambda p=md_path: self._apply_all_in_tab(p))
        btn_apply_all.pack(side=tk.LEFT, padx=4)

        btn_close = ttk.Button(bar, text="关闭标签页", command=lambda p=md_path: self._close_tab(p))
        btn_close.pack(side=tk.RIGHT, padx=4)

        canvas = tk.Canvas(page, highlightthickness=0)
        vsb = ttk.Scrollbar(page, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=(0, 8))
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=(0, 8))

        inner = ttk.Frame(canvas)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_configure(event=None) -> None:  # pragma: no cover - UI callback
            canvas.configure(scrollregion=canvas.bbox("all"))
            try:
                canvas.itemconfig(inner_id, width=canvas.winfo_width() - 2)
            except Exception:
                pass

        inner.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", _on_configure)

        tab = TabState(
            md_path=md_path,
            title="",
            results={},
            page=page,
            canvas=canvas,
            inner_frame=inner,
            scrollbar=vsb,
            item_uis=[],
            btn_refresh=btn_refresh,
            btn_apply_all=btn_apply_all,
            btn_close=btn_close,
        )
        self.tabs[str(md_path)] = tab
        self._update_tab_label(tab)
        return tab

    def _close_tab(self, md_path: Path) -> None:
        key = str(md_path)
        tab = self.tabs.pop(key, None)
        if not tab:
            return
        if tab.recalc_job:
            try:
                self.after_cancel(tab.recalc_job)
            except Exception:
                pass
            tab.recalc_job = None
        try:
            self.nb.forget(tab.page)
        except Exception:
            pass
        try:
            tab.page.destroy()
        except Exception:
            pass

    def _clear_inner(self, tab: TabState) -> None:
        for w in list(tab.inner_frame.children.values()):
            try:
                w.destroy()
            except Exception:
                pass
        tab.item_uis.clear()

    def _populate_items(self, tab: TabState) -> None:
        self._clear_inner(tab)
        items = tab.results.get("items", []) if isinstance(tab.results, dict) else []
        if tab.processing:
            status_text = f"已接收 {len(items)} 张 | 正在处理..."
        else:
            status_text = f"图片数：{len(items)}"

        head = ttk.Label(
            tab.inner_frame,
            text=f"{tab.md_path}\n标题：{tab.title} | {status_text}",
            font=("Microsoft YaHei", 10, "bold"),
        )
        head.pack(fill=tk.X, padx=4, pady=(8, 8))

        if not items:
            placeholder = "正在调用模型，请稍候..." if tab.processing else "未发现图片。"
            ttk.Label(tab.inner_frame, text=placeholder, foreground="#777").pack(fill=tk.X, padx=8, pady=8)
            return

        hdr = ttk.Frame(tab.inner_frame)
        hdr.pack(fill=tk.X, padx=8)
        ttk.Label(hdr, text="#", width=4).grid(row=0, column=0, sticky="w")
        ttk.Label(hdr, text="源（截断显示）", width=48).grid(row=0, column=1, sticky="w")
        ttk.Label(hdr, text="图意（可编辑）", width=36).grid(row=0, column=2, sticky="w")
        ttk.Label(hdr, text="最终文件名", width=36).grid(row=0, column=3, sticky="w")
        ttk.Label(hdr, text="操作", width=14).grid(row=0, column=4, sticky="w")

        for idx, item_data in enumerate(items):
            row = ttk.Frame(tab.inner_frame)
            row.pack(fill=tk.X, padx=8, pady=3)

            index = int(item_data.get("index", idx + 1))
            block_idx = int(item_data.get("block_index", index))
            img_idx = int(item_data.get("image_index", 1))
            src = item_data.get("src", "")
            above = item_data.get("above_text", "")
            below = item_data.get("below_text", "")
            between = item_data.get("between_text", "")
            alt = item_data.get("alt")
            title_attr = item_data.get("title_attr")

            ttk.Label(row, text=str(index), width=4).grid(row=0, column=0, sticky="w")
            src_disp = src if len(src) <= 80 else (src[:77] + "…")
            ttk.Label(row, text=src_disp, width=48).grid(row=0, column=1, sticky="w")

            intent_var = tk.StringVar(value=item_data.get("normalized_title") or "图意")
            ttk.Entry(row, textvariable=intent_var, width=36).grid(row=0, column=2, sticky="w")

            final_var = tk.StringVar(value="")
            ttk.Entry(row, textvariable=final_var, width=36, state="readonly").grid(row=0, column=3, sticky="w")

            ops = ttk.Frame(row)
            ops.grid(row=0, column=4, sticky="w")
            apply_one_btn = ttk.Button(ops, text="仅处理这一张", command=lambda tab=tab, pos=idx: self._on_apply_single(tab, pos))
            apply_one_btn.pack(side=tk.LEFT)

            skip_var = tk.BooleanVar(value=False)
            skip_check = ttk.Checkbutton(ops, text="删除此图", variable=skip_var, command=lambda t=tab, pos=idx: self._on_skip_toggle(t, pos))
            skip_check.pack(side=tk.LEFT, padx=(10, 0))

            item_ui = ItemUI(
                index=index,
                block_index=block_idx,
                image_index=img_idx,
                src=src,
                above_text=above,
                below_text=below,
                between_text=between,
                alt=alt,
                title_attr=title_attr,
                frame=row,
                intent_var=intent_var,
                final_var=final_var,
                apply_one_btn=apply_one_btn,
                skip_var=skip_var,
                skip_check=skip_check,
            )
            tab.item_uis.append(item_ui)

        self._recalc_names(tab)
        for item_ui in tab.item_uis:
            item_ui.intent_var.trace_add("write", lambda *_args, t=tab: self._schedule_recalc(t))
            item_ui.skip_var.trace_add("write", lambda *_args, t=tab: self._schedule_recalc(t))

    def _schedule_recalc(self, tab: TabState) -> None:
        if tab.recalc_job:
            try:
                self.after_cancel(tab.recalc_job)
            except Exception:
                pass
        tab.recalc_job = self.after(80, lambda t=tab: self._recalc_names(t))

    def _on_skip_toggle(self, tab: TabState, item_pos: int) -> None:
        try:
            item = tab.item_uis[item_pos]
        except Exception:
            return
        skip = bool(item.skip_var.get())
        try:
            item.apply_one_btn.configure(state=tk.DISABLED if skip else tk.NORMAL)
        except Exception:
            pass
        self._schedule_recalc(tab)

    def _recalc_names(self, tab: TabState) -> None:
        if tab.recalc_job:
            try:
                self.after_cancel(tab.recalc_job)
            except Exception:
                pass
            tab.recalc_job = None

        tmpl = self.template_var.get().strip() or DEFAULT_NAME_TEMPLATE
        seq_w = int(self.seq_width_var.get())
        max_len = int(self.max_len_var.get())
        counts: Dict[str, int] = {}

        for item in tab.item_uis:
            skip = bool(item.skip_var.get())
            try:
                item.apply_one_btn.configure(state=tk.DISABLED if skip else tk.NORMAL)
            except Exception:
                pass
            if skip:
                item.final_var.set("（将删除）")
                continue

            intent = sanitize_filename(item.intent_var.get() or "图意")
            counts[intent] = counts.get(intent, 0) + 1
            dup_idx = counts[intent]
            final_name = name_with_template(
                tmpl,
                tab.title,
                item.block_index,
                item.image_index,
                intent,
                seq_w,
                max_len,
                global_index=item.index,
                dup_index=dup_idx,
            )
            item.final_var.set(final_name)

    def _recalc_all_tabs(self) -> None:
        for tab in self.tabs.values():
            self._recalc_names(tab)

    def _refresh_tab(self, md_path: Path) -> None:
        cfg = self._gather_config(mode="dry-run")
        self.stop_flag = False
        threading.Thread(target=self._process_file_in_worker, args=(md_path, cfg), daemon=True).start()

    # ------------------------------------------------------------------ #
    # 单图处理（候选生成 / 预览对话框 / 写回）
    # ------------------------------------------------------------------ #
    def _generate_single_candidates(
        self,
        tab: TabState,
        item: ItemUI,
        explicit_refs: List[str],
        alt_text: Optional[str],
        title_attr: Optional[str],
        vision_src: Optional[str],
    ) -> Dict:
        base = normalize_base_url(self.base_url_var.get().strip())
        key = self.api_key_var.get().strip()
        model = self.model_var.get().strip()
        if not base or not key or not model:
            raise ValueError("缺少 Base URL / API Key / Model")
        msgs = build_ai_messages(
            tab.title,
            item.above_text,
            item.below_text,
            item.between_text,
            explicit_refs,
            alt_text,
            title_attr,
            vision_src=vision_src,
            base_url=base,
        )
        out = call_openai_chat(
            base,
            key,
            model,
            msgs,
            timeout=int(self.timeout_var.get()),
            max_retries=int(self.retries_var.get()),
            rate_limit=float(self.rate_limit_var.get()),
            verbose=bool(self.verbose_var.get()),
        )
        if not out:
            raise RuntimeError(get_last_llm_error() or "模型返回为空")
        data = safe_parse_json(out)
        result = validate_ai_result(data)
        if not result:
            raise ValueError("模型返回不可解析")
        return result

    def _build_vision_src_for_item(self, md_path: Path, img_src: str) -> Optional[str]:
        try:
            if core.is_remote_url(img_src):
                return img_src
            local_path = resolve_local_image(md_path.parent, img_src)
            if not local_path or not local_path.exists():
                return None
            data = local_path.read_bytes()
            import base64

            b64 = base64.b64encode(data).decode("ascii")
            mime = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp",
                ".bmp": "image/bmp",
                ".svg": "image/svg+xml",
                ".tif": "image/tiff",
                ".tiff": "image/tiff",
                ".ico": "image/x-icon",
                ".heic": "image/heic",
            }.get(local_path.suffix.lower(), "application/octet-stream")
            return f"data:{mime};base64,{b64}"
        except Exception:
            return None

    def _on_regen_single(self, tab: TabState, item_pos: int) -> None:
        try:
            item = tab.item_uis[item_pos]
        except Exception:
            return
        results_items = tab.results.get("items", []) if isinstance(tab.results, dict) else []
        item_data = results_items[item_pos] if 0 <= item_pos < len(results_items) else {}
        explicit_refs = item_data.get("explicit_refs", []) if isinstance(item_data, dict) else []
        alt_text = item_data.get("alt") if isinstance(item_data, dict) else None
        title_attr = item_data.get("title_attr") if isinstance(item_data, dict) else None
        vision_src = self._build_vision_src_for_item(tab.md_path, item.src) if self.vision_var.get() else None

        def worker() -> None:
            try:
                if self.verbose_var.get():
                    # 显示发送给LLM的内容摘要
                    context_summary = self._get_context_summary(item)
                    self._log_async(f"🤖 发送图片 #{item.index} 到LLM处理...")
                    self._log_async(f"   • 上下文：{context_summary}")
                    if vision_src:
                        self._log_async("   • 包含视觉分析")
                    else:
                        self._log_async("   • 纯文本分析")
                result = self._generate_single_candidates(tab, item, explicit_refs, alt_text, title_attr, vision_src)
            except Exception as exc:  # pragma: no cover - UI callback
                self._log_async(f"⚠️ 重生成失败：#{item.index} -> {exc}")
                return

            def apply_result() -> None:
                candidates = result.get("candidates") or []
                normalized = sanitize_filename(result.get("normalized_title") or "")

                if self.verbose_var.get():
                    # 显示LLM返回结果摘要
                    self._log_async(f"✅ LLM返回结果：#{item.index}")
                    self._log_async(f"   • 命名：{normalized or '图意'}")
                    self._log_async(f"   • 候选数量：{len(candidates)}")

                if normalized:
                    item.intent_var.set(normalized)
                    if 0 <= item_pos < len(results_items):
                        try:
                            results_items[item_pos]["normalized_title"] = normalized
                        except Exception:
                            pass
                if 0 <= item_pos < len(results_items):
                    try:
                        results_items[item_pos]["candidates"] = candidates
                    except Exception:
                        pass
                self._recalc_names(tab)

                if self.verbose_var.get():
                    final_name = item.final_var.get() or "未知"
                    self._log(f"📝 表单已更新：#{item.index} -> {normalized or '图意'} [{final_name}]")
                else:
                    self._log(f"✅ 重生成成功：#{item.index} -> {normalized or '图意'}")

            self.after(0, apply_result)
    
            threading.Thread(target=worker, daemon=True).start()
    
        def _get_context_summary(self, item: ItemUI) -> str:
            """生成上下文内容的简要摘要"""
            contexts = []
            if item.above_text.strip():
                above_chars = len(item.above_text.strip())
                contexts.append(f"上文({above_chars}字符)")
            if item.below_text.strip():
                below_chars = len(item.below_text.strip())
                contexts.append(f"下文({below_chars}字符)")

            return " + ".join(contexts) if contexts else "无上下文"

    def _on_apply_single(self, tab: TabState, item_pos: int) -> None:
        try:
            item = tab.item_uis[item_pos]
        except Exception:
            return
        if item.skip_var.get():
            messagebox.showinfo("提示", "该图片已标记为从文档中删除，如需单独处理请先取消勾选“删除此图”。")
            return
        self._open_single_dialog(tab, item_pos)

    def _open_single_dialog(self, tab: TabState, item_pos: int) -> None:
        try:
            item = tab.item_uis[item_pos]
        except Exception:
            return

        results_items = tab.results.get("items", []) if isinstance(tab.results, dict) else []
        item_data = results_items[item_pos] if 0 <= item_pos < len(results_items) else {}
        explicit_refs = item_data.get("explicit_refs", []) if isinstance(item_data, dict) else []
        alt_text = item_data.get("alt") if isinstance(item_data, dict) else None
        title_attr = item_data.get("title_attr") if isinstance(item_data, dict) else None
        candidates_data = item_data.get("candidates", []) if isinstance(item_data, dict) else []

        dlg = tk.Toplevel(self)
        dlg.title(f"仅处理这一张 - #{item.index}")
        dlg.geometry("1200x800")
        dlg.transient(self)
        dlg.grab_set()

        # 主容器 - 左右布局
        main_container = ttk.Frame(dlg)
        main_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # 左侧 - 图片信息与预览
        left_frame = ttk.Frame(main_container)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        ttk.Label(left_frame, text=f"图片 #{item.index}", font=("Microsoft YaHei", 11, "bold")).pack(anchor="w", pady=(0, 4))
        ttk.Label(left_frame, text=f"来源：{item.src}", wraplength=420, foreground="#555").pack(anchor="w", pady=(0, 2))
        doc_display = (tab.title or "").strip() or tab.md_path.name
        ttk.Label(left_frame, text=f"文档：{doc_display}", wraplength=420, foreground="#666").pack(anchor="w", pady=(0, 6))

        preview_frame = ttk.LabelFrame(left_frame, text="图片预览")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        img_label = ttk.Label(preview_frame, text="正在加载图片预览...", anchor="center")
        img_label.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 4))

        def _fetch_image_bytes(src: str) -> Tuple[Optional[bytes], str]:
            if is_remote_url(src):
                if requests is None:
                    return None, "预览需要 requests 库（pip install requests）"
                try:
                    resp = requests.get(src, timeout=12)
                    resp.raise_for_status()
                    return resp.content, ""
                except Exception as exc:
                    return None, f"远程图片加载失败：{exc}"
            try:
                local_path = resolve_local_image(tab.md_path.parent, src)
            except Exception as exc:
                return None, f"路径解析失败：{exc}"
            if not local_path:
                local_path = (tab.md_path.parent / src).resolve()
            if not local_path.exists():
                return None, f"文件不存在：{local_path}"
            try:
                return local_path.read_bytes(), ""
            except Exception as exc:
                return None, f"读取失败：{exc}"

        def _load_preview() -> None:
            data, error = _fetch_image_bytes(item.src)
            if data:
                img_label.after(0, lambda d=data: self._apply_preview_on_label(d, img_label))
            else:
                message = error or "无法加载图片预览"
                img_label.after(0, lambda msg=message: img_label.configure(text=msg))

        threading.Thread(target=_load_preview, daemon=True).start()

        neighbors_section = ttk.LabelFrame(preview_frame, text="邻近图片")
        neighbors_section.pack(fill=tk.X, expand=False, padx=8, pady=(0, 8))

        neighbor_items: List[Tuple[str, Optional[ItemUI]]] = [
            ("上一张", tab.item_uis[item_pos - 1] if item_pos > 0 else None),
            ("下一张", tab.item_uis[item_pos + 1] if item_pos + 1 < len(tab.item_uis) else None),
        ]

        for col, (title_text, neighbor_item) in enumerate(neighbor_items):
            neighbors_section.columnconfigure(col, weight=1)
            cell = ttk.Frame(neighbors_section, borderwidth=1, relief=tk.GROOVE)
            cell.grid(row=0, column=col, sticky="nsew", padx=4, pady=4)

            header_row = ttk.Frame(cell)
            header_row.pack(fill=tk.X, padx=6, pady=(4, 2))
            ttk.Label(header_row, text=title_text, width=6).pack(side=tk.LEFT)

            if neighbor_item:
                entry_var = neighbor_item.intent_var
            else:
                entry_var = tk.StringVar(value="无")

            entry = ttk.Entry(header_row, textvariable=entry_var, width=28)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
            entry.configure(state="readonly")
            entry._stringvar = entry_var  # type: ignore[attr-defined]

            thumb_label = ttk.Label(cell, text="加载缩略图", anchor="center")
            thumb_label.pack(fill=tk.BOTH, expand=True, padx=6, pady=(4, 6))

            if neighbor_item:
                thumb_label.configure(text="正在加载缩略图...")

                def _load_neighbor(target_item: ItemUI = neighbor_item, target_label: ttk.Label = thumb_label) -> None:
                    def worker() -> None:
                        data, error = _fetch_image_bytes(target_item.src)
                        if data:
                            target_label.after(
                                0,
                                lambda d=data, lbl=target_label: self._apply_preview_on_label(
                                    d, lbl, max_size=(220, 140)
                                ),
                            )
                        else:
                            message = error or "无法加载缩略图"
                            target_label.after(0, lambda msg=message, lbl=target_label: lbl.configure(text=msg))

                    threading.Thread(target=worker, daemon=True).start()

                _load_neighbor()
            else:
                thumb_label.configure(text="暂无图片")


        # 右侧 - 上下文与候选
        right_wrapper = ttk.Frame(main_container)
        right_wrapper.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))

        right_canvas = tk.Canvas(right_wrapper, highlightthickness=0)
        right_scroll = ttk.Scrollbar(right_wrapper, orient="vertical", command=right_canvas.yview)
        right_canvas.configure(yscrollcommand=right_scroll.set)
        right_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_frame = ttk.Frame(right_canvas)
        right_window = right_canvas.create_window((0, 0), window=right_frame, anchor="nw")

        def _on_right_configure(event=None) -> None:
            right_canvas.configure(scrollregion=right_canvas.bbox("all"))
            try:
                right_canvas.itemconfig(right_window, width=right_canvas.winfo_width())
            except Exception:
                pass

        right_frame.bind("<Configure>", _on_right_configure)
        right_canvas.bind("<Configure>", _on_right_configure)

        context_frame = ttk.LabelFrame(right_frame, text="上下文")
        context_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # 上下文工具条（翻译 / 归纳）
        tools_row = ttk.Frame(context_frame)
        tools_row.pack(fill=tk.X, padx=6, pady=(6, 0))
        ttk.Label(tools_row, text="操作：", foreground="#555").pack(side=tk.LEFT, padx=(0, 6))

        def _open_text_proc_dialog(kind: str) -> None:
            dlg2 = tk.Toplevel(self)
            dlg2.title("翻译结果" if kind == "translate" else "归纳结果")
            dlg2.geometry("720x520")
            dlg2.transient(self)
            dlg2.grab_set()

            out_box = scrolledtext.ScrolledText(dlg2, wrap=tk.WORD, font=CONTEXT_FONT)
            out_box.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
            out_box.insert("1.0", "⏳ 正在处理，请稍候...")
            out_box.configure(state=tk.DISABLED)

            above = (item.above_text or "").strip()
            below = (item.below_text or "").strip()
            parts: List[str] = []
            if above:
                parts.append(f"【上文】\n{above}")
            if below:
                parts.append(f"【下文】\n{below}")
            user_text = "\n\n".join(parts) if parts else "（无上下文内容）"

            def worker() -> None:
                try:
                    if kind == "translate":
                        base = (self.trans_base_url_var.get().strip() or self.base_url_var.get().strip())
                        key = (self.trans_api_key_var.get().strip() or self.api_key_var.get().strip())
                        model = (self.trans_model_var.get().strip() or self.model_var.get().strip())
                        sys_prompt = self.trans_prompt_var.get().strip()
                    else:
                        base = (self.sum_base_url_var.get().strip() or self.base_url_var.get().strip())
                        key = (self.sum_api_key_var.get().strip() or self.api_key_var.get().strip())
                        model = (self.sum_model_var.get().strip() or self.model_var.get().strip())
                        sys_prompt = self.sum_prompt_var.get().strip()

                    result = self._run_simple_chat(base, key, model, sys_prompt, user_text)
                    if not isinstance(result, str):
                        result = str(result)

                    def apply_ok() -> None:
                        out_box.configure(state=tk.NORMAL)
                        out_box.delete("1.0", tk.END)
                        out_box.insert("1.0", result or "（空）")
                        out_box.configure(state=tk.DISABLED)

                    self.after(0, apply_ok)
                except Exception as exc:
                    def apply_fail() -> None:
                        out_box.configure(state=tk.NORMAL)
                        out_box.delete("1.0", tk.END)
                        out_box.insert("1.0", f"⚠️ 处理失败：{exc}")
                        out_box.configure(state=tk.DISABLED)
                    self.after(0, apply_fail)

            threading.Thread(target=worker, daemon=True).start()

        ttk.Button(tools_row, text="翻译", command=lambda: _open_text_proc_dialog("translate")).pack(side=tk.LEFT, padx=4)
        ttk.Button(tools_row, text="归纳", command=lambda: _open_text_proc_dialog("summarize")).pack(side=tk.LEFT, padx=4)

        contexts = [
            ("上文", item.above_text),
            ("下文", item.below_text),
        ]

        for title, content in contexts:
            sub = ttk.LabelFrame(context_frame, text=title)
            sub.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
            sub.columnconfigure(0, weight=1)
            sub.rowconfigure(0, weight=1)
            text_content = (content or "").strip()
            char_count = len(text_content)
            if char_count == 0:
                height = CONTEXT_EMPTY_LINES
            else:
                est_lines = (char_count + CONTEXT_CHAR_PER_LINE - 1) // CONTEXT_CHAR_PER_LINE
                height = max(CONTEXT_MIN_LINES, min(CONTEXT_MAX_LINES, est_lines + 1))
            viewer = scrolledtext.ScrolledText(sub, height=height, wrap=tk.WORD, font=CONTEXT_FONT)
            viewer.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
            self._render_markdown(viewer, content or "")

        # 候选框架
        cand_frame = ttk.LabelFrame(right_frame, text="图意候选")
        cand_frame.pack(fill=tk.BOTH, expand=False)
        cand_container = ttk.Frame(cand_frame)
        cand_container.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        selected_var = tk.StringVar(value=item.intent_var.get())
        custom_var = tk.StringVar(value=item.intent_var.get())
        status_var = tk.StringVar(value="")

        def render_candidates(candidates: List[Dict], preferred: Optional[str] = None) -> None:
            for child in cand_container.winfo_children():
                child.destroy()
            sanitized: List[str] = []
            label_map = {"above": "上文理解", "below": "下文理解", "intent": "识图结果"}
            for cand in candidates:
                if not isinstance(cand, dict):
                    continue
                title_text = sanitize_filename(cand.get("title") or "")
                if not title_text:
                    continue
                sanitized.append(title_text)
                info: List[str] = []
                strategy = (cand.get("strategy") or "").lower()
                label = label_map.get(strategy)
                if label:
                    info.append(label)
                info.append(title_text)
                confidence = cand.get("confidence")
                if confidence not in (None, ""):
                    info.append(f"置信度:{confidence}")
                ttk.Radiobutton(
                    cand_container,
                    text=" | ".join(info),
                    value=title_text,
                    variable=selected_var,
                ).pack(anchor="w", pady=2)
                reason = cand.get("reason")
                if reason:
                    ttk.Label(cand_container, text=f"依据：{reason}", wraplength=580, foreground="#666").pack(anchor="w", padx=24, pady=(0, 4))
            ttk.Radiobutton(cand_container, text="自定义：", value="__custom__", variable=selected_var).pack(anchor="w", pady=(6, 2))
            entry = ttk.Entry(cand_container, textvariable=custom_var, width=60)
            entry.pack(anchor="w", padx=24, pady=(0, 6))
            entry.bind("<FocusIn>", lambda _evt: selected_var.set("__custom__"))
            if preferred and preferred in sanitized:
                selected_var.set(preferred)
            elif sanitized:
                selected_var.set(sanitized[0])
            else:
                selected_var.set("__custom__")
                entry.focus_set()

        preferred_strategy = (self.strategy_var.get().strip() or "above").lower()
        ordered_candidates: List[Dict] = []
        preferred_title: Optional[str] = None
        if isinstance(candidates_data, list):
            strategy_pick: Dict[str, Dict] = {}
            for cand in candidates_data:
                if not isinstance(cand, dict):
                    continue
                strat = (cand.get("strategy") or "").lower()
                if strat in ("above", "below", "intent") and strat not in strategy_pick:
                    strategy_pick[strat] = cand
            for strat in ("above", "below", "intent"):
                cand = strategy_pick.get(strat)
                if cand:
                    ordered_candidates.append(cand)
            for cand in candidates_data:
                if cand not in ordered_candidates and isinstance(cand, dict):
                    ordered_candidates.append(cand)
            if preferred_strategy in strategy_pick:
                preferred_title = sanitize_filename(strategy_pick[preferred_strategy].get("title") or "")
        else:
            ordered_candidates = []
        if not ordered_candidates:
            ordered_candidates = candidates_data if isinstance(candidates_data, list) else []
        current_title = sanitize_filename(item.intent_var.get() or "")
        render_candidates(ordered_candidates, preferred_title or current_title or None)
        ttk.Label(cand_frame, textvariable=status_var, foreground="#666").pack(anchor="w", padx=6, pady=(0, 4))

        actions_row = ttk.Frame(cand_frame)
        actions_row.pack(fill=tk.X, padx=6, pady=(4, 8))

        regen_btn = ttk.Button(actions_row, text="重新生成候选")
        regen_btn.pack(side=tk.LEFT)

        btns = ttk.Frame(actions_row)
        btns.pack(side=tk.LEFT, padx=(16, 0))

        def regen_action() -> None:
            base = normalize_base_url(self.base_url_var.get().strip())
            key = self.api_key_var.get().strip()
            model = self.model_var.get().strip()
            if not base or not key or not model:
                messagebox.showerror("错误", "请先填写 Base URL / API Key / Model。", parent=dlg)
                return
            status_var.set("⏳ 正在调用模型...")
            regen_btn.config(state=tk.DISABLED)
            vision_src = self._build_vision_src_for_item(tab.md_path, item.src) if self.vision_var.get() else None

            def worker() -> None:
                try:
                    result = self._generate_single_candidates(tab, item, explicit_refs, alt_text, title_attr, vision_src)
                except Exception as exc:
                    self.after(0, lambda: regen_fail(str(exc)))
                    return
                self.after(0, lambda: regen_success(result))

            def regen_success(result: Dict) -> None:
                regen_btn.config(state=tk.NORMAL)
                cand_list = result.get("candidates") or []
                normalized = sanitize_filename(result.get("normalized_title") or "")
                render_candidates(cand_list if isinstance(cand_list, list) else [], normalized or None)
                if normalized:
                    item.intent_var.set(normalized)
                    custom_var.set(normalized)
                    self._recalc_names(tab)
                if 0 <= item_pos < len(results_items):
                    try:
                        results_items[item_pos]["candidates"] = cand_list
                        if normalized:
                            results_items[item_pos]["normalized_title"] = normalized
                    except Exception:
                        pass
                status_var.set("✅ 候选已更新。")

            def regen_fail(msg: str) -> None:
                regen_btn.config(state=tk.NORMAL)
                status_var.set(f"⚠️ 候选生成失败：{msg}")

            threading.Thread(target=worker, daemon=True).start()

        regen_btn.configure(command=regen_action)

        def apply_choice(go_next: bool) -> None:
            choice = selected_var.get()
            if choice == "__custom__":
                chosen = sanitize_filename(custom_var.get() or "")
            else:
                chosen = sanitize_filename(choice or "")
            if not chosen:
                messagebox.showerror("错误", "请先选择或输入图意。", parent=dlg)
                return
            item.intent_var.set(chosen)
            if 0 <= item_pos < len(results_items):
                try:
                    results_items[item_pos]["normalized_title"] = chosen
                except Exception:
                    pass
            self._confirm_single_intent(tab, item, chosen)
            status_var.set(f"✅ 图意已更新：{chosen}")
            if go_next:
                dlg.destroy()
                self.after(
                    50,
                    lambda: self._open_single_dialog(tab, item_pos + 1)
                    if item_pos + 1 < len(tab.item_uis)
                    else None,
                )
            else:
                dlg.destroy()

        ttk.Button(btns, text="确定并继续", command=lambda: apply_choice(True)).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="确定并返回", command=lambda: apply_choice(False)).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="取消", command=dlg.destroy).pack(side=tk.LEFT, padx=4)
        status_var.set("提示：可重新生成候选，也可直接应用当前选择。")
        dlg.focus_set()

    def _confirm_single_intent(self, tab: TabState, item: ItemUI, chosen: str) -> None:
        try:
            self._recalc_names(tab)
            final_name = (item.final_var.get() or "").strip()
            results_items = tab.results.get("items", []) if isinstance(tab.results, dict) else []
            if 0 <= tab.item_uis.index(item) < len(results_items):
                try:
                    results_items[tab.item_uis.index(item)]["normalized_title"] = chosen
                except Exception:
                    pass
            if final_name:
                if self.verbose_var.get():
                    self._log_async(f"📝 仅更新图意：#{item.index} -> {chosen}")
            else:
                if self.verbose_var.get():
                    self._log_async(f"📝 已更新图意：#{item.index} -> {chosen}")
        except Exception:
            pass

    def _apply_all_in_tab(self, md_path: Path) -> None:
        tab = self.tabs.get(str(md_path))
        if not tab:
            return
        self._set_tab_processing(tab, True)
        self._recalc_names(tab)
        skip_set: Set[int] = {item.index for item in tab.item_uis if item.skip_var.get()}
        chosen_map = {
            item.index: sanitize_filename(item.intent_var.get() or "图意")
            for item in tab.item_uis
            if item.index not in skip_set
        }
        threading.Thread(
            target=self._apply_with_overrides,
            args=(tab, chosen_map, skip_set),
            daemon=True,
        ).start()

    def _apply_with_overrides(self, tab: TabState, chosen_map: Dict[int, str], skip_set: Set[int]) -> None:
        md_path = tab.md_path
        text = self._normalize_document_if_needed(md_path)
        if text == '':
            self.after(0, lambda p=md_path: self._clear_tab_processing(p))
            return
        refs = collect_images(text)

        total_images = len(refs)
        if self.verbose_var.get():
            self._log_async(f'🔄 开始应用命名：{md_path.name}（处理 {total_images} 张图片）')
        skip_set = set(skip_set)
        if skip_set:
            self._log_async(f"🧹 将从文档移除 {len(skip_set)} 张图片：{', '.join(str(i) for i in sorted(skip_set))}")

        attach_dir = md_path.parent / (self.attach_var.get().strip() or DEFAULT_ATTACH_DIR)
        mapping = load_image_mapping(attach_dir)
        seq_width = int(self.seq_width_var.get())
        max_len = int(self.max_len_var.get())
        name_tmpl = self.template_var.get().strip() or DEFAULT_NAME_TEMPLATE
        timeout = int(self.timeout_var.get())

        plan = load_attachment_plan(attach_dir)
        plan_path = plan_file_path(attach_dir)
        reuse_plan = False
        if plan and plan.get('document') == str(md_path) and not skip_set:
            statuses = [item.get('status') for item in plan.get('items', []) if isinstance(item, dict)]
            if statuses and all(status in ('pending', 'done') for status in statuses):
                reuse_plan = True
                self._log_async('🔁 检测到未完成的搬运计划，将尝试继续执行。')
            else:
                self._log_async('♻️ 发现旧搬运计划存在错误，将重新生成。')
        if not reuse_plan:
            plan = build_attachment_plan(
                md_path,
                text,
                refs,
                chosen_map,
                tab.title,
                attach_dir,
                name_tmpl,
                seq_width,
                max_len,
                skip_indexes=skip_set,
            )
            if plan.get('items'):
                save_attachment_plan(attach_dir, plan)
                self._log_async(f"📝 已生成搬运计划：共 {len(plan.get('items', []))} 项。")
            else:
                self._log_async('ℹ️ 所选图片均无需搬运计划（全部跳过或仅删除）。')

        def _log_plan_step(info: Dict) -> None:
            idx = info.get('index')
            action = info.get('action')
            status = info.get('status')
            target = info.get('target')
            self._log_async(f"   · 计划执行 #{idx} {action} -> {target} [{status}]")

        plan_items = plan.get('items', []) if isinstance(plan, dict) else []
        mapping_changed = False
        if plan_items:
            self._log_async(f'📥 开始回链（搬运计划执行）：{md_path.name}')
            success, mapping_changed = execute_attachment_plan(
                plan,
                md_path,
                attach_dir,
                timeout,
                mapping,
                logger=_log_plan_step,
                prefer_move=True,
            )
            if not success:
                self._log_async('❌ 回链中止：搬运计划执行失败，可修复问题后重新执行。')
                self._log_async(f'ℹ️ 临时搬运计划保留在：{plan_path}')
                self._log_async('提示：修复问题后可再次执行“应用命名”以继续处理。')
                self.after(0, lambda p=md_path: self._clear_tab_processing(p))
                return

            if not all(item.get('status') == 'done' for item in plan_items):
                self._log_async('⚠️ 搬运计划存在未完成条目，请检查后重试。')
                self._log_async(f'ℹ️ 临时搬运计划保留在：{plan_path}')
                self._log_async('提示：修复问题后可再次执行“应用命名”以继续处理。')
                self.after(0, lambda p=md_path: self._clear_tab_processing(p))
                return
            self._log_async('✅ 回链搬运执行完成。')

        index_to_target = {item['index']: item.get('target_rel') for item in plan_items if isinstance(item, dict)}

        new_parts: List[str] = []
        cursor = 0
        for i, ref in enumerate(refs):
            new_parts.append(text[cursor:ref.start])
            index = i + 1
            if index in skip_set:
                if self.verbose_var.get():
                    self._log_async(f'🧽 已移除图片引用：#{index}')
                cursor = ref.end
                continue
            target_rel = index_to_target.get(index, ref.src)
            original_seg = text[ref.start:ref.end]
            new_seg = original_seg.replace(ref.src, target_rel)
            if ref.kind == 'md':
                m2 = MD_IMAGE_RE.search(original_seg)
                if m2:
                    alt_raw = m2.group(1)
                    title_text = (ref.title or '').strip().strip('"').strip("'")
                    alt_clean = re.sub(r'<[^>]+>', '', alt_raw or '')
                    alt_clean = alt_clean.replace('|', ' ').strip()
                    alt_clean = WHITESPACE_RE.sub(' ', alt_clean).strip()
                    trailing_title = f' "{title_text}"' if title_text else ''
                    new_seg = f'![{alt_clean}]({target_rel}{trailing_title})'
            new_parts.append(new_seg)
            cursor = ref.end
        new_parts.append(text[cursor:])
        new_text = ''.join(new_parts)

        if bool(self.backup_var.get()):
            backup_path = md_path.with_suffix(md_path.suffix + '.bak')
            try:
                backup_path.write_text(text, encoding="utf-8", newline="\n")
                self._log_async(f'🗂 已备份原文件 -> {backup_path}')
            except Exception as e:
                self._log_async(f'⚠️ 备份失败：{e}')

        if new_text != text:
            try:
                write_text_utf8(md_path, new_text)
                if self.verbose_var.get():
                    self._log_async(f'📄 文件写回完成：{md_path.name}')
                    self._log_async(f'   · 处理 {total_images} 张图片，全部完成')
                else:
                    self._log_async(f'✅ 已写回：{md_path}')
            except Exception as e:
                self._log_async(f'❌ 写回失败：{md_path} -> {e}')
        else:
            if self.verbose_var.get():
                self._log_async(f'ℹ️ 文档未发生变化：{md_path.name}（可能未能生成新路径或处理失败）')
            else:
                self._log_async('ℹ️ 文档未发生变化（可能未能生成新路径或处理失败）。')

        if plan_items:
            plan['completed'] = True
            plan['completed_at'] = time.time()
            archived = self._archive_plan_to_history(attach_dir, plan)
            if archived:
                cleared = self._clear_plan_file(attach_dir)
                if cleared:
                    self._log_async(f'🧹 已清空临时搬运计划：{plan_path.name}')
                else:
                    self._log_async(f'⚠️ 请手动检查临时搬运计划文件：{plan_path}')
            else:
                save_attachment_plan(attach_dir, plan)
                self._log_async(f'⚠️ 由于归档失败，临时搬运计划已保留：{plan_path}')
        if mapping_changed:
            save_image_mapping(attach_dir, mapping)
        self.after(0, lambda p=md_path: self._mark_tab_completed(p))
        self._log_async(f'📦 回链流程结束：{md_path.name}')

    def _localize_remote_for_file(self, md_path: Path) -> None:
        if MILFileProcessor is None:
            messagebox.showwarning("提示", "缺少 md_image_localizer 模块，无法本地化远程图片。")
            return
        attach = self.attach_var.get().strip() or DEFAULT_ATTACH_DIR
        timeout = int(self.timeout_var.get())
        self._log_async(f"▶️ 本地化远程图片（{md_path} -> {attach}/）...")

        def worker() -> None:
            try:
                processor = MILFileProcessor(md_path, attach, timeout, dry_run=False, rename_images=False)
                downloads, rewritten, refs = processor.process()
                self._log_async(f"✅ 本地化完成：下载 {downloads} 张，改写 {rewritten} 处，更新引用 {refs} 处")
            except Exception as e:
                self._log_async(f"❌ 本地化失败：{e}")

        threading.Thread(target=worker, daemon=True).start()

    def _apply_preview_on_label(self, data: bytes, label: ttk.Label, max_size: Tuple[int, int] = (780, 440)) -> None:
        if Image is not None and ImageTk is not None:
            try:
                im = Image.open(BytesIO(data))
                try:
                    im = im.convert("RGB")
                except Exception:
                    pass
                im.thumbnail(max_size)
                tk_img = ImageTk.PhotoImage(im)
                label.configure(image=tk_img, text="")
                label.image = tk_img
                return
            except Exception as exc:
                label.configure(text=f"预览加载失败：{exc}")
                return
        label.configure(text="预览需要 Pillow 库（pip install pillow）")

    def _archive_plan_to_history(self, attach_dir: Path, plan: Dict) -> bool:
        try:
            history_path = attach_dir / PLAN_HISTORY_FILENAME
            entry = {
                "timestamp": time.time(),
                "timestamp_iso": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "plan": copy.deepcopy(plan),
            }
            history_path.parent.mkdir(parents=True, exist_ok=True)
            with history_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False))
                fh.write("\n")
            self._log_async(f"🗃️ 已归档搬运计划：{history_path.name}")
            return True
        except Exception as exc:
            self._log_async(f"⚠️ 归档搬运计划失败：{exc}")
            return False

    def _clear_plan_file(self, attach_dir: Path) -> bool:
        try:
            attach_dir.mkdir(parents=True, exist_ok=True)
            path = plan_file_path(attach_dir)
            path.write_text("{}", encoding="utf-8")
            return True
        except Exception as exc:
            self._log_async(f"⚠️ 清空搬运计划失败：{exc}")
            return False

    def _ensure_markdown_tags(self, widget: tk.Text) -> None:
        if getattr(widget, "_md_tags_ready", False):
            return
        try:
            widget.configure(font=CONTEXT_FONT)
        except Exception:
            pass
        widget.tag_configure("md_heading_1", font=CONTEXT_HEADING_FONT_1)
        widget.tag_configure("md_heading_2", font=CONTEXT_HEADING_FONT_2)
        widget.tag_configure("md_heading_3", font=CONTEXT_HEADING_FONT_3)
        widget.tag_configure("md_bold", font=CONTEXT_BOLD_FONT)
        widget.tag_configure("md_bullet", lmargin1=18, lmargin2=34)
        widget.tag_configure("md_quote", lmargin1=18, lmargin2=30, foreground="#1e88e5")
        widget.tag_configure("md_code", background="#f5f5f5", foreground="#d6336c")
        widget.tag_configure("md_placeholder", foreground="#888888")
        setattr(widget, "_md_tags_ready", True)

    def _insert_markdown_inline(self, widget: tk.Text, text: str, base_tags: Tuple[str, ...]) -> None:
        pos = 0
        for match in MD_INLINE_RE.finditer(text):
            start, end = match.span()
            if start > pos:
                widget.insert(tk.END, text[pos:start], base_tags)
            if match.group(1):
                widget.insert(tk.END, match.group(2), base_tags + ("md_bold",))
            else:
                widget.insert(tk.END, match.group(3), base_tags + ("md_code",))
            pos = end
        if pos < len(text):
            widget.insert(tk.END, text[pos:], base_tags)

    def _insert_markdown_line(self, widget: tk.Text, line: str) -> None:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if not stripped:
            if indent:
                widget.insert(tk.END, " " * indent)
            return

        base_tags: List[str] = []
        text_body = stripped

        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            if level and (len(stripped) == level or stripped[level] in (" ", "\t")):
                text_body = stripped[level:].lstrip()
                base_tags.append(f"md_heading_{min(level, 3)}")
            else:
                if indent:
                    widget.insert(tk.END, " " * indent)
        elif stripped.startswith(("- ", "* ")):
            text_body = stripped[2:].lstrip()
            widget.insert(tk.END, "• ", ("md_bullet",))
            base_tags.append("md_bullet")
        elif stripped.startswith(">"):
            text_body = stripped[1:].lstrip()
            widget.insert(tk.END, "▎ ", ("md_quote",))
            base_tags.append("md_quote")
        else:
            if indent:
                widget.insert(tk.END, " " * indent)

        text_body = MD_LINK_RE.sub(lambda m: f"{m.group(1)} ({m.group(2)})", text_body)
        self._insert_markdown_inline(widget, text_body, tuple(base_tags))

    def _render_markdown(self, widget: scrolledtext.ScrolledText, content: str) -> None:
        normalized = (content or "").replace("\r\n", "\n").replace("\r", "\n")
        normalized = normalized.strip("\n")
        self._ensure_markdown_tags(widget)
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        if not normalized.strip():
            widget.insert("1.0", "（空）", ("md_placeholder",))
            widget.configure(state=tk.DISABLED)
            return
        lines = normalized.split("\n")
        for idx, line in enumerate(lines):
            if idx:
                widget.insert(tk.END, "\n")
            self._insert_markdown_line(widget, line)
        widget.configure(state=tk.DISABLED)

    def _run_simple_chat(self, base: str, key: str, model: str, system_prompt: str, user_text: str) -> str:
        """简易聊天调用封装：用于翻译/归纳等纯文本任务，返回原样字符串。"""
        base_norm = normalize_base_url((base or "").strip() or self.base_url_var.get().strip())
        api_key = (key or "").strip() or self.api_key_var.get().strip()
        mdl = (model or "").strip() or self.model_var.get().strip()
        sys_p = (system_prompt or "").strip() or "你是助手。只输出最终结果。"
        msgs = [
            {"role": "system", "content": sys_p},
            {"role": "user", "content": user_text or ""},
        ]
        out = call_openai_chat(
            base_norm,
            api_key,
            mdl,
            msgs,
            timeout=int(self.timeout_var.get()),
            max_retries=int(self.retries_var.get()),
            rate_limit=float(self.rate_limit_var.get()),
            verbose=bool(self.verbose_var.get()),
            expect_json=False,
        )
        return out or ""

    # ------------------------------------------------------------------ #
    # API 测试
    # ------------------------------------------------------------------ #
    def _on_test_api(self) -> None:
        try:
            base = normalize_base_url(self.base_url_var.get().strip())
            key = self.api_key_var.get().strip()
            model = self.model_var.get().strip()
            if not base or not key:
                messagebox.showerror("错误", "请先填写 Base URL 与 API Key。")
                return
            msgs = [
                {"role": "system", "content": "你是健康检查助手。只输出严格JSON，形如 {\"ok\":true}"},
                {"role": "user", "content": json.dumps({"ping": "hello"}, ensure_ascii=False)},
            ]
            out = call_openai_chat(
                base,
                key,
                model,
                msgs,
                timeout=int(self.timeout_var.get()),
                max_retries=int(self.retries_var.get()),
                rate_limit=float(self.rate_limit_var.get()),
                verbose=True,
            )
            data = safe_parse_json(out) if out else None
            if isinstance(data, dict):
                messagebox.showinfo("测试结果", f"连接成功：{base}\n模型：{model}\n返回：{json.dumps(data, ensure_ascii=False)}")
            else:
                snippet = (out or "")[:280]
                messagebox.showwarning("测试结果", f"已连接但返回不可解析：\n{snippet}")
        except Exception as e:
            messagebox.showerror("测试失败", str(e))

    def _on_test_vision(self) -> None:
        try:
            base = normalize_base_url(self.base_url_var.get().strip())
            key = self.api_key_var.get().strip()
            model = self.model_var.get().strip()
            if not base or not key:
                messagebox.showerror("错误", "请先填写 Base URL 与 API Key。")
                return
            asset = random.choice(VISION_TEST_ASSETS)
            msgs = build_ai_messages(
                "测试图片识别",
                "",
                "",
                "",
                [],
                None,
                None,
                vision_src=asset["data_url"],
                base_url=base,
            )
            out = call_openai_chat(
                base,
                key,
                model,
                msgs,
                timeout=int(self.timeout_var.get()),
                max_retries=int(self.retries_var.get()),
                rate_limit=float(self.rate_limit_var.get()),
                verbose=bool(self.verbose_var.get()),
            )
            data = safe_parse_json(out) if out else None
            if isinstance(data, dict):
                pretty = json.dumps(data, ensure_ascii=False, indent=2)
                messagebox.showinfo(
                    "识图测试结果",
                    f"测试样例：{asset['name']}（{asset['description']}）\n返回：\n{pretty}",
                )
            else:
                snippet = (out or "")[:280]
                messagebox.showwarning("识图测试结果", f"已连接但返回不可解析：\n{snippet}")
        except Exception as exc:
            messagebox.showerror("测试失败", str(exc))


def main() -> None:
    app = BatchApp()
    app.mainloop()


if __name__ == "__main__":
    main()
