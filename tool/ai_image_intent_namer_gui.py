#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 图片“图意”命名器 - 窗口版（Tkinter）

特性：
- 无需命令行，提供图形界面来选择 Markdown 文件、设置 AI 参数、选择命名策略、预览与应用改名
- 复用核心逻辑（调用 ai_image_intent_namer 模块的能力），在窗口中显示结果与日志
- 提供“预览（不改文件）”、“直接应用（改名/回链，可选下载）”、“交互式应用（逐图挑选候选）”
- Windows/中文友好，支持中文文件名

依赖：
- Python 3.9+
- requests（若需要下载远程图片或调用 AI）
  安装：pip install requests

使用：
- 双击或在终端运行：python tool/ai_image_intent_namer_gui.py
- 在弹出的窗口中选择 Markdown 文件，设置参数，点击“预览”或“应用”

注意：
- 本 GUI 会导入同目录下的 ai_image_intent_namer.py，作为后端逻辑
- 若你移动了该文件，请确保 sys.path 中包含其目录
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 确保可从 `tool` 目录导入后端模块
THIS_FILE = Path(__file__).resolve()
TOOL_DIR = THIS_FILE.parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

# 导入后端能力
try:
    import ai_image_intent_namer as core
    # 引入需要用到的对象/函数
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
        download_image,
    )
except Exception as e:
    print("❌ 无法导入后端模块 ai_image_intent_namer.py，请确认该文件位于同目录。")
    print("错误：", e)
    sys.exit(1)

# Tkinter UI
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog

# 可选依赖：requests（远程图片预览）、Pillow（更多格式预览）
try:
    import requests  # type: ignore
except Exception:
    requests = None

try:
    from PIL import Image, ImageTk  # type: ignore
except Exception:
    Image = None
    ImageTk = None

from io import BytesIO
from urllib.parse import unquote

# 可选：Markdown 远程图片本地化工具
try:
    import md_image_localizer as mil  # type: ignore
    from md_image_localizer import FileProcessor as MILFileProcessor  # type: ignore
except Exception:
    mil = None
    MILFileProcessor = None

# 控制台编码
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

APP_TITLE = "AI 图片“图意”命名器（GUI）"
PROFILES_PATH = TOOL_DIR / "ai_image_intent_namer_gui.profiles.json"

DEFAULT_NAME_TEMPLATE = "{title}_{index:02d}"  # 例：文档标题_01（全局顺序编号，避免重复）

# 规范化 Base URL（用户若误填入 /v1 结尾，避免形成 /v1/v1/chat/completions）
def _normalize_base_url(url: str) -> str:
    u = (url or "").strip()
    if u.endswith("/v1") or u.endswith("/v1/"):
        try:
            u = u[: u.rfind("/v1")]
        except Exception:
            pass
    return u

# 已去重：_normalize_base_url 的重复定义

