#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 图片命名器 - Figma风格现代化GUI (稳定版)
完整还原Figma设计的界面布局和交互
使用兼容的颜色格式，确保跨平台稳定性
"""

from __future__ import annotations
import json
import os
import re
import sys
import threading
import tkinter as tk
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import customtkinter as ctk
from tkinter import filedialog, messagebox

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None

try:
    import requests
except Exception:
    requests = None

# 添加工具目录到路径
THIS_FILE = Path(__file__).resolve()
TOOL_DIR = THIS_FILE.parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

try:
    from ai_image_intent_namer import (
        Config,
        read_text,
        write_text_utf8,
        extract_doc_title,
        collect_images,
        find_neighbor_text,
        sanitize_filename,
        is_remote_url,
        resolve_local_image,
        name_with_template,
        build_ai_messages,
        call_openai_chat,
        safe_parse_json,
        validate_ai_result,
        normalize_base_url,
    )
except Exception as e:
    print("❌ 无法导入后端模块 ai_image_intent_namer.py")
    print("错误:", e)
    sys.exit(1)

# 常量定义
APP_TITLE = "AI 图片命名器"
PROFILES_PATH = TOOL_DIR / "ai_image_intent_namer_gui.profiles.json"
DEFAULT_NAME_TEMPLATE = "{title}_{index:02d}_{intent}"
DEFAULT_ATTACH_DIR = "attachments"

# 兼容的颜色系统（使用标准hex格式，不使用rgba）
COLORS = {
    # 主色系
    "primary": "#2563eb",           # 蓝色
    "primary_dark": "#1d4ed8",      # 深蓝
    "primary_light": "#3b82f6",     # 浅蓝
    "primary_lighter": "#60a5fa",   # 更浅蓝
    
    # 语义色
    "success": "#16a34a",           # 成功绿
    "success_dark": "#15803d",      # 深绿
    "warning": "#f59e0b",           # 警告橙
    "error": "#dc2626",             # 错误红
    "error_dark": "#b91c1c",        # 深红
    
    # 中性色
    "background": "#ffffff",        # 背景白
    "surface": "#f8fafc",           # 卡片背景
    "surface_dark": "#f1f5f9",      # 深卡片背景
    "border": "#e2e8f0",            # 边框
    "text": "#0f172a",              # 主文本
    "text_secondary": "#64748b",    # 次要文本
    "muted": "#94a3b8",             # 静音文本
    "gray": "#6b7280",              # 灰色
}

# 设置主题
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


@dataclass
class ImageEntry:
    """图片条目数据"""
    index: int
    src: str
    alt: Optional[str]
    title_attr: Optional[str]
    above_text: str
    below_text: str
    between_text: str
    intent: str = ""
    candidates: List[str] = field(default_factory=list)
    final_name: str = ""
    skipped: bool = False
    status: str = "pending"
    
    # UI引用
    row_frame: Optional[ctk.CTkFrame] = None
    intent_var: Optional[tk.StringVar] = None
    final_var: Optional[tk.StringVar] = None
    skip_var: Optional[tk.BooleanVar] = None


@dataclass
class MarkdownFile:
    """Markdown文件数据"""
    path: Path
    name: str
    status: str = "pending"
    image_count: int = 0
    processed_count: int = 0
    
    # UI引用
    card_frame: Optional[ctk.CTkFrame] = None
    stats_label: Optional[ctk.CTkLabel] = None
    status_badge: Optional[ctk.CTkLabel] = None


class FigmaStyleApp(ctk.CTk):
    """Figma风格的现代化应用（稳定版）"""
    
    def __init__(self) -> None:
        super().__init__()
        
        # 窗口设置
        self.title(APP_TITLE)
        self.geometry("1600x900")
        self.minsize(1400, 800)
        
        # 数据状态
        self.files: List[MarkdownFile] = []
        self.selected_file: Optional[MarkdownFile] = None
        self.image_entries: List[ImageEntry] = []
        self.stop_flag = False
        self.is_processing = False
        
        # 配置变量
        self._init_config_vars()
        
        # 预设数据
        self._init_presets()
        
        # 构建界面
        self._build_ui()
        
        # 加载配置
        self._load_config()
    
    def _init_config_vars(self) -> None:
        """初始化配置变量"""
        # API配置
        self.base_url_var = tk.StringVar(value="https://api.openai.com/v1")
        self.api_key_var = tk.StringVar(value="")
        self.model_var = tk.StringVar(value="gpt-4o-mini")
        self.temperature_var = tk.DoubleVar(value=0.3)
        self.max_tokens_var = tk.IntVar(value=150)
        self.timeout_var = tk.IntVar(value=30)
        
        # 命名模板
        self.template_var = tk.StringVar(value=DEFAULT_NAME_TEMPLATE)
        
        # 运行选项
        self.attach_dir_var = tk.StringVar(value=DEFAULT_ATTACH_DIR)
        self.use_vision_var = tk.BooleanVar(value=False)
        self.skip_existing_var = tk.BooleanVar(value=False)
        self.dry_run_var = tk.BooleanVar(value=True)
        self.verbose_var = tk.BooleanVar(value=False)
        
        # UI状态
        self.language_var = tk.StringVar(value="中文")
        self.filter_mode_var = tk.StringVar(value="all")
        
        # 统计数据
        self.stats_dirs = tk.IntVar(value=0)
        self.stats_llm_calls = tk.IntVar(value=0)
        self.stats_tokens = tk.IntVar(value=0)
    
    def _init_presets(self) -> None:
        """初始化预设数据"""
        self.presets = {
            "ai": [
                {"id": "siliconflow-qw", "name": "Siliconflow - Qw", "model": "Qwen/Qwen2.5-7B-Instruct"},
                {"id": "gpt4o", "name": "GPT-4o", "model": "gpt-4o"},
                {"id": "gpt4o-mini", "name": "GPT-4o Mini", "model": "gpt-4o-mini"},
                {"id": "claude", "name": "Claude 3.5", "model": "claude-3-5-sonnet-20241022"},
            ],
            "naming": [
                {"id": "title_seq_intent", "name": "标题_序号_图意", "template": "{title}_{index:02d}_{intent}"},
                {"id": "block_intent", "name": "段落_图意", "template": "{block:02d}_{intent}"},
                {"id": "intent_only", "name": "仅图意", "template": "{intent}"},
            ],
            "runtime": [
                {"id": "safe", "name": "安全模式", "use_vision": False, "dry_run": True},
                {"id": "standard", "name": "标准模式", "use_vision": False, "dry_run": False},
                {"id": "vision", "name": "视觉增强", "use_vision": True, "dry_run": False},
            ],
        }
        
        self.selected_ai_preset = tk.StringVar(value="Siliconflow - Qw")
        self.selected_naming_preset = tk.StringVar(value="标题_序号_图意")
        self.selected_runtime_preset = tk.StringVar(value="安全模式")
    
    def _build_ui(self) -> None:
        """构建Figma风格的UI"""
        # 主布局：2列3行网格
        self.grid_columnconfigure(0, weight=0, minsize=280)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        
        # 构建各个区域
        self._build_app_bar()
        self._build_file_list()
        self._build_processing_area()
        self._build_log_panel()
    
    def _build_app_bar(self) -> None:
        """构建顶部应用栏"""
        app_bar = ctk.CTkFrame(self, height=70, corner_radius=0, fg_color=COLORS["primary"])
        app_bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        app_bar.grid_propagate(False)
        app_bar.grid_columnconfigure(1, weight=1)
        
        # 左侧：标题
        title_frame = ctk.CTkFrame(app_bar, fg_color="transparent")
        title_frame.grid(row=0, column=0, padx=25, pady=15, sticky="w")
        
        ctk.CTkLabel(
            title_frame,
            text="AI 图片意图批量命名",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white"
        ).pack(side="left")
        
        # 中间：预设选择器
        presets_frame = ctk.CTkFrame(app_bar, fg_color="transparent")
        presets_frame.grid(row=0, column=1, padx=20, sticky="ew")
        
        # AI模型预设
        ai_container = ctk.CTkFrame(presets_frame, fg_color=COLORS["primary_light"], corner_radius=8)
        ai_container.pack(side="left", padx=8, fill="y")
        
        ctk.CTkLabel(
            ai_container,
            text="AI模型",
            font=ctk.CTkFont(size=11),
            text_color="white"
        ).pack(side="left", padx=(12, 8))
        
        self.ai_preset_menu = ctk.CTkOptionMenu(
            ai_container,
            variable=self.selected_ai_preset,
            values=[p["name"] for p in self.presets["ai"]],
            width=140,
            height=32,
            fg_color="white",
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_dark"],
            text_color=COLORS["text"],
            command=self._on_ai_preset_changed,
        )
        self.ai_preset_menu.pack(side="left", padx=(0, 12))
        
        # 命名规则预设
        naming_container = ctk.CTkFrame(presets_frame, fg_color=COLORS["primary_light"], corner_radius=8)
        naming_container.pack(side="left", padx=8, fill="y")
        
        ctk.CTkLabel(
            naming_container,
            text="命名规则",
            font=ctk.CTkFont(size=11),
            text_color="white"
        ).pack(side="left", padx=(12, 8))
        
        self.naming_preset_menu = ctk.CTkOptionMenu(
            naming_container,
            variable=self.selected_naming_preset,
            values=[p["name"] for p in self.presets["naming"]],
            width=160,
            height=32,
            fg_color="white",
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_dark"],
            text_color=COLORS["text"],
            command=self._on_naming_preset_changed,
        )
        self.naming_preset_menu.pack(side="left", padx=(0, 12))
        
        # 运行选项预设（匹配Figma的"安全模式"）
        self.runtime_preset_menu = ctk.CTkOptionMenu(
            presets_frame,
            variable=self.selected_runtime_preset,
            values=[p["name"] for p in self.presets["runtime"]],
            width=140,
            height=32,
            fg_color="white",
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_dark"],
            text_color=COLORS["text"],
            command=self._on_runtime_preset_changed,
        )
        self.runtime_preset_menu.pack(side="left", padx=8)
        
        # 右侧：操作按钮
        actions_frame = ctk.CTkFrame(app_bar, fg_color="transparent")
        actions_frame.grid(row=0, column=2, padx=25, pady=15, sticky="e")
        
        ctk.CTkButton(
            actions_frame,
            text="❓ 帮助",
            width=80,
            height=36,
            fg_color=COLORS["primary_light"],
            hover_color=COLORS["primary_lighter"],
            text_color="white",
            command=self._show_help,
        ).pack(side="right", padx=5)
        
        # 语言切换
        self.language_menu = ctk.CTkOptionMenu(
            actions_frame,
            variable=self.language_var,
            values=["中文", "English"],
            width=90,
            height=36,
            fg_color=COLORS["primary_light"],
            button_color=COLORS["primary_light"],
            button_hover_color=COLORS["primary_lighter"],
            text_color="white",
        )
        self.language_menu.pack(side="right", padx=5)
        
        ctk.CTkButton(
            actions_frame,
            text="⚙️ 预设管理",
            width=110,
            height=36,
            fg_color=COLORS["primary_light"],
            hover_color=COLORS["primary_lighter"],
            text_color="white",
            command=self._open_settings,
        ).pack(side="right", padx=5)
    
    def _build_file_list(self) -> None:
        """构建文件列表面板"""
        file_panel = ctk.CTkFrame(self, corner_radius=0)
        file_panel.grid(row=1, column=0, sticky="nsew")
        file_panel.grid_rowconfigure(3, weight=1)
        
        # 标题
        header = ctk.CTkFrame(file_panel, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            header,
            text="📁 文档列表",
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w"
        ).pack(fill="x")
        
        self.file_count_label = ctk.CTkLabel(
            header,
            text="0 个文件",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        self.file_count_label.pack(fill="x", pady=(5, 0))
        
        # 操作按钮
        btn_frame = ctk.CTkFrame(file_panel, fg_color="transparent")
        btn_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        btn_frame.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkButton(
            btn_frame,
            text="➕ 添加文件",
            command=self._on_add_files,
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        
        ctk.CTkButton(
            btn_frame,
            text="🗑️ 移除",
            command=self._on_remove_files,
            height=34,
            fg_color="transparent",
            border_width=2,
        ).grid(row=1, column=0, sticky="ew", padx=(0, 5))
        
        ctk.CTkButton(
            btn_frame,
            text="清空",
            command=self._on_clear_files,
            height=34,
            fg_color="transparent",
            border_width=2,
        ).grid(row=1, column=1, sticky="ew", padx=(5, 0))
        
        # 分隔线
        ctk.CTkFrame(file_panel, height=1, fg_color=COLORS["border"]).grid(
            row=2, column=0, sticky="ew", padx=20, pady=(0, 10)
        )
        
        # 文件列表（可滚动）
        self.file_list_container = ctk.CTkScrollableFrame(file_panel, fg_color="transparent")
        self.file_list_container.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # 空状态提示
        self.empty_hint = ctk.CTkLabel(
            self.file_list_container,
            text='暂无文件\n\n拖拽 Markdown 文件到此处\n或点击上方"添加文件"按钮',
            font=ctk.CTkFont(size=13),
            text_color=COLORS["muted"],
            justify="center",
        )
        self.empty_hint.pack(expand=True, pady=50)
    
    def _build_processing_area(self) -> None:
        """构建主处理区"""
        main_area = ctk.CTkFrame(self, corner_radius=0, fg_color=COLORS["background"])
        main_area.grid(row=1, column=1, sticky="nsew")
        main_area.grid_rowconfigure(2, weight=1)
        main_area.grid_columnconfigure(0, weight=1)
        
        # 控制栏
        control_bar = ctk.CTkFrame(main_area, fg_color=COLORS["surface"], height=80)
        control_bar.grid(row=0, column=0, sticky="ew")
        control_bar.grid_propagate(False)
        control_bar.grid_columnconfigure(1, weight=1)
        
        # 文件信息
        file_info = ctk.CTkFrame(control_bar, fg_color="transparent")
        file_info.grid(row=0, column=0, sticky="w", padx=25, pady=15)
        
        self.current_file_label = ctk.CTkLabel(
            file_info,
            text="请从左侧选择文件",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w"
        )
        self.current_file_label.pack(anchor="w")
        
        self.file_stats_label = ctk.CTkLabel(
            file_info,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        self.file_stats_label.pack(anchor="w", pady=(3, 0))
        
        # 操作按钮
        actions = ctk.CTkFrame(control_bar, fg_color="transparent")
        actions.grid(row=0, column=2, sticky="e", padx=25, pady=15)
        
        self.batch_preview_btn = ctk.CTkButton(
            actions,
            text="▶️ 批量预览",
            command=self._on_batch_preview,
            width=140,
            height=38,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["primary"],
        )
        self.batch_preview_btn.pack(side="left", padx=5)
        
        self.write_back_btn = ctk.CTkButton(
            actions,
            text="💾 批量写回",
            command=self._on_write_back,
            width=130,
            height=38,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["success"],
            state="disabled",
        )
        self.write_back_btn.pack(side="left", padx=5)
        
        ctk.CTkButton(
            actions,
            text="🔍 查找替换",
            command=self._show_find_replace,
            width=120,
            height=38,
            fg_color="transparent",
            border_width=2,
        ).pack(side="left", padx=5)
        
        # 过滤栏
        filter_bar = ctk.CTkFrame(main_area, fg_color="transparent", height=50)
        filter_bar.grid(row=1, column=0, sticky="new", padx=25, pady=(15, 10))
        
        ctk.CTkLabel(
            filter_bar,
            text="过滤:",
            font=ctk.CTkFont(size=13),
        ).pack(side="left", padx=(0, 10))
        
        ctk.CTkSegmentedButton(
            filter_bar,
            values=["全部", "待确认", "已跳过"],
            variable=self.filter_mode_var,
            command=self._on_filter_change,
        ).pack(side="left")
        
        # 图片表格容器
        self.table_container = ctk.CTkScrollableFrame(main_area, fg_color="transparent")
        self.table_container.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 15))
        
        # 空状态提示
        self.table_empty_hint = ctk.CTkLabel(
            self.table_container,
            text='👈 请从左侧选择或添加 Markdown 文件\n\n点击"批量预览"后，这里将显示所有图片',
            font=ctk.CTkFont(size=15),
            text_color=COLORS["muted"],
            justify="center",
        )
        self.table_empty_hint.pack(expand=True, pady=100)
    
    def _build_log_panel(self) -> None:
        """构建日志面板"""
        log_panel = ctk.CTkFrame(self, corner_radius=0, fg_color=COLORS["surface"], height=180)
        log_panel.grid(row=2, column=0, columnspan=2, sticky="ew")
        log_panel.grid_propagate(False)
        log_panel.grid_columnconfigure(0, weight=1)
        log_panel.grid_rowconfigure(2, weight=1)
        
        # 头部
        log_header = ctk.CTkFrame(log_panel, fg_color="transparent", height=40)
        log_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 5))
        log_header.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            log_header,
            text="📋 处理日志",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        
        self.status_label = ctk.CTkLabel(
            log_header,
            text="准备就绪",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
        )
        self.status_label.grid(row=0, column=1, sticky="w", padx=20)
        
        self.stop_btn = ctk.CTkButton(
            log_header,
            text="⏸️ 停止",
            command=self._on_stop,
            width=80,
            height=28,
            fg_color=COLORS["error"],
            state="disabled",
        )
        self.stop_btn.grid(row=0, column=2, sticky="e")
        
        # 进度条
        self.progress_bar = ctk.CTkProgressBar(log_panel, height=6)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.progress_bar.set(0)
        
        # 日志文本
        log_frame = ctk.CTkFrame(log_panel, fg_color="white", corner_radius=8)
        log_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 10))
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        self.log_text = tk.Text(
            log_frame,
            height=2,
            wrap=tk.WORD,
            relief=tk.FLAT,
            bg="white",
            fg=COLORS["text"],
            font=("Consolas", 10),
            padx=10,
            pady=8,
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        
        log_scroll = ctk.CTkScrollbar(log_frame, command=self.log_text.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scroll.set)
        
        # 底部状态栏（匹配Figma设计）
        status_bar = ctk.CTkFrame(log_panel, fg_color="white", height=40)
        status_bar.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 10))
        status_bar.grid_propagate(False)
        status_bar.grid_columnconfigure(1, weight=1)
        
        # 左侧：附件目录标签
        ctk.CTkLabel(
            status_bar,
            text="附件目录",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
        ).grid(row=0, column=0, sticky="w", padx=15)
        
        # 中间：统计信息
        self.stats_label = ctk.CTkLabel(
            status_bar,
            text="目录: 0  |  LLM 调用: 0  |  Tokens: 0",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
        )
        self.stats_label.grid(row=0, column=1, sticky="e", padx=15)
        
        # 右侧：操作按钮
        btn_frame = ctk.CTkFrame(status_bar, fg_color="transparent")
        btn_frame.grid(row=0, column=2, sticky="e", padx=10)
        
        ctk.CTkButton(
            btn_frame,
            text="收起",
            width=60,
            height=28,
            fg_color="transparent",
            text_color=COLORS["text"],
            hover_color=COLORS["surface"],
            border_width=1,
            border_color=COLORS["border"],
        ).pack(side="right", padx=2)
        
        ctk.CTkButton(
            btn_frame,
            text="清空",
            width=60,
            height=28,
            fg_color="transparent",
            text_color=COLORS["text"],
            hover_color=COLORS["surface"],
            border_width=1,
            border_color=COLORS["border"],
            command=lambda: self.log_text.delete("1.0", tk.END),
        ).pack(side="right", padx=2)
        
        ctk.CTkButton(
            btn_frame,
            text="复制全部",
            width=70,
            height=28,
            fg_color="transparent",
            text_color=COLORS["text"],
            hover_color=COLORS["surface"],
            border_width=1,
            border_color=COLORS["border"],
        ).pack(side="right", padx=2)
        
        ctk.CTkButton(
            btn_frame,
            text="过滤",
            width=60,
            height=28,
            fg_color="transparent",
            text_color=COLORS["text"],
            hover_color=COLORS["surface"],
            border_width=1,
            border_color=COLORS["border"],
        ).pack(side="right", padx=2)
    
    # ================================================================
    # 文件操作
    # ================================================================
    
    def _on_add_files(self) -> None:
        """添加文件"""
        paths = filedialog.askopenfilenames(
            title="选择 Markdown 文件",
            filetypes=[("Markdown", "*.md *.markdown"), ("所有文件", "*.*")]
        )
        
        if not paths:
            return
        
        added_count = 0
        for path_str in paths:
            path = Path(path_str)
            if any(f.path == path for f in self.files):
                continue
            
            md_file = MarkdownFile(path=path, name=path.name)
            self.files.append(md_file)
            self._add_file_card(md_file)
            added_count += 1
        
        if added_count > 0:
            self._update_file_count()
            self._log(f"✅ 已添加 {added_count} 个文件")
            self.empty_hint.pack_forget()
    
    def _add_file_card(self, md_file: MarkdownFile) -> None:
        """添加文件卡片"""
        card = ctk.CTkFrame(
            self.file_list_container,
            corner_radius=8,
            fg_color="white",
            border_width=2,
            border_color=COLORS["border"],
        )
        card.pack(fill="x", padx=10, pady=5)
        
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(fill="x", padx=15, pady=12)
        
        name_label = ctk.CTkLabel(
            info_frame,
            text=md_file.name,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        name_label.pack(fill="x")
        
        stats_label = ctk.CTkLabel(
            info_frame,
            text="0 张图片",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
            anchor="w",
        )
        stats_label.pack(fill="x", pady=(3, 0))
        
        status_badge = ctk.CTkLabel(
            card,
            text="待处理",
            font=ctk.CTkFont(size=10),
            fg_color=COLORS["muted"],
            text_color="white",
            corner_radius=4,
            width=60,
            height=20,
        )
        status_badge.place(relx=1.0, rely=0, x=-15, y=12, anchor="ne")
        
        # 绑定点击事件
        def on_click(e=None):
            self._select_file(md_file)
        
        for widget in [card, info_frame, name_label, stats_label]:
            widget.bind("<Button-1>", on_click)
        
        # 保存UI引用
        md_file.card_frame = card
        md_file.stats_label = stats_label
        md_file.status_badge = status_badge
    
    def _select_file(self, md_file: MarkdownFile) -> None:
        """选择文件"""
        self.selected_file = md_file
        self.current_file_label.configure(text=md_file.name)
        self.file_stats_label.configure(text=f"{md_file.image_count} 张图片")
        
        # 更新选中状态
        for f in self.files:
            if f.card_frame:
                if f == md_file:
                    f.card_frame.configure(border_color=COLORS["primary"], border_width=2)
                else:
                    f.card_frame.configure(border_color=COLORS["border"], border_width=2)
        
        self._log(f"📄 已选择: {md_file.name}")
    
    def _on_remove_files(self) -> None:
        """移除选中的文件"""
        if not self.selected_file:
            messagebox.showwarning("提示", "请先选择要移除的文件")
            return
        
        if messagebox.askyesno("确认", f"确定要移除 {self.selected_file.name} 吗？"):
            if self.selected_file.card_frame:
                self.selected_file.card_frame.destroy()
            
            self.files.remove(self.selected_file)
            self.selected_file = None
            self._update_file_count()
            self._log("🗑️ 已移除文件")
            
            if not self.files:
                self.empty_hint.pack(expand=True, pady=50)
    
    def _on_clear_files(self) -> None:
        """清空所有文件"""
        if not self.files:
            return
        
        if messagebox.askyesno("确认", "确定要清空所有文件吗？"):
            for f in self.files:
                if f.card_frame:
                    f.card_frame.destroy()
            
            self.files.clear()
            self.selected_file = None
            self.image_entries.clear()
            self._update_file_count()
            self.empty_hint.pack(expand=True, pady=50)
            self._log("🗑️ 已清空文件列表")
    
    def _update_file_count(self) -> None:
        """更新文件计数"""
        count = len(self.files)
        self.file_count_label.configure(text=f"{count} 个文件")
    
    # ================================================================
    # 批量处理
    # ================================================================
    
    def _on_batch_preview(self) -> None:
        """批量预览处理"""
        if not self.selected_file:
            messagebox.showwarning("提示", "请先选择一个文件")
            return
        
        self.stop_flag = False
        self.is_processing = True
        self.batch_preview_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.table_empty_hint.pack_forget()
        
        thread = threading.Thread(target=self._batch_preview_worker, daemon=True)
        thread.start()
    
    def _batch_preview_worker(self) -> None:
        """批量预览工作线程"""
        try:
            md_file = self.selected_file
            if not md_file:
                return
            
            self._log(f"📖 正在读取: {md_file.name}")
            text = read_text(md_file.path)
            title = extract_doc_title(text)
            images = collect_images(text)
            
            self._log(f"🖼️ 找到 {len(images)} 张图片")
            
            md_file.image_count = len(images)
            if md_file.stats_label:
                self.after(0, lambda: md_file.stats_label.configure(text=f"{len(images)} 张图片"))
            
            self.after(0, self._clear_table)
            
            entries = []
            for idx, img_info in enumerate(images):
                if self.stop_flag:
                    break
                
                above, below, between = find_neighbor_text(text, img_info["line_no"])
                
                entry = ImageEntry(
                    index=idx + 1,
                    src=img_info["src"],
                    alt=img_info.get("alt"),
                    title_attr=img_info.get("title"),
                    above_text=above,
                    below_text=below,
                    between_text=between,
                )
                entries.append(entry)
                
                self.after(0, lambda e=entry: self._add_table_row(e))
                
                progress = (idx + 1) / len(images)
                self.after(0, lambda p=progress: self.progress_bar.set(p))
            
            self.image_entries = entries
            self._log(f"✅ 预览完成，共 {len(entries)} 张图片")
            
        except Exception as e:
            self._log(f"❌ 处理失败: {e}")
        finally:
            self.after(0, self._batch_complete)
    
    def _clear_table(self) -> None:
        """清空表格"""
        for widget in self.table_container.winfo_children():
            widget.destroy()
    
    def _add_table_row(self, entry: ImageEntry) -> None:
        """添加表格行（卡片式）"""
        row = ctk.CTkFrame(
            self.table_container,
            corner_radius=8,
            fg_color="white",
            border_width=1,
            border_color=COLORS["border"],
        )
        row.pack(fill="x", padx=5, pady=4)
        row.grid_columnconfigure(2, weight=1)
        
        # 序号
        ctk.CTkLabel(
            row,
            text=f"#{entry.index}",
            font=ctk.CTkFont(size=14, weight="bold"),
            width=50,
        ).grid(row=0, column=0, padx=15, pady=12, sticky="w")
        
        # 缩略图占位
        thumb_frame = ctk.CTkFrame(row, width=60, height=60, fg_color=COLORS["surface"])
        thumb_frame.grid(row=0, column=1, padx=(0, 15), pady=12)
        thumb_frame.grid_propagate(False)
        
        ctk.CTkLabel(
            thumb_frame,
            text="🖼️",
            font=ctk.CTkFont(size=24),
        ).place(relx=0.5, rely=0.5, anchor="center")
        
        # 信息区
        info_frame = ctk.CTkFrame(row, fg_color="transparent")
        info_frame.grid(row=0, column=2, padx=(0, 15), pady=12, sticky="ew")
        info_frame.grid_columnconfigure(1, weight=1)
        
        # 原始路径
        ctk.CTkLabel(
            info_frame,
            text="原始路径:",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
            width=70,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        
        ctk.CTkLabel(
            info_frame,
            text=entry.src[:80] + "..." if len(entry.src) > 80 else entry.src,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=(5, 0))
        
        # AI意图输入
        ctk.CTkLabel(
            info_frame,
            text="AI意图:",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
            width=70,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))
        
        intent_var = tk.StringVar(value=entry.intent)
        ctk.CTkEntry(
            info_frame,
            textvariable=intent_var,
            placeholder_text="等待生成或手动输入...",
            height=32,
        ).grid(row=1, column=1, sticky="ew", padx=(5, 0), pady=(8, 0))
        
        # 最终命名
        ctk.CTkLabel(
            info_frame,
            text="最终命名:",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
            width=70,
            anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))
        
        final_var = tk.StringVar(value=entry.final_name or entry.src)
        ctk.CTkLabel(
            info_frame,
            textvariable=final_var,
            font=ctk.CTkFont(size=11),
            text_color=COLORS["primary"],
            anchor="w",
        ).grid(row=2, column=1, sticky="w", padx=(5, 0), pady=(8, 0))
        
        # 操作区
        actions_frame = ctk.CTkFrame(row, fg_color="transparent")
        actions_frame.grid(row=0, column=3, padx=15, pady=12, sticky="e")
        
        # 跳过复选框
        skip_var = tk.BooleanVar(value=entry.skipped)
        ctk.CTkCheckBox(
            actions_frame,
            text="跳过",
            variable=skip_var,
            width=60,
        ).pack(side="top", pady=(0, 8))
        
        # 复审按钮
        ctk.CTkButton(
            actions_frame,
            text="👁️ 复审",
            command=lambda e=entry: self._open_review_panel(e),
            width=80,
            height=30,
            fg_color=COLORS["primary"],
        ).pack(side="top")
        
        # 保存UI引用
        entry.row_frame = row
        entry.intent_var = intent_var
        entry.final_var = final_var
        entry.skip_var = skip_var
    
    def _batch_complete(self) -> None:
        """批量处理完成"""
        self.is_processing = False
        self.batch_preview_btn.configure(state="normal")
        self.write_back_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress_bar.set(0)
    
    def _on_write_back(self) -> None:
        """批量写回"""
        if not self.image_entries:
            messagebox.showwarning("提示", "没有可写回的内容")
            return
        
        messagebox.showinfo("提示", "批量写回功能开发中...")
    
    def _on_stop(self) -> None:
        """停止处理"""
        self.stop_flag = True
        self._log("⏸️ 正在停止...")
    
    def _on_filter_change(self, value: str) -> None:
        """过滤模式改变"""
        self._log(f"过滤模式: {value}")
    
    # ================================================================
    # 单图复审面板
    # ================================================================
    
    def _open_review_panel(self, entry: ImageEntry) -> None:
        """打开单图复审面板"""
        panel = ctk.CTkToplevel(self)
        panel.title(f"单图复审 - #{entry.index}")
        panel.geometry("1100x750")
        panel.transient(self)
        
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)
        
        # 顶部栏
        header = ctk.CTkFrame(panel, fg_color=COLORS["primary"], height=60)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            header,
            text=f"图片 #{entry.index}",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white",
        ).grid(row=0, column=0, padx=25, pady=15, sticky="w")
        
        ctk.CTkLabel(
            header,
            text="待确认",
            font=ctk.CTkFont(size=13),
            text_color="white",
        ).grid(row=0, column=1, padx=25, pady=15, sticky="w")
        
        ctk.CTkButton(
            header,
            text="✕",
            command=panel.destroy,
            width=40,
            height=40,
            fg_color=COLORS["primary_light"],
            hover_color=COLORS["primary_lighter"],
            text_color="white",
            font=ctk.CTkFont(size=18),
        ).grid(row=0, column=2, padx=25, pady=15, sticky="e")
        
        # 内容区（左右分栏）
        content = ctk.CTkFrame(panel, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)
        
        # 左侧：图片预览
        left_panel = ctk.CTkFrame(content, fg_color=COLORS["surface"])
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)
        left_panel.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(
            left_panel,
            text="图片预览",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(15, 10))
        
        preview_frame = ctk.CTkFrame(left_panel, fg_color="white")
        preview_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        
        ctk.CTkLabel(
            preview_frame,
            text="🖼️\n\n正在加载图片...",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["muted"],
        ).pack(expand=True, fill="both", padx=20, pady=20)
        
        # 右侧：上下文和候选项
        right_panel = ctk.CTkScrollableFrame(content, fg_color="transparent")
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        
        # 上下文部分
        context_section = ctk.CTkFrame(right_panel, fg_color="white")
        context_section.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            context_section,
            text="📝 上下文",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(15, 10))
        
        if entry.above_text:
            ctk.CTkLabel(
                context_section,
                text="上文:",
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_secondary"],
            ).pack(anchor="w", padx=20, pady=(5, 2))
            
            above_text = ctk.CTkTextbox(context_section, height=80, wrap="word")
            above_text.pack(fill="x", padx=20, pady=(0, 10))
            above_text.insert("1.0", entry.above_text)
            above_text.configure(state="disabled")
        
        if entry.below_text:
            ctk.CTkLabel(
                context_section,
                text="下文:",
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_secondary"],
            ).pack(anchor="w", padx=20, pady=(5, 2))
            
            below_text = ctk.CTkTextbox(context_section, height=80, wrap="word")
            below_text.pack(fill="x", padx=20, pady=(0, 15))
            below_text.insert("1.0", entry.below_text)
            below_text.configure(state="disabled")
        
        # 底部操作栏
        footer = ctk.CTkFrame(panel, fg_color=COLORS["surface"], height=70)
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_propagate(False)
        
        footer_btns = ctk.CTkFrame(footer, fg_color="transparent")
        footer_btns.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkButton(
            footer_btns,
            text="⬅️ 上一张",
            width=110,
            height=40,
            fg_color="transparent",
            border_width=2,
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            footer_btns,
            text="⏭️ 跳过",
            width=100,
            height=40,
            fg_color=COLORS["warning"],
            command=lambda: (entry.skip_var.set(True) if entry.skip_var else None, panel.destroy()),
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            footer_btns,
            text="✅ 应用并继续",
            width=140,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["success"],
            command=panel.destroy,
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            footer_btns,
            text="下一张 ➡️",
            width=110,
            height=40,
            fg_color="transparent",
            border_width=2,
        ).pack(side="left", padx=5)
    
    # ================================================================
    # 预设回调
    # ================================================================
    
    def _on_ai_preset_changed(self, value: str) -> None:
        """AI预设改变"""
        for preset in self.presets["ai"]:
            if preset["name"] == value:
                self.model_var.set(preset["model"])
                self._log(f"🤖 AI模型: {preset['model']}")
                break
    
    def _on_naming_preset_changed(self, value: str) -> None:
        """命名预设改变"""
        for preset in self.presets["naming"]:
            if preset["name"] == value:
                self.template_var.set(preset["template"])
                self._log(f"📝 命名模板: {preset['template']}")
                break
    
    def _on_runtime_preset_changed(self, value: str) -> None:
        """运行选项预设改变"""
        for preset in self.presets["runtime"]:
            if preset["name"] == value:
                self.use_vision_var.set(preset["use_vision"])
                self._log(f"⚙️ 运行模式: {preset['name']}")
                break
    
    # ================================================================
    # 设置对话框
    # ================================================================
    
    def _open_settings(self) -> None:
        """打开预设管理对话框（完全匹配Figma设计）"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("预设管理")
        dialog.geometry("900x750")
        dialog.transient(self)
        
        # 顶部工具栏
        toolbar = ctk.CTkFrame(dialog, fg_color=COLORS["surface"], height=50)
        toolbar.pack(fill="x", padx=0, pady=0)
        toolbar.pack_propagate(False)
        
        ctk.CTkLabel(
            toolbar,
            text="预设管理",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(side="left", padx=25, pady=10)
        
        # 右侧工具按钮
        toolbar_btns = ctk.CTkFrame(toolbar, fg_color="transparent")
        toolbar_btns.pack(side="right", padx=25, pady=10)
        
        ctk.CTkButton(
            toolbar_btns,
            text="✕",
            command=dialog.destroy,
            width=40,
            height=32,
            fg_color="transparent",
            text_color=COLORS["text"],
            hover_color=COLORS["surface_dark"],
        ).pack(side="right", padx=3)
        
        ctk.CTkButton(
            toolbar_btns,
            text="🔄 重置全部",
            width=100,
            height=32,
            fg_color="transparent",
            text_color=COLORS["text"],
            hover_color=COLORS["surface_dark"],
            border_width=1,
            border_color=COLORS["border"],
        ).pack(side="right", padx=3)
        
        ctk.CTkButton(
            toolbar_btns,
            text="📥 导入",
            width=80,
            height=32,
            fg_color="transparent",
            text_color=COLORS["text"],
            hover_color=COLORS["surface_dark"],
            border_width=1,
            border_color=COLORS["border"],
        ).pack(side="right", padx=3)
        
        ctk.CTkButton(
            toolbar_btns,
            text="📤 导出",
            width=80,
            height=32,
            fg_color="transparent",
            text_color=COLORS["text"],
            hover_color=COLORS["surface_dark"],
            border_width=1,
            border_color=COLORS["border"],
        ).pack(side="right", padx=3)
        
        # 主标签页
        tabview = ctk.CTkTabview(dialog)
        tabview.pack(fill="both", expand=True, padx=0, pady=0)
        
        # ⚙️ AI 模型标签页
        api_tab = tabview.add("⚙️ AI 模型")
        self._build_ai_model_tab(api_tab)
        
        # 📋 命名规则标签页
        naming_tab = tabview.add("📋 命名规则")
        self._build_naming_tab(naming_tab)
        
        # ⚡ 运行选项标签页
        runtime_tab = tabview.add("⚡运行选项")
        self._build_runtime_tab(runtime_tab)
    
    def _build_ai_model_tab(self, parent) -> None:
        """构建 AI 模型配置标签页"""
        # 顶部预设选择和操作栏
        preset_bar = ctk.CTkFrame(parent, fg_color=COLORS["surface"], height=60)
        preset_bar.pack(fill="x", padx=20, pady=(15, 10))
        preset_bar.pack_propagate(False)
        
        # 预设选择下拉
        preset_selector = ctk.CTkOptionMenu(
            preset_bar,
            values=["Siliconflow - Qwen", "GPT-4o", "GPT-4o Mini", "Claude 3.5"],
            width=200,
            height=36,
        )
        preset_selector.pack(side="left", padx=15, pady=12)
        
        # 操作按钮组
        ctk.CTkButton(
            preset_bar,
            text="🗑️ 删除",
            width=80,
            height=36,
            fg_color="transparent",
            text_color=COLORS["text"],
            border_width=1,
            border_color=COLORS["border"],
        ).pack(side="right", padx=5, pady=12)
        
        ctk.CTkButton(
            preset_bar,
            text="📋 复制",
            width=80,
            height=36,
            fg_color="transparent",
            text_color=COLORS["text"],
            border_width=1,
            border_color=COLORS["border"],
        ).pack(side="right", padx=5, pady=12)
        
        ctk.CTkButton(
            preset_bar,
            text="➕ 另存为...",
            width=100,
            height=36,
            fg_color="transparent",
            text_color=COLORS["text"],
            border_width=1,
            border_color=COLORS["border"],
        ).pack(side="right", padx=5, pady=12)
        
        ctk.CTkButton(
            preset_bar,
            text="💾 保存",
            width=80,
            height=36,
            fg_color=COLORS["primary"],
            command=self._save_config,
        ).pack(side="right", padx=5, pady=12)
        
        # 滚动内容区
        content = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # 预设名称
        ctk.CTkLabel(content, text="预设名称", anchor="w", font=ctk.CTkFont(size=12)).pack(fill="x", pady=(10, 5))
        ctk.CTkEntry(content, placeholder_text="Siliconflow - Qwen", height=36).pack(fill="x", pady=(0, 15))
        
        # API 类型子标签
        api_type_tabs = ctk.CTkSegmentedButton(
            content,
            values=["主 API", "翻译 API", "摘要 API"],
            height=36,
        )
        api_type_tabs.pack(fill="x", pady=(0, 20))
        api_type_tabs.set("主 API")
        
        # Base URL
        ctk.CTkLabel(content, text="Base URL", anchor="w", font=ctk.CTkFont(size=12)).pack(fill="x", pady=(0, 5))
        ctk.CTkEntry(content, textvariable=self.base_url_var, height=36).pack(fill="x", pady=(0, 15))
        
        # API Key
        ctk.CTkLabel(content, text="API Key", anchor="w", font=ctk.CTkFont(size=12)).pack(fill="x", pady=(0, 5))
        ctk.CTkEntry(content, textvariable=self.api_key_var, placeholder_text="sk-...", show="*", height=36).pack(fill="x", pady=(0, 15))
        
        # 模型
        ctk.CTkLabel(content, text="模型", anchor="w", font=ctk.CTkFont(size=12)).pack(fill="x", pady=(0, 5))
        ctk.CTkEntry(content, textvariable=self.model_var, height=36).pack(fill="x", pady=(0, 15))
        
        # 系统提示词
        ctk.CTkLabel(content, text="系统提示词", anchor="w", font=ctk.CTkFont(size=12)).pack(fill="x", pady=(0, 5))
        system_prompt = ctk.CTkTextbox(content, height=100)
        system_prompt.pack(fill="x", pady=(0, 15))
        system_prompt.insert("1.0", "You are an AI assistant that helps name images based on their content and context.")
        
        # 测试连接按钮
        test_btn = ctk.CTkButton(
            content,
            text="⚙️ 测试连接",
            height=36,
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text"],
        )
        test_btn.pack(fill="x", pady=(0, 20))
        
        # 参数设置（两列布局）
        params_frame = ctk.CTkFrame(content, fg_color="transparent")
        params_frame.pack(fill="x", pady=(0, 15))
        params_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Temperature
        temp_frame = ctk.CTkFrame(params_frame, fg_color="transparent")
        temp_frame.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ctk.CTkLabel(temp_frame, text="Temperature", anchor="w", font=ctk.CTkFont(size=12)).pack(fill="x", pady=(0, 5))
        ctk.CTkEntry(temp_frame, textvariable=self.temperature_var, height=36).pack(fill="x")
        
        # 最大令牌数
        tokens_frame = ctk.CTkFrame(params_frame, fg_color="transparent")
        tokens_frame.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        ctk.CTkLabel(tokens_frame, text="最大令牌数", anchor="w", font=ctk.CTkFont(size=12)).pack(fill="x", pady=(0, 5))
        ctk.CTkEntry(tokens_frame, textvariable=self.max_tokens_var, height=36).pack(fill="x")
    
    def _build_naming_tab(self, parent) -> None:
        """构建命名规则标签页"""
        # 顶部预设选择栏
        preset_bar = ctk.CTkFrame(parent, fg_color=COLORS["surface"], height=60)
        preset_bar.pack(fill="x", padx=20, pady=(15, 10))
        preset_bar.pack_propagate(False)
        
        preset_selector = ctk.CTkOptionMenu(
            preset_bar,
            values=["标题_序号_图意", "段落_图意", "仅图意"],
            width=200,
            height=36,
        )
        preset_selector.pack(side="left", padx=15, pady=12)
        
        ctk.CTkButton(
            preset_bar,
            text="💾 保存",
            width=80,
            height=36,
            fg_color=COLORS["primary"],
            command=self._save_config,
        ).pack(side="right", padx=5, pady=12)
        
        # 内容区
        content = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        ctk.CTkLabel(content, text="命名模板", anchor="w", font=ctk.CTkFont(size=12)).pack(fill="x", pady=(10, 5))
        ctk.CTkEntry(content, textvariable=self.template_var, height=36).pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(
            content,
            text="可用占位符: {title} {index} {intent} {block} {idx}",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"]
        ).pack(fill="x", pady=(0, 15))
        
        # 示例
        ctk.CTkLabel(content, text="示例", anchor="w", font=ctk.CTkFont(size=12, weight="bold")).pack(fill="x", pady=(10, 5))
        example_frame = ctk.CTkFrame(content, fg_color=COLORS["surface"])
        example_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(
            example_frame,
            text='输入: {title}_{index:02d}_{intent}\n输出: 文档标题_01_图片描述',
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
            justify="left",
        ).pack(padx=15, pady=15, anchor="w")
    
    def _build_runtime_tab(self, parent) -> None:
        """构建运行选项标签页"""
        # 顶部预设选择栏
        preset_bar = ctk.CTkFrame(parent, fg_color=COLORS["surface"], height=60)
        preset_bar.pack(fill="x", padx=20, pady=(15, 10))
        preset_bar.pack_propagate(False)
        
        preset_selector = ctk.CTkOptionMenu(
            preset_bar,
            values=["安全模式", "标准模式", "视觉增强"],
            width=200,
            height=36,
        )
        preset_selector.pack(side="left", padx=15, pady=12)
        
        ctk.CTkButton(
            preset_bar,
            text="💾 保存",
            width=80,
            height=36,
            fg_color=COLORS["primary"],
            command=self._save_config,
        ).pack(side="right", padx=5, pady=12)
        
        # 内容区
        content = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        ctk.CTkLabel(content, text="附件目录", anchor="w", font=ctk.CTkFont(size=12)).pack(fill="x", pady=(10, 5))
        ctk.CTkEntry(content, textvariable=self.attach_dir_var, height=36).pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(content, text="功能选项", anchor="w", font=ctk.CTkFont(size=12, weight="bold")).pack(fill="x", pady=(10, 10))
        
        ctk.CTkSwitch(content, text="启用视觉识别（使用图片内容）", variable=self.use_vision_var).pack(fill="x", padx=10, pady=8)
        ctk.CTkSwitch(content, text="跳过已存在的文件", variable=self.skip_existing_var).pack(fill="x", padx=10, pady=8)
        ctk.CTkSwitch(content, text="预览模式（不写入文件）", variable=self.dry_run_var).pack(fill="x", padx=10, pady=8)
        ctk.CTkSwitch(content, text="详细日志输出", variable=self.verbose_var).pack(fill="x", padx=10, pady=8)
    
    def _show_find_replace(self) -> None:
        """显示查找替换对话框"""
        messagebox.showinfo("提示", "查找替换功能开发中...")
    
    def _show_help(self) -> None:
        """显示帮助信息"""
        messagebox.showinfo(
            "帮助",
            "AI 图片命名器\n\n"
            "使用步骤:\n"
            '1. 点击左侧"添加文件"按钮，选择 Markdown 文件\n'
            "2. 从列表中点击选择一个文件\n"
            '3. 点击"批量预览"按钮，系统将分析所有图片\n'
            "4. 复审每张图片的命名意图，可手动修改\n"
            '5. 确认无误后点击"批量写回"应用更改'
        )
    
    # ================================================================
    # 配置管理
    # ================================================================
    
    def _load_config(self) -> None:
        """加载配置文件"""
        if not PROFILES_PATH.exists():
            return
        
        try:
            with open(PROFILES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "default" in data:
                    default = data["default"]
                    self.base_url_var.set(default.get("base_url", ""))
                    self.api_key_var.set(default.get("api_key", ""))
                    self.model_var.set(default.get("model", "gpt-4o-mini"))
        except Exception as e:
            print(f"加载配置失败: {e}")
    
    def _save_config(self) -> None:
        """保存配置文件"""
        try:
            data = {
                "default": {
                    "base_url": self.base_url_var.get(),
                    "api_key": self.api_key_var.get(),
                    "model": self.model_var.get(),
                    "temperature": self.temperature_var.get(),
                    "max_tokens": self.max_tokens_var.get(),
                    "timeout": self.timeout_var.get(),
                    "name_template": self.template_var.get(),
                    "attach_dir": self.attach_dir_var.get(),
                }
            }
            
            with open(PROFILES_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self._log("✅ 配置已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {e}")
    
    # ================================================================
    # 辅助方法
    # ================================================================
    
    def _log(self, message: str) -> None:
        """添加日志消息"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.status_label.configure(text=message)
    
    def _update_stats(self) -> None:
        """更新统计信息显示"""
        dirs = self.stats_dirs.get()
        llm = self.stats_llm_calls.get()
        tokens = self.stats_tokens.get()
        self.stats_label.configure(
            text=f"目录: {dirs}  |  LLM 调用: {llm}  |  Tokens: {tokens:,}"
        )


def main() -> None:
    """主函数"""
    app = FigmaStyleApp()
    app.mainloop()


if __name__ == "__main__":
    main()
