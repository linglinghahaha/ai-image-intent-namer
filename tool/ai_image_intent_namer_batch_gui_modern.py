#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 图片"图意"命名器 - 现代化批量 GUI
基于 CustomTkinter 的现代化界面设计
"""

from __future__ import annotations
import json
import os
import re
import sys
import threading
import tkinter as tk
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog

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
    )
except Exception as e:
    print("❌ 无法导入后端模块 ai_image_intent_namer.py")
    print("错误:", e)
    sys.exit(1)

# 常量定义
APP_TITLE = "AI 图片命名器 · 现代化界面"
PROFILES_PATH = TOOL_DIR / "ai_image_intent_namer_gui.profiles.json"
TEMPLATE_PRESETS_PATH = TOOL_DIR / "ai_image_intent_namer_gui.templates.json"
DEFAULT_NAME_TEMPLATE = "{title}_{index:02d}_{intent}"
DEFAULT_ATTACH_DIR = "attachments"

# 颜色主题 (参考Figma设计)
COLORS = {
    "primary": "#2563eb",      # 蓝色主题
    "primary_hover": "#1d4ed8",
    "success": "#16a34a",      # 成功绿色
    "warning": "#ea580c",      # 警告橙色
    "error": "#dc2626",        # 错误红色
    "background": "#ffffff",   # 背景白色
    "surface": "#f8fafc",      # 卡片背景
    "border": "#e2e8f0",       # 边框颜色
    "text": "#0f172a",         # 文本颜色
    "text_secondary": "#64748b", # 次要文本
}

# 设置 CustomTkinter 主题
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


@dataclass
class ItemUI:
    """单个图片项的UI数据"""
    index: int
    block_index: int
    image_index: int
    src: str
    above_text: str
    below_text: str
    between_text: str
    alt: Optional[str]
    title_attr: Optional[str]
    frame: ctk.CTkFrame
    intent_var: tk.StringVar
    final_var: tk.StringVar
    apply_btn: ctk.CTkButton
    skip_var: tk.BooleanVar
    skip_check: ctk.CTkCheckBox
    intent_entry: Optional[ctk.CTkEntry] = None
    thumbnail_label: Optional[ctk.CTkLabel] = None


@dataclass
class TabState:
    """标签页状态"""
    md_path: Path
    title: str
    results: Dict
    page: ctk.CTkFrame
    canvas: tk.Canvas
    inner_frame: ctk.CTkFrame
    scrollbar: ctk.CTkScrollbar
    item_uis: List[ItemUI]
    btn_refresh: ctk.CTkButton
    btn_apply_all: ctk.CTkButton
    btn_close: ctk.CTkButton
    recalc_job: Optional[str] = None
    processing: bool = False
    completed: bool = False


class ModernBatchApp(ctk.CTk):
    """现代化批量处理应用"""
    
    def __init__(self) -> None:
        super().__init__()
        
        # 窗口基本设置
        self.title(APP_TITLE)
        self.geometry("1400x850")
        self.minsize(1200, 700)
        
        # 状态变量
        self.files: List[Path] = []
        self.stop_flag = False
        self.tabs: Dict[str, TabState] = {}
        self.profiles: Dict[str, Dict] = {}
        
        # UI变量
        self.ui_language_var = tk.StringVar(value="zh")
        self.intent_language_var = tk.StringVar(value="auto")
        self.template_var = tk.StringVar(value=DEFAULT_NAME_TEMPLATE)
        self.template_preset_var = tk.StringVar(value="标题_全局序号_图意")
        
        # API配置变量
        self.base_url_var = tk.StringVar(value="https://api.openai.com/v1")
        self.api_key_var = tk.StringVar(value="")
        self.model_var = tk.StringVar(value="gpt-4o-mini")
        self.temperature_var = tk.DoubleVar(value=0.3)
        self.max_tokens_var = tk.IntVar(value=150)
        
        # 运行选项
        self.attach_dir_var = tk.StringVar(value=DEFAULT_ATTACH_DIR)
        self.use_vision_var = tk.BooleanVar(value=False)
        self.skip_existing_var = tk.BooleanVar(value=False)
        self.dry_run_var = tk.BooleanVar(value=True)
        
        # 状态变量
        self.status_var = tk.StringVar(value="准备就绪")
        self.progress_var = tk.DoubleVar(value=0.0)
        
        # 模板预设
        self.template_presets: Dict[str, Dict[str, str]] = {}
        self._load_template_presets()
        
        # 构建界面
        self._build_ui()
        
        # 加载配置
        self._load_profiles()
    
    def _build_ui(self) -> None:
        """构建现代化UI界面"""
        
        # 使用grid布局划分主要区域
        self.grid_columnconfigure(0, weight=0, minsize=300)  # 左侧边栏
        self.grid_columnconfigure(1, weight=1)               # 主内容区
        self.grid_rowconfigure(0, weight=0)                  # 顶部栏
        self.grid_rowconfigure(1, weight=1)                  # 内容区
        self.grid_rowconfigure(2, weight=0)                  # 状态栏
        
        # 1. 顶部应用栏
        self._build_app_bar()
        
        # 2. 左侧边栏
        self._build_sidebar()
        
        # 3. 主内容区
        self._build_main_content()
        
        # 4. 底部状态栏
        self._build_status_bar()
    
    def _build_app_bar(self) -> None:
        """构建顶部应用栏"""
        app_bar = ctk.CTkFrame(self, height=60, corner_radius=0)
        app_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        app_bar.grid_columnconfigure(1, weight=1)
        
        # 应用标题和图标
        title_frame = ctk.CTkFrame(app_bar, fg_color="transparent")
        title_frame.grid(row=0, column=0, padx=20, pady=10, sticky="w")
        
        title_label = ctk.CTkLabel(
            title_frame,
            text="🎨 AI 图片命名器",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title_label.pack(side="left")
        
        subtitle = ctk.CTkLabel(
            title_frame,
            text="批量智能处理 · 快速生成命名",
            font=ctk.CTkFont(size=12),
            text_color="gray50"
        )
        subtitle.pack(side="left", padx=10)
        
        # 右侧操作按钮
        actions_frame = ctk.CTkFrame(app_bar, fg_color="transparent")
        actions_frame.grid(row=0, column=1, padx=20, pady=10, sticky="e")
        
        # 设置按钮
        settings_btn = ctk.CTkButton(
            actions_frame,
            text="⚙️ 设置",
            width=100,
            command=self._open_settings_dialog,
        )
        settings_btn.pack(side="right", padx=5)
        
        # 帮助按钮
        help_btn = ctk.CTkButton(
            actions_frame,
            text="❓ 帮助",
            width=100,
            fg_color="transparent",
            border_width=2,
            command=self._show_help,
        )
        help_btn.pack(side="right", padx=5)
    
    def _build_sidebar(self) -> None:
        """构建左侧边栏（文件列表区）"""
        sidebar = ctk.CTkFrame(self, corner_radius=0)
        sidebar.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        sidebar.grid_rowconfigure(2, weight=1)
        
        # 文件列表标题
        list_header = ctk.CTkFrame(sidebar)
        list_header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))
        list_header.grid_columnconfigure(0, weight=1)
        
        list_title = ctk.CTkLabel(
            list_header,
            text="📁 文档列表",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        list_title.grid(row=0, column=0, sticky="w")
        
        file_count = ctk.CTkLabel(
            list_header,
            text="0 个文件",
            font=ctk.CTkFont(size=12),
            text_color="gray50"
        )
        file_count.grid(row=1, column=0, sticky="w", pady=(5, 0))
        self.file_count_label = file_count
        
        # 文件操作按钮组
        btn_frame = ctk.CTkFrame(sidebar)
        btn_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        btn_frame.grid_columnconfigure((0, 1), weight=1)
        
        add_btn = ctk.CTkButton(
            btn_frame,
            text="➕ 添加",
            command=self._on_add_files,
            height=35,
        )
        add_btn.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        
        remove_btn = ctk.CTkButton(
            btn_frame,
            text="🗑️ 移除",
            command=self._on_remove_selected,
            fg_color="transparent",
            border_width=2,
            height=35,
        )
        remove_btn.grid(row=0, column=1, padx=(5, 0), sticky="ew")
        
        clear_btn = ctk.CTkButton(
            btn_frame,
            text="清空列表",
            command=self._on_clear_list,
            fg_color="transparent",
            text_color="gray50",
            hover_color=("gray90", "gray20"),
            height=30,
        )
        clear_btn.grid(row=1, column=0, columnspan=2, pady=(10, 0), sticky="ew")
        
        # 文件列表（可滚动）
        list_frame = ctk.CTkFrame(sidebar)
        list_frame.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 15))
        
        self.file_listbox = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,
            font=("Microsoft YaHei", 10),
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            bg="#f8fafc",
        )
        self.file_listbox.pack(fill=tk.BOTH, expand=True)
        
        # 批量操作区
        batch_frame = ctk.CTkFrame(sidebar)
        batch_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 15))
        
        batch_title = ctk.CTkLabel(
            batch_frame,
            text="批量操作",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        batch_title.pack(fill="x", padx=10, pady=(10, 5))
        
        preview_btn = ctk.CTkButton(
            batch_frame,
            text="▶️ 批量预览",
            command=self._on_batch_preview,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        preview_btn.pack(fill="x", padx=10, pady=5)
        self.preview_btn = preview_btn
        
        stop_btn = ctk.CTkButton(
            batch_frame,
            text="⏸️ 停止",
            command=self._on_stop,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            height=35,
            state="disabled",
        )
        stop_btn.pack(fill="x", padx=10, pady=(5, 10))
        self.stop_btn = stop_btn
    
    def _build_main_content(self) -> None:
        """构建主内容区（标签页）"""
        main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        main_container.grid(row=1, column=1, sticky="nsew", padx=15, pady=15)
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=1)
        
        # 创建标签页控件
        self.notebook = ctk.CTkTabview(main_container)
        self.notebook.pack(fill="both", expand=True)
        
        # 添加欢迎标签
        welcome_tab = self.notebook.add("开始使用")
        self._build_welcome_page(welcome_tab)
    
    def _build_welcome_page(self, parent: ctk.CTkFrame) -> None:
        """构建欢迎页面"""
        # 居中容器
        center_frame = ctk.CTkFrame(parent, fg_color="transparent")
        center_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # 欢迎标题
        welcome_title = ctk.CTkLabel(
            center_frame,
            text="👋 欢迎使用 AI 图片命名器",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        welcome_title.pack(pady=(0, 20))
        
        # 说明文字
        desc_text = (
            "这是一个基于 AI 的智能图片命名工具\n\n"
            "✨ 自动分析上下文生成图片意图\n"
            "🎯 支持批量处理多个 Markdown 文档\n"
            "🔄 灵活的命名模板和预设管理\n"
            "👀 可视化审核界面，精确控制\n\n"
            "请从左侧添加 Markdown 文件开始"
        )
        
        desc_label = ctk.CTkLabel(
            center_frame,
            text=desc_text,
            font=ctk.CTkFont(size=14),
            justify="center",
            text_color="gray40"
        )
        desc_label.pack(pady=(0, 30))
        
        # 快速开始按钮
        quick_start_btn = ctk.CTkButton(
            center_frame,
            text="🚀 快速开始",
            command=self._on_add_files,
            width=200,
            height=45,
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        quick_start_btn.pack(pady=10)
        
        # 文档链接
        docs_btn = ctk.CTkButton(
            center_frame,
            text="📖 查看文档",
            command=self._show_help,
            width=200,
            height=35,
            fg_color="transparent",
            border_width=2,
        )
        docs_btn.pack(pady=5)
    
    def _build_status_bar(self) -> None:
        """构建底部状态栏"""
        status_bar = ctk.CTkFrame(self, height=40, corner_radius=0)
        status_bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        status_bar.grid_columnconfigure(0, weight=1)
        
        # 状态文本
        status_label = ctk.CTkLabel(
            status_bar,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=11),
            anchor="w"
        )
        status_label.grid(row=0, column=0, padx=20, sticky="w")
        
        # 进度条
        self.progress_bar = ctk.CTkProgressBar(
            status_bar,
            width=200,
            height=10,
            variable=self.progress_var,
        )
        self.progress_bar.grid(row=0, column=1, padx=20, sticky="e")
        self.progress_bar.set(0)
    
    # ================================================================
    # 文件操作
    # ================================================================
    
    def _on_add_files(self) -> None:
        """添加文件"""
        file_paths = filedialog.askopenfilenames(
            title="选择 Markdown 文件",
            filetypes=[("Markdown files", "*.md *.markdown"), ("All files", "*.*")]
        )
        
        if not file_paths:
            return
        
        for path_str in file_paths:
            path = Path(path_str)
            if path not in self.files:
                self.files.append(path)
                self.file_listbox.insert(tk.END, path.name)
        
        self._update_file_count()
        self._set_status(f"已添加 {len(file_paths)} 个文件")
    
    def _on_remove_selected(self) -> None:
        """移除选中的文件"""
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要移除的文件")
            return
        
        # 从后往前删除，避免索引混乱
        for index in reversed(selection):
            self.files.pop(index)
            self.file_listbox.delete(index)
        
        self._update_file_count()
        self._set_status(f"已移除 {len(selection)} 个文件")
    
    def _on_clear_list(self) -> None:
        """清空文件列表"""
        if not self.files:
            return
        
        if messagebox.askyesno("确认", "确定要清空所有文件吗？"):
            self.files.clear()
            self.file_listbox.delete(0, tk.END)
            self._update_file_count()
            self._set_status("已清空文件列表")
    
    def _update_file_count(self) -> None:
        """更新文件计数"""
        count = len(self.files)
        self.file_count_label.configure(text=f"{count} 个文件")
    
    # ================================================================
    # 批量处理
    # ================================================================
    
    def _on_batch_preview(self) -> None:
        """批量预览"""
        if not self.files:
            messagebox.showwarning("提示", "请先添加 Markdown 文件")
            return
        
        self.stop_flag = False
        self.preview_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        
        # 在后台线程中处理
        thread = threading.Thread(target=self._batch_preview_worker, daemon=True)
        thread.start()
    
    def _batch_preview_worker(self) -> None:
        """批量预览工作线程"""
        total = len(self.files)
        
        for i, md_path in enumerate(self.files):
            if self.stop_flag:
                self._log_async("⏸️ 用户中止处理")
                break
            
            try:
                # 更新进度
                progress = (i + 1) / total
                self.after(0, lambda p=progress: self.progress_var.set(p))
                self.after(0, lambda p=md_path: self._set_status(f"正在处理: {p.name}"))
                
                # 处理文件
                cfg = self._gather_config("preview")
                self._process_file_in_worker(md_path, cfg)
                
            except Exception as e:
                error_msg = f"❌ 处理 {md_path.name} 时出错: {e}"
                self._log_async(error_msg)
        
        # 完成
        self.after(0, self._batch_complete)
    
    def _process_file_in_worker(self, md_path: Path, cfg: Config) -> None:
        """在工作线程中处理单个文件"""
        try:
            # 读取文档
            text = read_text(md_path)
            title = extract_doc_title(text)
            
            # 提取图片信息
            images = collect_images(text)
            
            if not images:
                self._log_async(f"⚠️ {md_path.name} 中未找到图片")
                return
            
            # 准备标签页
            self.after(0, lambda: self._prepare_processing_tab(md_path, title))
            
            # 处理每张图片
            results = []
            for idx, img_info in enumerate(images):
                if self.stop_flag:
                    break
                
                # 查找上下文
                above, below, between = find_neighbor_text(text, img_info["line_no"])
                
                # 构建结果
                item = {
                    "index": idx + 1,
                    "src": img_info["src"],
                    "alt": img_info.get("alt"),
                    "title": img_info.get("title"),
                    "above_text": above,
                    "below_text": below,
                    "between_text": between,
                    "intent": "",
                    "candidates": [],
                }
                
                results.append(item)
                
                # 添加到UI
                self.after(0, lambda t=title, r=item, i=idx: 
                          self._append_processing_item(md_path, t, r, i))
            
            # 保存结果
            tab_results = {
                "title": title,
                "images": results,
            }
            
            self.after(0, lambda: self._apply_preview_results(md_path, text, tab_results))
            self._log_async(f"✅ {md_path.name} 处理完成，共 {len(results)} 张图片")
            
        except Exception as e:
            self._log_async(f"❌ 处理 {md_path.name} 失败: {e}")
    
    def _batch_complete(self) -> None:
        """批量处理完成"""
        self.preview_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress_var.set(0)
        self._set_status("✅ 批量处理完成")
    
    def _on_stop(self) -> None:
        """停止处理"""
        self.stop_flag = True
        self._set_status("正在停止...")
    
    # ================================================================
    # 标签页管理
    # ================================================================
    
    def _prepare_processing_tab(self, md_path: Path, title: str) -> None:
        """准备处理标签页"""
        tab_id = str(md_path)
        
        # 如果标签已存在，先删除
        if tab_id in self.tabs:
            self._close_tab(md_path)
        
        # 创建新标签
        tab_state = self._create_tab(md_path, title)
        self.tabs[tab_id] = tab_state
    
    def _create_tab(self, md_path: Path, title: str) -> TabState:
        """创建标签页"""
        tab_name = md_path.stem
        tab_frame = self.notebook.add(tab_name)
        
        # 创建滚动区域
        canvas = tk.Canvas(tab_frame, bg="#ffffff", highlightthickness=0)
        scrollbar = ctk.CTkScrollbar(tab_frame, command=canvas.yview)
        inner_frame = ctk.CTkFrame(canvas, fg_color="transparent")
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        canvas_window = canvas.create_window((0, 0), window=inner_frame, anchor="nw")
        
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_window, width=event.width)
        
        inner_frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
        
        # 创建底部按钮栏
        bottom_frame = ctk.CTkFrame(tab_frame)
        bottom_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        
        btn_refresh = ctk.CTkButton(
            bottom_frame,
            text="🔄 刷新",
            width=120,
            command=lambda: self._refresh_tab(md_path),
        )
        btn_refresh.pack(side="left", padx=5)
        
        btn_apply_all = ctk.CTkButton(
            bottom_frame,
            text="✅ 全部应用",
            width=120,
            fg_color="#16a34a",
            hover_color="#15803d",
            command=lambda: self._apply_all_in_tab(md_path),
        )
        btn_apply_all.pack(side="left", padx=5)
        
        btn_close = ctk.CTkButton(
            bottom_frame,
            text="❌ 关闭",
            width=120,
            fg_color="transparent",
            border_width=2,
            command=lambda: self._close_tab(md_path),
        )
        btn_close.pack(side="right", padx=5)
        
        tab_state = TabState(
            md_path=md_path,
            title=title,
            results={},
            page=tab_frame,
            canvas=canvas,
            inner_frame=inner_frame,
            scrollbar=scrollbar,
            item_uis=[],
            btn_refresh=btn_refresh,
            btn_apply_all=btn_apply_all,
            btn_close=btn_close,
        )
        
        return tab_state
    
    def _append_processing_item(self, md_path: Path, title: str, item: Dict, index: Optional[int]) -> None:
        """添加处理项到标签页"""
        tab_id = str(md_path)
        tab = self.tabs.get(tab_id)
        
        if not tab:
            return
        
        # 创建图片卡片
        card = ctk.CTkFrame(tab.inner_frame, corner_radius=10)
        card.pack(fill="x", padx=10, pady=5)
        
        # 卡片头部
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 10))
        
        index_label = ctk.CTkLabel(
            header,
            text=f"#{item['index']}",
            font=ctk.CTkFont(size=16, weight="bold"),
            width=50,
        )
        index_label.pack(side="left")
        
        src_label = ctk.CTkLabel(
            header,
            text=item['src'][:60] + "..." if len(item['src']) > 60 else item['src'],
            font=ctk.CTkFont(size=11),
            text_color="gray50",
        )
        src_label.pack(side="left", padx=10)
        
        # 跳过复选框
        skip_var = tk.BooleanVar(value=False)
        skip_check = ctk.CTkCheckBox(
            header,
            text="跳过",
            variable=skip_var,
        )
        skip_check.pack(side="right")
        
        # 意图输入
        intent_frame = ctk.CTkFrame(card, fg_color="transparent")
        intent_frame.pack(fill="x", padx=15, pady=10)
        
        intent_label = ctk.CTkLabel(
            intent_frame,
            text="图意:",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=50,
            anchor="w",
        )
        intent_label.pack(side="left")
        
        intent_var = tk.StringVar(value="")
        intent_entry = ctk.CTkEntry(
            intent_frame,
            textvariable=intent_var,
            placeholder_text="等待生成或手动输入...",
        )
        intent_entry.pack(side="left", fill="x", expand=True, padx=10)
        
        # 最终文件名
        final_frame = ctk.CTkFrame(card, fg_color="transparent")
        final_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        final_label = ctk.CTkLabel(
            final_frame,
            text="命名:",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=50,
            anchor="w",
        )
        final_label.pack(side="left")
        
        final_var = tk.StringVar(value=item['src'])
        final_display = ctk.CTkLabel(
            final_frame,
            textvariable=final_var,
            font=ctk.CTkFont(size=11),
            anchor="w",
        )
        final_display.pack(side="left", fill="x", expand=True, padx=10)
        
        # 操作按钮
        action_frame = ctk.CTkFrame(card, fg_color="transparent")
        action_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        apply_btn = ctk.CTkButton(
            action_frame,
            text="✅ 应用",
            width=100,
            height=30,
            fg_color="#16a34a",
            hover_color="#15803d",
        )
        apply_btn.pack(side="right", padx=5)
        
        # 创建 ItemUI
        item_ui = ItemUI(
            index=item['index'],
            block_index=0,
            image_index=item['index'],
            src=item['src'],
            above_text=item.get('above_text', ''),
            below_text=item.get('below_text', ''),
            between_text=item.get('between_text', ''),
            alt=item.get('alt'),
            title_attr=item.get('title'),
            frame=card,
            intent_var=intent_var,
            final_var=final_var,
            apply_btn=apply_btn,
            skip_var=skip_var,
            skip_check=skip_check,
            intent_entry=intent_entry,
        )
        
        tab.item_uis.append(item_ui)
    
    def _apply_preview_results(self, md_path: Path, text_data: str, results: Dict) -> None:
        """应用预览结果"""
        tab_id = str(md_path)
        tab = self.tabs.get(tab_id)
        
        if tab:
            tab.results = results
            # 重新计算所有命名
            self._recalc_names(tab)
    
    def _close_tab(self, md_path: Path) -> None:
        """关闭标签页"""
        tab_id = str(md_path)
        tab = self.tabs.get(tab_id)
        
        if not tab:
            return
        
        # 删除标签
        tab_name = md_path.stem
        try:
            self.notebook.delete(tab_name)
        except:
            pass
        
        del self.tabs[tab_id]
    
    def _refresh_tab(self, md_path: Path) -> None:
        """刷新标签页"""
        cfg = self._gather_config("preview")
        self.stop_flag = False
        thread = threading.Thread(
            target=self._process_file_in_worker,
            args=(md_path, cfg),
            daemon=True
        )
        thread.start()
        self._set_status(f"正在刷新 {md_path.name}...")
    
    def _apply_all_in_tab(self, md_path: Path) -> None:
        """应用标签页中的所有更改"""
        tab = self.tabs.get(str(md_path))
        if not tab:
            return
        
        # 重算所有命名
        self._recalc_names(tab)
        
        # 收集跳过的和选择的图意
        skip_set: Set[int] = {
            item.index for item in tab.item_uis 
            if item.skip_var.get()
        }
        chosen_map = {
            item.index: sanitize_filename(item.intent_var.get() or "图意")
            for item in tab.item_uis
            if item.index not in skip_set
        }
        
        # 在后台线程执行应用
        thread = threading.Thread(
            target=self._apply_with_overrides,
            args=(tab, chosen_map, skip_set),
            daemon=True
        )
        thread.start()
        self._set_status(f"正在应用更改到 {md_path.name}...")
    
    # ================================================================
    # 配置与设置
    # ================================================================
    
    def _open_settings_dialog(self) -> None:
        """打开设置对话框"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("设置")
        dialog.geometry("700x600")
        dialog.transient(self)
        dialog.grab_set()
        
        # 创建标签页
        tabview = ctk.CTkTabview(dialog)
        tabview.pack(fill="both", expand=True, padx=20, pady=20)
        
        # API设置
        api_tab = tabview.add("API 配置")
        self._build_api_settings(api_tab)
        
        # 命名模板
        template_tab = tabview.add("命名模板")
        self._build_template_settings(template_tab)
        
        # 运行选项
        runtime_tab = tabview.add("运行选项")
        self._build_runtime_settings(runtime_tab)
        
        # 底部按钮
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        save_btn = ctk.CTkButton(
            btn_frame,
            text="💾 保存",
            command=lambda: self._save_settings(dialog),
        )
        save_btn.pack(side="right", padx=5)
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="取消",
            fg_color="transparent",
            border_width=2,
            command=dialog.destroy,
        )
        cancel_btn.pack(side="right", padx=5)
    
    def _build_api_settings(self, parent: ctk.CTkFrame) -> None:
        """构建API设置界面"""
        # Base URL
        url_label = ctk.CTkLabel(parent, text="Base URL:", anchor="w")
        url_label.pack(fill="x", padx=20, pady=(20, 5))
        
        url_entry = ctk.CTkEntry(parent, textvariable=self.base_url_var)
        url_entry.pack(fill="x", padx=20, pady=(0, 15))
        
        # API Key
        key_label = ctk.CTkLabel(parent, text="API Key:", anchor="w")
        key_label.pack(fill="x", padx=20, pady=(0, 5))
        
        key_entry = ctk.CTkEntry(parent, textvariable=self.api_key_var, show="*")
        key_entry.pack(fill="x", padx=20, pady=(0, 15))
        
        # Model
        model_label = ctk.CTkLabel(parent, text="模型:", anchor="w")
        model_label.pack(fill="x", padx=20, pady=(0, 5))
        
        model_entry = ctk.CTkEntry(parent, textvariable=self.model_var)
        model_entry.pack(fill="x", padx=20, pady=(0, 15))
        
        # Temperature
        temp_label = ctk.CTkLabel(parent, text=f"Temperature: {self.temperature_var.get():.1f}", anchor="w")
        temp_label.pack(fill="x", padx=20, pady=(0, 5))
        
        temp_slider = ctk.CTkSlider(
            parent,
            from_=0,
            to=2,
            variable=self.temperature_var,
            command=lambda v: temp_label.configure(text=f"Temperature: {v:.1f}")
        )
        temp_slider.pack(fill="x", padx=20, pady=(0, 15))
        
        # Max Tokens
        tokens_label = ctk.CTkLabel(parent, text="Max Tokens:", anchor="w")
        tokens_label.pack(fill="x", padx=20, pady=(0, 5))
        
        tokens_entry = ctk.CTkEntry(parent, textvariable=self.max_tokens_var)
        tokens_entry.pack(fill="x", padx=20, pady=(0, 15))
        
        # 测试按钮
        test_btn = ctk.CTkButton(
            parent,
            text="🧪 测试连接",
            command=self._test_api_connection,
        )
        test_btn.pack(pady=20)
    
    def _build_template_settings(self, parent: ctk.CTkFrame) -> None:
        """构建模板设置界面"""
        template_label = ctk.CTkLabel(parent, text="命名模板:", anchor="w")
        template_label.pack(fill="x", padx=20, pady=(20, 5))
        
        template_entry = ctk.CTkEntry(parent, textvariable=self.template_var)
        template_entry.pack(fill="x", padx=20, pady=(0, 10))
        
        help_text = (
            "可用占位符:\n"
            "  {title} - 文档标题\n"
            "  {index} - 全局序号\n"
            "  {intent} - AI生成的图意\n"
            "  {block} - 块序号\n"
            "  {idx} - 块内序号"
        )
        
        help_label = ctk.CTkLabel(
            parent,
            text=help_text,
            justify="left",
            font=ctk.CTkFont(size=11),
            text_color="gray50"
        )
        help_label.pack(fill="x", padx=20, pady=10)
    
    def _build_runtime_settings(self, parent: ctk.CTkFrame) -> None:
        """构建运行选项界面"""
        # 附件目录
        attach_label = ctk.CTkLabel(parent, text="附件目录:", anchor="w")
        attach_label.pack(fill="x", padx=20, pady=(20, 5))
        
        attach_entry = ctk.CTkEntry(parent, textvariable=self.attach_dir_var)
        attach_entry.pack(fill="x", padx=20, pady=(0, 15))
        
        # 选项开关
        vision_switch = ctk.CTkSwitch(
            parent,
            text="启用视觉识别",
            variable=self.use_vision_var,
        )
        vision_switch.pack(fill="x", padx=20, pady=10)
        
        skip_switch = ctk.CTkSwitch(
            parent,
            text="跳过已存在的文件",
            variable=self.skip_existing_var,
        )
        skip_switch.pack(fill="x", padx=20, pady=10)
        
        dry_switch = ctk.CTkSwitch(
            parent,
            text="预览模式（不写入文件）",
            variable=self.dry_run_var,
        )
        dry_switch.pack(fill="x", padx=20, pady=10)
    
    def _save_settings(self, dialog: ctk.CTkToplevel) -> None:
        """保存设置"""
        self._save_profiles()
        messagebox.showinfo("提示", "设置已保存")
        dialog.destroy()
    
    def _test_api_connection(self) -> None:
        """测试API连接"""
        messagebox.showinfo("测试", "API连接测试功能待实现")
    
    # ================================================================
    # 配置文件管理
    # ================================================================
    
    def _gather_config(self, mode: str) -> Config:
        """收集当前配置"""
        return Config(
            base_url=self.base_url_var.get(),
            api_key=self.api_key_var.get(),
            model=self.model_var.get(),
            temperature=self.temperature_var.get(),
            max_tokens=self.max_tokens_var.get(),
            name_template=self.template_var.get(),
            attach_dir=self.attach_dir_var.get(),
            use_vision=self.use_vision_var.get(),
            skip_existing=self.skip_existing_var.get(),
            dry_run=self.dry_run_var.get() if mode == "preview" else False,
        )
    
    def _load_profiles(self) -> None:
        """加载配置文件"""
        if not PROFILES_PATH.exists():
            return
        
        try:
            with open(PROFILES_PATH, "r", encoding="utf-8") as f:
                self.profiles = json.load(f)
                
            # 应用默认配置
            if "default" in self.profiles:
                default = self.profiles["default"]
                self.base_url_var.set(default.get("base_url", ""))
                self.api_key_var.set(default.get("api_key", ""))
                self.model_var.set(default.get("model", "gpt-4o-mini"))
                self.template_var.set(default.get("template", DEFAULT_NAME_TEMPLATE))
        except Exception as e:
            print(f"加载配置失败: {e}")
    
    def _save_profiles(self) -> None:
        """保存配置文件"""
        self.profiles["default"] = {
            "base_url": self.base_url_var.get(),
            "api_key": self.api_key_var.get(),
            "model": self.model_var.get(),
            "template": self.template_var.get(),
            "temperature": self.temperature_var.get(),
            "max_tokens": self.max_tokens_var.get(),
        }
        
        try:
            with open(PROFILES_PATH, "w", encoding="utf-8") as f:
                json.dump(self.profiles, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def _load_template_presets(self) -> None:
        """加载模板预设"""
        if not TEMPLATE_PRESETS_PATH.exists():
            # 使用默认预设
            self.template_presets = {
                "标题_全局序号_图意": {
                    "template": "{title}_{index:02d}_{intent}",
                    "description": "标题_全局序号_图意",
                },
                "标题_段内序号_图意": {
                    "template": "{title}_{block:02d}-{idx:02d}_{intent}",
                    "description": "标题_段落序号-段内序号_图意",
                },
            }
            return
        
        try:
            with open(TEMPLATE_PRESETS_PATH, "r", encoding="utf-8") as f:
                self.template_presets = json.load(f)
        except Exception as e:
            print(f"加载模板预设失败: {e}")
    
    # ================================================================
    # 辅助方法
    # ================================================================
    
    def _set_status(self, message: str) -> None:
        """设置状态栏消息"""
        self.status_var.set(message)
    
    def _log_async(self, message: str) -> None:
        """异步日志（从工作线程调用）"""
        self.after(0, lambda: self._set_status(message))
    
    def _show_help(self) -> None:
        """显示帮助"""
        help_text = (
            "AI 图片命名器 - 使用指南\n\n"
            "1. 添加 Markdown 文件\n"
            "2. 配置 API 和命名模板\n"
            "3. 点击批量预览生成命名\n"
            "4. 审核并应用更改\n\n"
            "更多信息请访问项目文档。"
        )
        messagebox.showinfo("帮助", help_text)


def main() -> None:
    """主函数"""
    app = ModernBatchApp()
    app.mainloop()


if __name__ == "__main__":
    main()