def getenv_default(name: str, default: str | None = None) -> Optional[str]:
    return os.environ.get(name) if os.environ.get(name) else default

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("980x680")
        self.minsize(960, 640)

        # 状态数据
        self.last_results: Optional[Dict] = None
        self.overrides: Dict[int, str] = {}  # 交互式选择：index -> chosen intent
        self.profiles: Dict[str, Dict] = {}  # 多套 API/策略/模板配置

        # 构建 UI
        self._build_widgets()
        # 加载配置档并刷新下拉
        self._load_profiles()
        # 将窗口置顶显示，避免被遮挡或未前置导致“看不到”
        try:
            self.after(200, self._bring_to_front)
        except Exception:
            pass

    def _build_widgets(self):
        # 顶部文件选择与基础配置
        top = ttk.Frame(self, padding=8)
        top.pack(side=tk.TOP, fill=tk.X)

        # 文件选择
        ttk.Label(top, text="Markdown 文件:").grid(row=0, column=0, sticky="w")
        self.path_var = tk.StringVar()
        entry_path = ttk.Entry(top, textvariable=self.path_var, width=70)
        entry_path.grid(row=0, column=1, sticky="we", padx=4)
        btn_browse = ttk.Button(top, text="浏览...", command=self._on_browse)
        btn_browse.grid(row=0, column=2, padx=2)

        # 附件目录 与 下载
        ttk.Label(top, text="附件目录名:").grid(row=0, column=3, sticky="e", padx=(18, 2))
        self.attach_var = tk.StringVar(value="attachments")
        ttk.Entry(top, textvariable=self.attach_var, width=16).grid(row=0, column=4, sticky="w")
        self.download_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="下载远程图片", variable=self.download_var).grid(row=0, column=5, padx=(12, 0))

        # 策略、模板、序号宽度、文件名长度
        ttk.Label(top, text="策略:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.strategy_var = tk.StringVar(value="intent")
        ttk.Combobox(top, textvariable=self.strategy_var, values=["seq", "above", "below", "between", "intent", "hybrid"], width=10, state="readonly").grid(row=1, column=1, sticky="w", pady=(8, 0))

        ttk.Label(top, text="命名模板:").grid(row=1, column=2, sticky="e", padx=(12, 2), pady=(8, 0))
        self.template_var = tk.StringVar(value=DEFAULT_NAME_TEMPLATE)
        ttk.Entry(top, textvariable=self.template_var, width=40).grid(row=1, column=3, columnspan=2, sticky="we", pady=(8, 0))

        ttk.Label(top, text="序号宽度:").grid(row=1, column=5, sticky="e", padx=(12, 2), pady=(8, 0))
        self.seq_width_var = tk.IntVar(value=2)
        ttk.Spinbox(top, from_=1, to=4, textvariable=self.seq_width_var, width=5).grid(row=1, column=6, sticky="w", pady=(8, 0))

        ttk.Label(top, text="文件名最大长度:").grid(row=1, column=7, sticky="e", padx=(12, 2), pady=(8, 0))
        self.max_len_var = tk.IntVar(value=80)
        ttk.Spinbox(top, from_=30, to=200, textvariable=self.max_len_var, width=6).grid(row=1, column=8, sticky="w", pady=(8, 0))

        # AI 参数
        ttk.Separator(self, orient="horizontal").pack(fill=tk.X, pady=6)
        ai = ttk.Frame(self, padding=8)
        ai.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(ai, text="Base URL:").grid(row=0, column=0, sticky="w")
        self.base_url_var = tk.StringVar(value=getenv_default("OPENAI_BASE_URL", "https://api.openai.com"))
        ttk.Entry(ai, textvariable=self.base_url_var, width=40).grid(row=0, column=1, sticky="w")

        ttk.Label(ai, text="API Key:").grid(row=0, column=2, sticky="e", padx=(18, 2))
        self.api_key_var = tk.StringVar(value=getenv_default("OPENAI_API_KEY", ""))
        ttk.Entry(ai, textvariable=self.api_key_var, width=36, show="*").grid(row=0, column=3, sticky="w")

        ttk.Label(ai, text="Model:").grid(row=0, column=4, sticky="e", padx=(18, 2))
        self.model_var = tk.StringVar(value=getenv_default("OPENAI_MODEL", "gpt-4o-mini"))
        ttk.Entry(ai, textvariable=self.model_var, width=20).grid(row=0, column=5, sticky="w")

        ttk.Label(ai, text="Timeout:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.timeout_var = tk.IntVar(value=120)
        ttk.Spinbox(ai, from_=10, to=180, textvariable=self.timeout_var, width=6).grid(row=1, column=1, sticky="w", pady=(6, 0))

        ttk.Label(ai, text="Max Retries:").grid(row=1, column=2, sticky="e", padx=(18, 2), pady=(6, 0))
        self.retries_var = tk.IntVar(value=2)
        ttk.Spinbox(ai, from_=0, to=6, textvariable=self.retries_var, width=6).grid(row=1, column=3, sticky="w", pady=(6, 0))

        ttk.Label(ai, text="Rate Limit(s):").grid(row=1, column=4, sticky="e", padx=(18, 2), pady=(6, 0))
        self.rate_limit_var = tk.DoubleVar(value=0.3)
        ttk.Entry(ai, textvariable=self.rate_limit_var, width=8).grid(row=1, column=5, sticky="w", pady=(6, 0))

        # 配置档（可保存/选择多套 API + 策略 + 模板参数）
        ttk.Label(ai, text="配置档:").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.profile_name_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(ai, textvariable=self.profile_name_var, values=[], width=28)
        self.profile_combo.grid(row=2, column=1, sticky="w", pady=(6, 0))
        ttk.Button(ai, text="保存/更新", command=self._on_profile_save).grid(row=2, column=2, padx=(12, 2), pady=(6, 0), sticky="w")
        ttk.Button(ai, text="载入", command=self._on_profile_load).grid(row=2, column=3, padx=(6, 2), pady=(6, 0), sticky="w")
        ttk.Button(ai, text="删除", command=self._on_profile_delete).grid(row=2, column=4, padx=(6, 2), pady=(6, 0), sticky="w")
        ttk.Button(ai, text="测试API", command=self._on_test_api).grid(row=2, column=5, padx=(6, 2), pady=(6, 0), sticky="w")
        ttk.Label(ai, text="提示：Base URL 不要包含 /v1；超时可适当调大", foreground="#777").grid(row=3, column=0, columnspan=6, sticky="w", pady=(4, 0))


        # 选项
        opt = ttk.Frame(self, padding=8)
        opt.pack(side=tk.TOP, fill=tk.X)
        self.verbose_var = tk.BooleanVar(value=False)
        self.backup_var = tk.BooleanVar(value=True)
        self.vision_var = tk.BooleanVar(value=False)
        self.pre_localize_var = tk.BooleanVar(value=True)
        self.rename_md_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt, text="详细日志", variable=self.verbose_var).pack(side=tk.LEFT, padx=(0, 16))
        ttk.Checkbutton(opt, text="写回前备份（推荐）", variable=self.backup_var).pack(side=tk.LEFT)
        ttk.Checkbutton(opt, text="启用视觉理解(VLM)", variable=self.vision_var).pack(side=tk.LEFT, padx=(16, 0))
        ttk.Checkbutton(opt, text="先本地化远程图片（md_image_localizer）", variable=self.pre_localize_var).pack(side=tk.LEFT, padx=(16, 0))
        ttk.Checkbutton(opt, text="按标题重命名 Markdown", variable=self.rename_md_var).pack(side=tk.LEFT, padx=(16, 0))

        # 操作按钮
        btns = ttk.Frame(self, padding=8)
        btns.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(btns, text="预览（不改文件）", command=self._on_preview).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="直接应用（改名/回链）", command=self._on_apply).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="交互式应用（逐图选择）", command=self._on_interactive_apply).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="单图选择（预览+应用）", command=self._on_pick_one).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="保存报告 JSON", command=self._on_save_report).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="本地化远程图片", command=self._on_localize_remote).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="退出", command=self.destroy).pack(side=tk.RIGHT, padx=4)

        # 结果/日志显示
        self.text = scrolledtext.ScrolledText(self, wrap=tk.WORD, font=("Consolas", 10))
        self.text.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=8, pady=8)

    def _log(self, s: str):
        self.text.insert(tk.END, s + "\n")
        self.text.see(tk.END)
        self.update_idletasks()

    def _on_browse(self):
        p = filedialog.askopenfilename(
            title="选择 Markdown 文件",
            filetypes=[("Markdown", "*.md"), ("所有文件", "*.*")]
        )
        if p:
            self.path_var.set(p)

    def _build_config(self, mode: str) -> Config:
        """从 UI 收集配置，构建后端 Config"""
        return Config(
            mode=mode,
            strategy=self.strategy_var.get(),
            base_url=_normalize_base_url(self.base_url_var.get() or getenv_default("OPENAI_BASE_URL", "")),
            api_key=self.api_key_var.get() or getenv_default("OPENAI_API_KEY", ""),
            model=self.model_var.get() or getenv_default("OPENAI_MODEL", "gpt-4o-mini"),
            timeout=int(self.timeout_var.get()),
            max_retries=int(self.retries_var.get()),
            rate_limit=float(self.rate_limit_var.get()),
            attach_dir_name=self.attach_var.get() or "attachments",
            download=bool(self.download_var.get()),
            name_template=self.template_var.get() or DEFAULT_NAME_TEMPLATE,
            seq_width=int(self.seq_width_var.get()),
            max_name_len=int(self.max_len_var.get()),
            save_report=None,
            verbose=bool(self.verbose_var.get()),
            backup=bool(self.backup_var.get()),
            vision=bool(self.vision_var.get()),
            chunk_size=5,
        )

    def _run_in_thread(self, target, *args, **kwargs):
        t = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
        t.start()


    def _resolve_local_image(self, md_dir: Path, src: str) -> Optional[Path]:
        """
        尝试解析/定位本地图片路径，容错以下情况：
        - 链接含引号、反斜杠或 URL 编码（空格等）
        - 目标文件不在预期子目录，改为在文档同级或其子目录递归搜索
        - 名称包含中文与括号等特殊字符
        返回存在的 Path 或 None。
        """
        try:
            s = (src or "").strip().strip('"').strip("'")
            if not s:
                return None
            s = s.replace("\\", "/")
            # 1) 直接解析
            p = (md_dir / Path(s)).resolve()
            if p.exists():
                return p
            # 2) URL 解码后重试
            s2 = unquote(s)
            p2 = (md_dir / Path(s2)).resolve()
            if p2.exists():
                return p2
            # 3) 基于文件名递归搜索（先精确名称，再前缀匹配）
            basename = Path(s2).name or Path(s).name
            if basename:
                for cand in md_dir.rglob(basename):
                    if cand.is_file():
                        return cand
                stem = Path(basename).stem
                exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".tif", ".tiff", ".ico", ".heic"}
                for cand in md_dir.rglob(f"{stem}*"):
                    if cand.is_file() and cand.suffix.lower() in exts:
                        return cand
            return None
        except Exception:
            return None

    def _preview_impl(self):
        try:
            md_path = Path(self.path_var.get()).expanduser()
            if not md_path.exists():
                messagebox.showerror("错误", f"文件不存在：{md_path}")
                return
            # 若策略需要调用 AI，必须提供 Base URL 与 API Key
            if self.strategy_var.get() != "seq":
                base = self.base_url_var.get() or getenv_default("OPENAI_BASE_URL", "")
                key = self.api_key_var.get() or getenv_default("OPENAI_API_KEY", "")
                if not base or not key:
                    messagebox.showerror("错误", "未提供 Base URL 或 API Key。请在 AI 参数中填写后重试，或将策略切换为 seq。")
                    self._log("⚠️ 未提供 Base URL 或 API Key，预览将无法生成 AI 候选，文件名会退化为固定“图意”。")
                    return
            cfg = self._build_config(mode="dry-run")
            self._log(f"▶ 预览：{md_path}")
            self.last_results = process_document(md_path, cfg)
            # 在窗口打印摘要
            self._log("—— 预览结果 ——")
            if self.last_results and isinstance(self.last_results, dict):
                items = self.last_results.get("items", [])
                err_cnt = 0
                first_err: Optional[dict] = None
                for it in items:
                    bs = it.get("best", "")
                    nt = it.get("normalized_title", "")
                    ae = it.get("ai_error", "")
                    tag = f" | ai_error={ae}" if ae else ""
                    self._log(f"  • #{it['index']} block={it['block_index']} idx={it['image_index']} -> {it['suggested_name']} | best={bs} intent={nt}{tag}")
                    if ae:
                        err_cnt += 1
                        if first_err is None:
                            first_err = it
                if self.strategy_var.get() != "seq":
                    if err_cnt == len(items) and len(items) > 0:
                        self._log("⚠️ LLM 全部失败（可能为解析/格式错误、权限/模型不可用或速率限制）。已使用本地回退策略生成名称。")
                    elif err_cnt > 0:
                        self._log(f"⚠️ LLM 部分失败：{err_cnt}/{len(items)}。失败项已使用回退策略。")
                    # 打印首个失败项的详细诊断信息，便于快速定位（请求模式/错误原文/API配置）
                    if first_err:
                        ae = first_err.get("ai_error", "")
                        rm = first_err.get("request_mode", "")
                        raw = first_err.get("ai_raw", "")
                        base = _normalize_base_url(self.base_url_var.get() or getenv_default("OPENAI_BASE_URL", ""))
                        model = self.model_var.get() or getenv_default("OPENAI_MODEL", "gpt-4o-mini")
                        vision_on = bool(self.vision_var.get())
                        self._log(f"🩺 失败诊断：mode={rm} err={ae}")
                        if raw:
                            self._log(f"   ai_raw: {raw}")
                        self._log(f"   API: base={base} model={model} vision={vision_on} timeout={self.timeout_var.get()} retries={self.retries_var.get()} rate_limit={self.rate_limit_var.get()}")
                        self._log("   建议：点击“测试API”验证连通性；确认 Base URL 不含 /v1；模型名称与是否启用视觉理解(VLM)匹配；检查余额与权限。")
            self._log("✅ 预览完成\n")
        except Exception as e:
            self._log(f"❌ 预览失败：{e}")

    def _on_preview(self):
        self.text.delete("1.0", tk.END)
        self._run_in_thread(self._preview_impl)

    def _apply_impl(self):
        try:
            md_path = Path(self.path_var.get()).expanduser()
            if not md_path.exists():
                messagebox.showerror("错误", f"文件不存在：{md_path}")
                return
            # 若策略需要调用 AI，必须提供 Base URL 与 API Key
            if self.strategy_var.get() != "seq":
                base = self.base_url_var.get() or getenv_default("OPENAI_BASE_URL", "")
                key = self.api_key_var.get() or getenv_default("OPENAI_API_KEY", "")
                if not base or not key:
                    messagebox.showerror("错误", "未提供 Base URL 或 API Key。请在 AI 参数中填写后重试，或将策略切换为 seq。")
                    self._log("⚠️ 未提供 Base URL 或 API Key，已取消应用。")
                    return
            # 预检远程图片并提示下载选项影响
            try:
                txt_preview = read_text(md_path)
                refs_preview = collect_images(txt_preview)
                remote_count = sum(1 for r in refs_preview if is_remote_url(r.src if hasattr(r, "src") else r.get("src", "")))
                if remote_count > 0 and not bool(self.download_var.get()):
                    self._log(f"ℹ️ 检测到远程图片 {remote_count} 张，且未勾选“下载远程图片”。这些图片的链接将不会改写为本地路径；仅对本地图片执行重命名/搬移。")
            except Exception:
                pass
            # 预处理：本地化远程图片（可选）
            try:
                if bool(self.pre_localize_var.get()):
                    txt_tmp = read_text(md_path)
                    refs_tmp = collect_images(txt_tmp)
                    remote_tmp = sum(1 for r in refs_tmp if is_remote_url(r.src if hasattr(r, "src") else r.get("src", "")))
                    if remote_tmp > 0:
                        if MILFileProcessor is None:
                            self._log("⚠️ 缺少 md_image_localizer 模块，无法本地化远程图片。")
                        else:
                            self._log(f"▶ 先本地化远程图片：检测到 {remote_tmp} 张远程图片，开始下载...")
                            self._pre_localize_remote_impl(md_path)
            except Exception:
                pass
            cfg = self._build_config(mode="apply")
            self._log(f"▶ 直接应用：{md_path}")
            self.last_results = process_document(md_path, cfg)
            # 应用后如 LLM 失败项较多给出提示
            try:
                items = (self.last_results or {}).get("items", [])
                err_cnt = sum(1 for it in items if it.get("ai_error"))
                if self.strategy_var.get() != "seq" and err_cnt:
                    self._log(f"ℹ️ LLM 失败项：{err_cnt}/{len(items)}（已使用回退策略命名）。")
            except Exception:
                pass
            # 可选：重命名 Markdown 文件
            try:
                if bool(self.rename_md_var.get()):
                    new_path = self._maybe_rename_md(md_path)
                    md_path = new_path
            except Exception as e:
                self._log(f"⚠️ 重命名 Markdown 失败：{e}")
            self._log("✅ 已应用（如启用下载则已下载并回写链接）。\n")
        except Exception as e:
            self._log(f"❌ 应用失败：{e}")

    def _on_apply(self):
        self.text.delete("1.0", tk.END)
        self._run_in_thread(self._apply_impl)

    def _on_localize_remote(self):
        self.text.delete("1.0", tk.END)
        try:
            md_path = Path(self.path_var.get()).expanduser()
            if not md_path.exists():
                messagebox.showerror("错误", f"文件不存在：{md_path}")
                return
            self._run_in_thread(self._pre_localize_remote_impl, md_path)
        except Exception as e:
            self._log(f"❌ 本地化失败：{e}")

    def _pre_localize_remote_impl(self, md_path: Path):
        try:
            if MILFileProcessor is None:
                self._log("⚠️ 缺少 md_image_localizer 模块，无法执行本地化。")
                return
            attach = self.attach_var.get() or "attachments"
            timeout = int(self.timeout_var.get())
            # 预估远程数
            try:
                txt = read_text(md_path)
                refs = collect_images(txt)
                remote_count = sum(1 for r in refs if is_remote_url(r.src if hasattr(r, "src") else r.get("src", "")))
            except Exception:
                remote_count = -1
            self._log(f"▶ 执行远程图片本地化（到 {attach}/）...")
            proc = MILFileProcessor(md_path, attach, timeout, dry_run=False, rename_images=False)
            dl, repl, ref = proc.process()
            if remote_count >= 0:
                self._log(f"✅ 本地化完成：下载 {dl} 张，改写 {repl} 处，更新引用式 {ref} 处（预计远程 {remote_count}）")
            else:
                self._log(f"✅ 本地化完成：下载 {dl} 张，改写 {repl} 处，更新引用式 {ref} 处")
        except Exception as e:
            self._log(f"❌ 本地化失败：{e}")

    def _maybe_rename_md(self, md_path: Path) -> Path:
        try:
            text = read_text(md_path)
            title = extract_doc_title(text, md_path)
            safe = sanitize_filename(title)
            if not safe:
                return md_path
            target = md_path.with_name(f"{safe}{md_path.suffix}")
            if target == md_path:
                return md_path
            if target.exists():
                target = ensure_unique_path(md_path.parent, f"{safe}{md_path.suffix}")
            md_path.rename(target)
            self.path_var.set(str(target))
            self._log(f"📝 已重命名 Markdown：{md_path.name} -> {target.name}")
            return target
        except Exception as e:
            self._log(f"⚠️ 重命名 Markdown 失败：{e}")
            return md_path

    # 交互式应用（GUI 内逐图选择候选）
    def _interactive_apply_impl(self):
        """
        流程：
        1) 调用后端生成候选（不改文件）：mode=no-rename 或 dry-run
        2) 弹出逐图对话框选择候选或自定义短语
        3) 用选择的短语按模板计算目标文件名，执行重命名/回链（本函数内实现）
        """
        try:
            md_path = Path(self.path_var.get()).expanduser()
            if not md_path.exists():
                messagebox.showerror("错误", f"文件不存在：{md_path}")
                return
            # 若策略需要调用 AI，必须提供 Base URL 与 API Key
            if self.strategy_var.get() != "seq":
                base = self.base_url_var.get() or getenv_default("OPENAI_BASE_URL", "")
                key = self.api_key_var.get() or getenv_default("OPENAI_API_KEY", "")
                if not base or not key:
                    messagebox.showerror("错误", "未提供 Base URL 或 API Key。请填写后重试，或将策略切换为 seq。")
                    self._log("⚠️ 未提供 Base URL 或 API Key，将无法生成 AI 候选。")
                    return
            # 预检远程图片下载影响
            try:
                txt_preview = read_text(md_path)
                refs_preview = collect_images(txt_preview)
                remote_count = sum(1 for r in refs_preview if is_remote_url(r.src if hasattr(r, "src") else r.get("src", "")))
                if remote_count > 0 and not bool(self.download_var.get()):
                    self._log(f"ℹ️ 检测到远程图片 {remote_count} 张，且未勾选“下载远程图片”。交互式应用阶段将不会改写远程链接。")
            except Exception:
                pass
            # 预处理：本地化远程图片（可选）
            try:
                if bool(self.pre_localize_var.get()):
                    txt_tmp = read_text(md_path)
                    refs_tmp = collect_images(txt_tmp)
                    remote_tmp = sum(1 for r in refs_tmp if is_remote_url(r.src if hasattr(r, "src") else r.get("src", "")))
                    if remote_tmp > 0:
                        if MILFileProcessor is None:
                            self._log("⚠️ 缺少 md_image_localizer 模块，无法本地化远程图片。")
                        else:
                            self._log(f"▶ 先本地化远程图片：检测到 {remote_tmp} 张远程图片，开始下载...")
                            self._pre_localize_remote_impl(md_path)
            except Exception:
                pass
            cfg_preview = self._build_config(mode="dry-run")
            self._log(f"▶ 获取候选：{md_path}")
            results = process_document(md_path, cfg_preview)
            self.last_results = results
            if not results or "items" not in results:
                self._log("⚠️ 未获取到候选。")
                return
            items = results["items"]
            title = results.get("title", extract_doc_title(read_text(md_path), md_path))
            # 逐图对话框
            chosen_map: Dict[int, str] = {}
            for it in items:
                idx = it["index"]
                candidates = it.get("candidates", [])
                default_title = it.get("normalized_title") or (candidates[0]["title"] if candidates else "图意")
                chosen = self._choose_candidate_dialog(idx, it["src"], it.get("above_text",""), it.get("below_text",""), candidates, default_title)
                if chosen is None:  # 用户取消
                    self._log("ℹ️ 已取消交互式应用。")
                    return
                chosen_map[idx] = sanitize_filename(chosen) if chosen else sanitize_filename(default_title)

            # 应用选择：执行重命名与回链
            self._log("▶ 按选择应用重命名与回链...")
            self._apply_with_overrides(md_path, title, chosen_map)
            try:
                if bool(self.rename_md_var.get()):
                    newp = self._maybe_rename_md(md_path)
                    md_path = newp
            except Exception as e:
                self._log(f"⚠️ 重命名 Markdown 失败：{e}")
            self._log("✅ 交互式应用完成。\n")
        except Exception as e:
            self._log(f"❌ 交互式应用失败：{e}")

    def _choose_candidate_dialog(self, index: int, src: str, above: str, below: str, candidates: List[Dict], default_title: str) -> Optional[str]:
        """弹出一个模式对话框，让用户为第 index 张图片选择候选或自定义"""
        dlg = tk.Toplevel(self)
        dlg.title(f"选择图意 - 图片 #{index}")
        dlg.geometry("720x520")
        dlg.transient(self)
        dlg.grab_set()

        # 标题
        ttk.Label(dlg, text=f"图片 #{index}", font=("Microsoft YaHei", 11, "bold")).pack(pady=(10, 6))
        ttk.Label(dlg, text=f"源: {src}", wraplength=680, foreground="#555").pack(pady=(0, 8))

        # 上下文展示（可折叠简化，此处直接显示）
        ctx_frame = ttk.LabelFrame(dlg, text="上下文")
        ctx_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        txt = scrolledtext.ScrolledText(ctx_frame, wrap=tk.WORD, height=10)
        txt.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        txt.insert(tk.END, f"[上文]\n{above.strip()}\n\n[下文]\n{below.strip()}\n")
        txt.configure(state=tk.DISABLED)

        # 候选区
        cand_frame = ttk.LabelFrame(dlg, text="候选（选择一项，或在下方自定义）")
        cand_frame.pack(fill=tk.X, padx=10, pady=6)
        var_choice = tk.StringVar(value=default_title)
        # 展示前 6 个候选
        show_cands = candidates[:6] if candidates else []
        if not show_cands:
            show_cands = [{"strategy":"intent","title":default_title,"reason":"默认","confidence":0.6}]
        for i, c in enumerate(show_cands, start=1):
            title = c.get("title") or ""
            meta = f"[{c.get('strategy')}] conf={c.get('confidence',0)} {c.get('reason','')}"
            rb = ttk.Radiobutton(cand_frame, text=title, value=title, variable=var_choice)
            rb.pack(anchor="w", padx=8, pady=2)
            ttk.Label(cand_frame, text=meta, foreground="#777").pack(anchor="w", padx=28)

        # 自定义输入
        custom_frame = ttk.Frame(dlg)
        custom_frame.pack(fill=tk.X, padx=10, pady=6)
        ttk.Label(custom_frame, text="自定义图意：").pack(side=tk.LEFT)
        custom_var = tk.StringVar()
        ttk.Entry(custom_frame, textvariable=custom_var, width=48).pack(side=tk.LEFT, padx=6)

        # 按钮
        btns = ttk.Frame(dlg)
        btns.pack(fill=tk.X, padx=10, pady=10)
        ret: Dict[str, Optional[str]] = {"val": None}

        def on_ok():
            chosen = custom_var.get().strip() or var_choice.get().strip()
            ret["val"] = sanitize_filename(chosen) if chosen else None
            dlg.destroy()

        def on_cancel():
            ret["val"] = None
            dlg.destroy()

        ttk.Button(btns, text="确定", command=on_ok).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="取消", command=on_cancel).pack(side=tk.RIGHT)

        dlg.wait_window()
        return ret["val"]

    def _apply_with_overrides(self, md_path: Path, title: str, chosen_map: Dict[int, str]):
        """
        根据用户选择的每图“图意”短语执行改名与回链。
        逻辑与后端一致： block/idx 采用“上一图到当前图的区间文本是否存在”来划分块序与块内序号。
        """
        text = read_text(md_path)
        refs = collect_images(text)

        # 准备输出文本（以偏移切片方式构建）
        new_parts: List[str] = []
        cursor = 0

        # 计数器
        block_idx = 0
        img_idx = 0
        last_end = 0

        # 附件目录
        attach_dir = md_path.parent / (self.attach_var.get() or "attachments")
        seq_width = int(self.seq_width_var.get())
        max_len = int(self.max_len_var.get())
        name_tmpl = self.template_var.get() or DEFAULT_NAME_TEMPLATE
        timeout = int(self.timeout_var.get())
        download_opt = bool(self.download_var.get())

        for i, ref in enumerate(refs):
            # 上一图到当前图之间的文字
            above, below, between, _ = core.find_neighbor_text(text, refs, i)
            # 与后端一致的分块判定：
            # 仅当“上一图到当前图之间”的有效文字 >=4，且剔除“如上/如下/上图/下图/见图X”等显式引用后仍有足够字母/汉字，才视为新块
            visible_above = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", above)
            is_new_block = False
            if len(visible_above) >= 4:
                above_wo_refs = above
                try:
                    # 剥离显式引用短语
                    for pat in core.EXPLICIT_REF_PATTERNS:
                        above_wo_refs = re.sub(pat, "", above_wo_refs)
                except Exception:
                    pass
                # 去掉数字与符号，仅保留字母/汉字，再判断长度阈值
                letters_only = re.sub(r"[\d\W_]+", "", above_wo_refs, flags=re.UNICODE)
                if len(letters_only) >= 4:
                    is_new_block = True
            if is_new_block:
                block_idx += 1
                img_idx = 1
            else:
                if block_idx == 0:
                    block_idx = 1
                img_idx += 1

            # 拼接原文前段
            new_parts.append(text[cursor:ref.start])

            # 最终图意短语
            chosen = chosen_map.get(ref["index"] if isinstance(ref, dict) else (i + 1))
            if not chosen:
                # 兜底：用上一次预览的 normalized_title 或“图意”
                chosen = "图意"
                if self.last_results and "items" in self.last_results:
                    try:
                        chosen = self.last_results["items"][i].get("normalized_title") or chosen
                    except Exception:
                        pass
            chosen = sanitize_filename(chosen)

            # 计算目标文件名（传入全局序号 i+1 以支持 {index}）
            final_base = name_with_template(name_tmpl, title, block_idx, img_idx, chosen, seq_width, max_len, global_index=(i + 1))

            # 执行下载或搬移/重命名，并得到新相对路径
            new_rel = ref.src  # 默认保留
            try:
                if download_opt and is_remote_url(ref.src):
                    saved = download_image(ref.src, attach_dir, timeout)
                    if saved:
                        ext = saved.suffix or ".img"
                        target = ensure_unique_path(attach_dir, f"{final_base}{ext}")
                        try:
                            saved.rename(target)
                        except Exception:
                            target.write_bytes(saved.read_bytes())
                            try:
                                saved.unlink(missing_ok=True)  # type: ignore
                            except Exception:
                                pass
                        new_rel = os.path.relpath(target, md_path.parent).replace("\\", "/")
                else:
                    # 本地：搬移/重命名到附件目录（带鲁棒解析）
                    try:
                        src_path = self._resolve_local_image(md_path.parent, ref.src)
                        if src_path and src_path.exists():
                            ext = src_path.suffix or ".img"
                            target = ensure_unique_path(attach_dir, f"{final_base}{ext}")
                            attach_dir.mkdir(parents=True, exist_ok=True)
                            if src_path.parent == attach_dir:
                                src_path.rename(target)
                            else:
                                target.write_bytes(src_path.read_bytes())
                            new_rel = os.path.relpath(target, md_path.parent).replace("\\", "/")
                        else:
                            self._log(f"⚠️ 本地图片不存在或无法定位：{ref.src}")
                    except Exception as e:
                        self._log(f"⚠️ 搬移/重命名失败：{e}")
            except Exception as e:
                self._log(f"⚠️ 处理图片失败：{e}")

            # 在该图片标记段内替换 src -> new_rel
            original_seg = text[ref.start:ref.end]
            new_seg = original_seg.replace(ref.src, new_rel)
            new_parts.append(new_seg)

            # 游标推进
            cursor = ref.end

        # 追加尾部
        new_parts.append(text[cursor:])
        new_text = "".join(new_parts)

        # 备份与写回
        if bool(self.backup_var.get()):
            backup_path = md_path.with_suffix(md_path.suffix + ".bak")
            try:
                backup_path.write_text(text, encoding="utf-8", newline="\n")
                self._log(f"🗂 已备份原文件 -> {backup_path}")
            except Exception as e:
                self._log(f"⚠️ 备份失败：{e}")

        if new_text != text:
            try:
                write_text_utf8(md_path, new_text)
                self._log(f"✅ 已写回：{md_path}")
            except Exception as e:
                self._log(f"❌ 写回失败：{e}")
        else:
            self._log("ℹ️ 文档未发生变化（可能未能生成新路径或处理失败）。")

    def _on_interactive_apply(self):
        self.text.delete("1.0", tk.END)
        self._run_in_thread(self._interactive_apply_impl)

    # 单图选择（GUI 内预览图片并对指定序号应用）
    def _on_pick_one(self):
        try:
            self.text.delete("1.0", tk.END)
            md_path = Path(self.path_var.get()).expanduser()
            if not md_path.exists():
                messagebox.showerror("错误", f"文件不存在：{md_path}")
                return
            # 若策略需要调用 AI，必须提供 Base URL 与 API Key（在主线程中校验）
            if self.strategy_var.get() != "seq":
                base = self.base_url_var.get() or getenv_default("OPENAI_BASE_URL", "")
                key = self.api_key_var.get() or getenv_default("OPENAI_API_KEY", "")
                if not base or not key:
                    messagebox.showerror("错误", "未提供 Base URL 或 API Key。请在 AI 参数中填写后重试，或将策略切换为 seq。")
                    self._log("⚠️ 未提供 Base URL 或 API Key，单图选择将无法生成 AI 候选。")
                    return
            # 在主线程中解析文档并获取图片数量（避免后台线程里弹 simpledialog）
            text = read_text(md_path)
            refs = collect_images(text)
            if not refs:
                messagebox.showinfo("提示", "未发现图片。")
                return
            # 可选：预先本地化远程图片
            try:
                if bool(self.pre_localize_var.get()):
                    remote_count = sum(1 for r in refs if is_remote_url(r.src if hasattr(r, "src") else r.get("src", "")))
                    if remote_count > 0:
                        if MILFileProcessor is None:
                            self._log("⚠️ 缺少 md_image_localizer 模块，无法本地化远程图片。")
                        else:
                            self._log(f"▶ 先本地化远程图片：检测到 {remote_count} 张远程图片，开始下载...")
                            self._pre_localize_remote_impl(md_path)
                            text = read_text(md_path)
                            refs = collect_images(text)
            except Exception:
                pass
            idx = simpledialog.askinteger("单图选择", f"输入图片序号（1~{len(refs)}）：", minvalue=1, maxvalue=len(refs), parent=self)
            if not idx:
                self._log("ℹ️ 已取消单图选择。")
                return
            # 后台线程执行耗时操作（生成候选、重命名/改链），并回到主线程弹出预览对话框
            self._run_in_thread(self._pick_one_impl, md_path, text, refs, int(idx))
        except Exception as e:
            self._log(f"❌ 单图选择失败：{e}")

    def _pick_one_impl(self, md_path: Path, text: str, refs: List, idx: int):
        try:
            # 预览候选（只取该序号的项展示）
            cfg_preview = self._build_config(mode="dry-run")
            self._log(f"▶ 获取单图候选：{md_path} | index={idx}")
            results = process_document(md_path, cfg_preview)
            items = results.get("items", []) if isinstance(results, dict) else []
            if not items or idx - 1 >= len(items):
                self._log("⚠️ 未获取到候选或序号超出范围。")
                return
            it = items[idx - 1]
            title = results.get("title", extract_doc_title(text, md_path))

            # 提取三种候选短语（上文/下文/识图intent）
            cands = it.get("candidates", []) or []
            def _pick_title_for(strategy: str, default_val: str) -> str:
                for c in cands:
                    if c.get("strategy") == strategy and c.get("title"):
                        return c.get("title")
                return default_val
            default_nt = it.get("normalized_title") or "图意"
            above_phrase = _pick_title_for("above", default_nt)
            below_phrase = _pick_title_for("below", default_nt)
            intent_phrase = _pick_title_for("intent", default_nt)

            # 在主线程中弹窗预览该图并选择（避免线程问题）
            chosen_holder: Dict[str, Optional[str]] = {"val": None}
            done = threading.Event()
            def _open_dialog_on_main():
                chosen = self._choose_pick_one_dialog(
                    idx,
                    md_path,
                    it.get("src", ""),
                    it.get("above_text", ""),
                    it.get("below_text", ""),
                    above_phrase,
                    below_phrase,
                    intent_phrase
                )
                chosen_holder["val"] = chosen
                done.set()
            self.after(0, _open_dialog_on_main)
            done.wait()
            if chosen_holder["val"] is None:
                self._log("ℹ️ 已取消单图选择。")
                return
            chosen = sanitize_filename(chosen_holder["val"] or default_nt)

            # 计算该图的块序与块内序号（与后端一致规则）
            block_idx = 0
            img_idx = 0
            target_ref = None
            target_block = 0
            target_img = 0
            for i, ref in enumerate(refs):
                above, below, between, explicit_refs = find_neighbor_text(text, refs, i)
                visible_above = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", above)
                is_new_block = False
                if len(visible_above) >= 4:
                    above_wo_refs = above
                    try:
                        for pat in core.EXPLICIT_REF_PATTERNS:
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
                else:
                    if block_idx == 0:
                        block_idx = 1
                    img_idx += 1

                if (i + 1) == idx:
                    target_ref = ref
                    target_block = block_idx
                    target_img = img_idx
                    break

            if target_ref is None:
                self._log("❌ 迭代失败：未定位到目标图片。")
                return

            # 生成最终文件名
            final_name = name_with_template(
                self.template_var.get() or DEFAULT_NAME_TEMPLATE,
                title,
                target_block,
                target_img,
                chosen,
                int(self.seq_width_var.get()),
                int(self.max_len_var.get()),
                global_index=idx
            )

            # 执行下载/搬移与改链（仅该图）
            new_text = text
            attach_dir = md_path.parent / (self.attach_var.get() or "attachments")
            timeout = int(self.timeout_var.get())
            download_opt = bool(self.download_var.get())
            try:
                if download_opt and is_remote_url(target_ref.src):
                    saved = download_image(target_ref.src, attach_dir, timeout)
                    if saved:
                        ext = saved.suffix or ".img"
                        target_path = ensure_unique_path(attach_dir, f"{final_name}{ext}")
                        try:
                            saved.rename(target_path)
                        except Exception:
                            target_path.write_bytes(saved.read_bytes())
                            try:
                                saved.unlink(missing_ok=True)  # type: ignore
                            except Exception:
                                pass
                        new_rel = os.path.relpath(target_path, md_path.parent).replace("\\", "/")
                        new_text = new_text[:target_ref.start] + new_text[target_ref.start:target_ref.end].replace(target_ref.src, new_rel) + new_text[target_ref.end:]
                else:
                    # 本地：搬移/重命名到附件目录
                    src_path = self._resolve_local_image(md_path.parent, target_ref.src)
                    if src_path and src_path.exists():
                        ext = src_path.suffix or ".img"
                        target_path = ensure_unique_path(attach_dir, f"{final_name}{ext}")
                        attach_dir.mkdir(parents=True, exist_ok=True)
                        if src_path.parent == attach_dir:
                            src_path.rename(target_path)
                        else:
                            target_path.write_bytes(src_path.read_bytes())
                        new_rel = os.path.relpath(target_path, md_path.parent).replace("\\", "/")
                        new_text = new_text[:target_ref.start] + new_text[target_ref.start:target_ref.end].replace(target_ref.src, new_rel) + new_text[target_ref.end:]
                    else:
                        self._log(f"⚠️ 本地图片不存在或无法定位：{target_ref.src}")
            except Exception as e:
                self._log(f"⚠️ 处理图片失败：{e}")

            # 备份与写回
            if bool(self.backup_var.get()):
                backup_path = md_path.with_suffix(md_path.suffix + ".bak")
                try:
                    backup_path.write_text(text, encoding="utf-8", newline="\n")
                    self._log(f"🗂 已备份原文件 -> {backup_path}")
                except Exception as e:
                    self._log(f"⚠️ 备份失败：{e}")

            if new_text != text:
                try:
                    write_text_utf8(md_path, new_text)
                    self._log(f"✅ 已写回（单图）：{md_path}\n  • #{idx} block={target_block} idx={target_img} -> {final_name}")
                    try:
                        if bool(self.rename_md_var.get()):
                            newp = self._maybe_rename_md(md_path)
                            md_path = newp
                    except Exception as e2:
                        self._log(f"⚠️ 重命名 Markdown 失败：{e2}")
                except Exception as e:
                    self._log(f"❌ 写回失败：{e}")
            else:
                self._log("ℹ️ 文档未发生变化（可能处理失败或路径未更新）。")

        except Exception as e:
            self._log(f"❌ 单图选择失败：{e}")

    def _choose_pick_one_dialog(self, index: int, md_path: Path, src: str, above: str, below: str, above_phrase: str, below_phrase: str, intent_phrase: str) -> Optional[str]:
        """弹出单图选择对话框，并直接显示图片预览与三选一候选"""
        dlg = tk.Toplevel(self)
        dlg.title(f"单图选择 - 图片 #{index}")
        dlg.geometry("820x680")
        dlg.transient(self)
        dlg.grab_set()

        ttk.Label(dlg, text=f"图片 #{index}", font=("Microsoft YaHei", 11, "bold")).pack(pady=(10, 6))
        ttk.Label(dlg, text=f"源: {src}", wraplength=780, foreground="#555").pack(pady=(0, 8))

        # 预览图片（支持本地/远程；远程需 requests，更多格式需 Pillow）
        preview_frame = ttk.LabelFrame(dlg, text="图片预览")
        preview_frame.pack(fill=tk.X, padx=10, pady=6)
        img_label = ttk.Label(preview_frame, text="正在尝试加载图片预览...", anchor="center")
        img_label.pack(fill=tk.X, padx=10, pady=10)

        def _load_preview():
            """
            在后台线程加载字节数据，在主线程中创建 PhotoImage/ImageTk 并更新 UI，避免跨线程操作 Tk。
            """
            try:
                if core.is_remote_url(src):
                    if requests is None or Image is None or ImageTk is None:
                        img_label.after(0, lambda: img_label.configure(text="远程图片预览需要 requests + Pillow（PIL）。请安装后重试：pip install requests pillow"))
                        return
                    r = requests.get(src, timeout=12)
                    r.raise_for_status()
                    data = r.content

                    def apply_remote():
                        try:
                            im = Image.open(BytesIO(data))
                            try:
                                im = im.convert("RGB")
                            except Exception:
                                pass
                            im.thumbnail((760, 420))
                            tk_img = ImageTk.PhotoImage(im)
                            img_label.configure(image=tk_img, text="")
                            img_label.image = tk_img  # 防 GC
                        except Exception as e2:
                            img_label.configure(text=f"预览加载失败：{e2}")
                    img_label.after(0, apply_remote)
                else:
                    p = self._resolve_local_image(md_path.parent, src) or (md_path.parent / Path(src)).resolve()
                    if not p.exists():
                        img_label.after(0, lambda: img_label.configure(text=f"文件不存在或无法定位：{p}"))
                        return
                    if Image is not None and ImageTk is not None:
                        try:
                            data = p.read_bytes()
                        except Exception as e:
                            img_label.after(0, lambda: img_label.configure(text=f"读取失败：{e}"))
                            return

                        def apply_local_pillow():
                            try:
                                im = Image.open(BytesIO(data))
                                try:
                                    im = im.convert("RGB")
                                except Exception:
                                    pass
                                im.thumbnail((760, 420))
                                tk_img = ImageTk.PhotoImage(im)
                                img_label.configure(image=tk_img, text="")
                                img_label.image = tk_img  # 防 GC
                            except Exception as e2:
                                img_label.configure(text=f"预览加载失败：{e2}")
                        img_label.after(0, apply_local_pillow)
                    else:
                        # 无 Pillow：仅支持 PNG/GIF 的 Tk PhotoImage，且必须在主线程执行
                        if p.suffix.lower() in (".png", ".gif"):
                            def apply_photoimage():
                                try:
                                    tk_img2 = tk.PhotoImage(file=str(p))
                                    img_label.configure(image=tk_img2, text="")
                                    img_label.image = tk_img2  # 防 GC
                                except Exception as e3:
                                    img_label.configure(text=f"加载失败：{e3}")
                            img_label.after(0, apply_photoimage)
                        else:
                            img_label.after(0, lambda: img_label.configure(text="缺少 Pillow（PIL），无法预览非 PNG/GIF。请安装：pip install pillow"))
            except Exception as e:
                img_label.after(0, lambda: img_label.configure(text=f"预览加载失败：{e}"))

        # 异步加载，避免卡 UI
        try:
            threading.Thread(target=_load_preview, daemon=True).start()
        except Exception:
            _load_preview()

        # 上下文展示
        ctx_frame = ttk.LabelFrame(dlg, text="上下文")
        ctx_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        txt = scrolledtext.ScrolledText(ctx_frame, wrap=tk.WORD, height=10)
        txt.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        txt.insert(tk.END, f"[上文]\n{(above or '').strip()}\n\n[下文]\n{(below or '').strip()}\n")
        txt.configure(state=tk.DISABLED)

        # 候选（三选一 + 自定义）
        cand_frame = ttk.LabelFrame(dlg, text="选择图意（三选一，或下方自定义）")
        cand_frame.pack(fill=tk.X, padx=10, pady=6)
        var_choice = tk.StringVar(value=intent_phrase or above_phrase or below_phrase or "图意")
        ttk.Radiobutton(cand_frame, text=f"上文总结 -> {above_phrase}", value=above_phrase, variable=var_choice).pack(anchor="w", padx=8, pady=2)
        ttk.Radiobutton(cand_frame, text=f"下文总结 -> {below_phrase}", value=below_phrase, variable=var_choice).pack(anchor="w", padx=8, pady=2)
        ttk.Radiobutton(cand_frame, text=f"识图图意 -> {intent_phrase}", value=intent_phrase, variable=var_choice).pack(anchor="w", padx=8, pady=2)

        custom_frame = ttk.Frame(dlg)
        custom_frame.pack(fill=tk.X, padx=10, pady=6)
        ttk.Label(custom_frame, text="自定义图意：").pack(side=tk.LEFT)
        custom_var = tk.StringVar()
        ttk.Entry(custom_frame, textvariable=custom_var, width=48).pack(side=tk.LEFT, padx=6)

        # 按钮
        btns = ttk.Frame(dlg)
        btns.pack(fill=tk.X, padx=10, pady=10)
        ret: Dict[str, Optional[str]] = {"val": None}

        def on_ok():
            chosen = custom_var.get().strip() or var_choice.get().strip()
            ret["val"] = sanitize_filename(chosen) if chosen else None
            dlg.destroy()

        def on_cancel():
            ret["val"] = None
            dlg.destroy()

        ttk.Button(btns, text="确定", command=on_ok).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="取消", command=on_cancel).pack(side=tk.RIGHT)

        dlg.wait_window()
        return ret["val"]

    def _on_save_report(self):
        if not self.last_results:
            messagebox.showinfo("提示", "没有可保存的报告，请先预览或应用。")
            return
        p = filedialog.asksaveasfilename(
            title="保存报告为 JSON",
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json")]
        )
        if not p:
            return
        try:
            Path(p).parent.mkdir(parents=True, exist_ok=True)
            Path(p).write_text(json.dumps(self.last_results, ensure_ascii=False, indent=2), encoding="utf-8")
            messagebox.showinfo("提示", f"已保存：{p}")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：{e}")

    def _profiles_path(self) -> Path:
        return PROFILES_PATH

    def _load_profiles(self):
        try:
            p = self._profiles_path()
            if p.exists():
                self.profiles = json.load(p.open("r", encoding="utf-8"))
            else:
                self.profiles = {}
        except Exception:
            self.profiles = {}
        # 更新下拉
        names = sorted(list(self.profiles.keys()))
        try:
            self.profile_combo["values"] = names
        except Exception:
            pass
        # 自动选择默认/最近一个
        if names and not self.profile_name_var.get():
            self.profile_name_var.set(names[0])

    def _save_profiles(self):
        try:
            p = self._profiles_path()
            p.parent.mkdir(parents=True, exist_ok=True)
            json.dump(self.profiles, p.open("w", encoding="utf-8"), ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("错误", f"保存配置档失败：{e}")

    def _collect_current_settings(self) -> Dict:
        # 收集当前 UI 参数，便于保存为配置档
        return {
            "base_url": self.base_url_var.get().strip(),
            "api_key": self.api_key_var.get().strip(),
            "model": self.model_var.get().strip(),
            "timeout": int(self.timeout_var.get()),
            "max_retries": int(self.retries_var.get()),
            "rate_limit": float(self.rate_limit_var.get()),
            "strategy": self.strategy_var.get().strip(),
            "template": self.template_var.get().strip(),
            "seq_width": int(self.seq_width_var.get()),
            "max_name_len": int(self.max_len_var.get()),
            "attach_dir_name": self.attach_var.get().strip(),
            "download": bool(self.download_var.get()),
            "vision": bool(self.vision_var.get()),
            "pre_localize": bool(self.pre_localize_var.get()),
            "rename_md": bool(self.rename_md_var.get()),
        }

    def _apply_profile(self, d: Dict):
        # 将配置档参数写回 UI
        try:
            self.base_url_var.set(d.get("base_url", self.base_url_var.get()))
            self.api_key_var.set(d.get("api_key", self.api_key_var.get()))
            self.model_var.set(d.get("model", self.model_var.get()))
            self.timeout_var.set(int(d.get("timeout", self.timeout_var.get())))
            self.retries_var.set(int(d.get("max_retries", self.retries_var.get())))
            self.rate_limit_var.set(float(d.get("rate_limit", self.rate_limit_var.get())))
            self.strategy_var.set(d.get("strategy", self.strategy_var.get()))
            self.template_var.set(d.get("template", self.template_var.get()))
            self.seq_width_var.set(int(d.get("seq_width", self.seq_width_var.get())))
            self.max_len_var.set(int(d.get("max_name_len", self.max_len_var.get())))
            self.attach_var.set(d.get("attach_dir_name", self.attach_var.get()))
            self.download_var.set(bool(d.get("download", self.download_var.get())))
            self.vision_var.set(bool(d.get("vision", self.vision_var.get())))
            self.pre_localize_var.set(bool(d.get("pre_localize", self.pre_localize_var.get())))
            self.rename_md_var.set(bool(d.get("rename_md", self.rename_md_var.get())))
        except Exception as e:
            messagebox.showerror("错误", f"载入配置失败：{e}")

    def _on_profile_save(self):
        name = (self.profile_name_var.get() or "").strip()
        if not name:
            messagebox.showinfo("提示", "请输入配置档名称后再保存。")
            return
        d = self._collect_current_settings()
        self.profiles[name] = d
        self._save_profiles()
        # 刷新下拉
        try:
            names = sorted(list(self.profiles.keys()))
            self.profile_combo["values"] = names
            if name not in names:
                self.profile_name_var.set(name)
        except Exception:
            pass
        messagebox.showinfo("提示", f"已保存/更新配置档：{name}")

    def _on_profile_load(self):
        name = (self.profile_name_var.get() or "").strip()
        if not name or name not in self.profiles:
            messagebox.showinfo("提示", "未找到该配置档，请先保存或选择已有配置名。")
            return
        self._apply_profile(self.profiles[name])
        messagebox.showinfo("提示", f"已载入配置档：{name}")

    def _on_profile_delete(self):
        name = (self.profile_name_var.get() or "").strip()
        if not name or name not in self.profiles:
            messagebox.showinfo("提示", "未找到该配置档。")
            return
        try:
            del self.profiles[name]
            self._save_profiles()
            names = sorted(list(self.profiles.keys()))
            self.profile_combo["values"] = names
            self.profile_name_var.set(names[0] if names else "")
            messagebox.showinfo("提示", f"已删除配置档：{name}")
        except Exception as e:
            messagebox.showerror("错误", f"删除失败：{e}")

    def _on_test_api(self):
        """测试当前 Base URL / API Key / Model 是否可用（兼容 SiliconFlow / OpenAI 格式）"""
        try:
            base = _normalize_base_url(self.base_url_var.get() or getenv_default("OPENAI_BASE_URL", ""))
            key = self.api_key_var.get() or getenv_default("OPENAI_API_KEY", "")
            model = self.model_var.get() or getenv_default("OPENAI_MODEL", "gpt-4o-mini")
            if not base or not key:
                messagebox.showerror("错误", "请先填写 Base URL 与 API Key。")
                return
            msgs = [
                {"role": "system", "content": "你是健康检查助手。只输出严格JSON，形如 {\"ok\":true}"},
                {"role": "user", "content": json.dumps({"ping": "hello"}, ensure_ascii=False)},
            ]
            out = core.call_openai_chat(
                base, key, model, msgs,
                timeout=int(self.timeout_var.get()),
                max_retries=int(self.retries_var.get()),
                rate_limit=float(self.rate_limit_var.get()),
                verbose=True
            )
            d = core.safe_parse_json(out) if out else None
            if isinstance(d, dict):
                messagebox.showinfo("测试结果", f"连接成功：{base}\n模型：{model}\n返回：{json.dumps(d, ensure_ascii=False)}")
            else:
                text = (out or "")[:280]
                messagebox.showwarning("测试结果", f"已连接但返回不可解析（可能非严格JSON）：\n{text}")
        except Exception as e:
            messagebox.showerror("测试失败", f"{e}")

    def _bring_to_front(self):
        try:
            self.update()
            self.deiconify()
            self.lift()
            self.attributes("-topmost", True)
            # 短暂置顶以抢前台，随后还原
            self.after(600, lambda: self.attributes("-topmost", False))
            self.focus_force()
        except Exception:
            pass

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()