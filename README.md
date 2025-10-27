# AI 图片“图意”命名器 · V1

AI 图片“图意”命名器是一款面向 Markdown 图文的 LLM 命名/搬运工具，支持批量生成图意、翻译/归纳上下文，并自动下载、重命名与回写图片链接。

本发行包提供 Markdown 图片命名/搬运的一体化工具集，包含批量 GUI、命令行核心脚本以及可选的图片本地化辅助脚本。本次 V1 版本对 GUI 进行了完整修复，并新增了“翻译 / 归纳”上下文助手，可在单图审核时快速获取译文或摘要。

## 目录结构
```
release_bundle/
├─ README.md                  当前说明
├─ requirements.txt           依赖列表
└─ tool/
   ├─ ai_image_intent_namer.py          核心 CLI / 业务逻辑
   ├─ ai_image_intent_namer_batch_gui.py 批量 GUI（推荐入口）
   ├─ ai_image_intent_namer_gui.py       旧版 GUI（可选）
   └─ md_image_localizer.py              可选：Markdown 图片本地化脚本
```
> 配置文件 `ai_image_intent_namer_gui.profiles.json` 不会随包分发，首次运行 GUI 时请手动填写 API / 模型配置并另存为配置档。

## 运行环境
- Python 3.9 及以上
- Tkinter（Python 自带，如为精简发行版需单独安装）
- 依赖：`requests`, `pillow`

安装依赖：
```powershell
pip install -r requirements.txt
```

## 快速开始
1. 解压本目录，进入 `release_bundle`。
2. 启动批量 GUI：
   ```powershell
   python tool/ai_image_intent_namer_batch_gui.py
   ```
3. 在 GUI 中：
   - 添加需要处理的 Markdown 文件。
   - 在顶部“AI 参数”区填写 Base URL / API Key / 模型，或点击“API/模型配置...”配置并保存多套档案。
   - 可在单图对话框中使用“翻译 / 归纳”按钮，快速获得上文/下文的译文或摘要。
   - 选择“批量预览（串行）”或“立即应用”即可批量生成候选并写回文档。

## V1 版本亮点
- **翻译 / 归纳助手**：在单图审核对话框顶部新增两个按钮，支持独立的 Base URL / API Key / 模型 / Prompt 配置，返回结果直接展示在弹窗中。
- **兼容多厂商输出**：`call_openai_chat` 新增 `expect_json` 开关与 `flatten_text` 处理，完美兼容 SiliconFlow 等返回 `output_text` 数组的模型，避免翻译结果为空。
- **稳定性回归**：核心脚本恢复为干净的 UTF-8 源文件，所有 GUI 调用均已验证可用。

## 交付物
此 README 所在目录即可视为“V1”发行包；若需分享给其他用户，可直接压缩整个 `release_bundle/` 目录，或使用同目录下的 `AI_Image_Intent_Namer_V1.zip`（见 release_package）。

> 建议将 `release_bundle` 打包后进行数字签名或校验，以便后续版本更新时能够快速比对差异。
