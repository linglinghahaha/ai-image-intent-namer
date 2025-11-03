# AI 图片意图命名桌面应用（Electron + React + FastAPI）

该目录包含一个全新的桌面应用脚手架，前端采用 Electron + React + Vite，界面直接复用了 Figma 导出的组件；后端提供 FastAPI 服务并复用现有的 `ai_image_intent_namer` 逻辑。整体结构如下：

```
desktop_app/
├── backend/               # Python FastAPI 服务
│   ├── main.py            # 核心 API 定义
│   └── requirements.txt   # 后端依赖清单
└── frontend/              # Electron + React 前端
    ├── package.json       # npm scripts、依赖与 Electron Builder 配置
    ├── index.html         # Vite 入口
    ├── tsconfig.json      # TypeScript 配置（含路径别名）
    ├── vite.config.ts     # Vite 构建配置
    ├── electron/          # Electron 主进程与打包脚本
    │   ├── main.ts        # Electron 主进程入口
    │   └── build.ts       # 使用 electron-builder 的打包脚本
    └── src/
        ├── main.tsx       # React 应用入口，注入后端 Provider
        ├── styles.css     # 全局补充样式
        ├── figma/         # 复制自 `.vscode/figma/src` 的界面代码
        ├── services/api.ts
        ├── providers/BackendProvider.tsx
        └── hooks/useBackend.ts
```

## 后端：FastAPI 包装现有 Python 能力

- `desktop_app/backend/main.py` 暴露了 `/api/v1/*` 端点，包括健康检查、配置文件读写、Markdown 预览、候选生成、命名写回以及通用文本处理。
- 导入路径通过 `sys.path` 指向 `tool/` 目录，直接重用 `ai_image_intent_namer` 里的 `Config`, `process_document`, `build_attachment_plan` 等函数。
- 运行方式：

```bash
cd desktop_app/backend
python -m venv .venv
.venv\Scripts\activate        # Windows Powershell
pip install -r requirements.txt
uvicorn desktop_app.backend.main:app --reload --port 8000
```

## 前端：Electron + React + Vite

- 前端将 Figma 导出的组件完整复制到 `src/figma`，避免改动原始设计稿。
- `BackendProvider` 暴露统一的 `apiClient`（封装 `fetch`），并在启动时探测 FastAPI 服务；`App.tsx` 中的批量预览、写回流程已经对接新的 API（若后端不可用会自动回退到 Mock 数据）。
- npm 常用脚本：

```bash
cd desktop_app/frontend
npm install

# 开发模式：并行启动 Vite 与 Electron
npm run dev

# 仅构建前端静态资源
npm run build

# TypeScript 类型检查
npm run typecheck

# 产出桌面安装包（需要安装 electron-builder 依赖）
npm run package
```

> **提示**  
> - Electron 打包脚本会尝试将 `electron/main.ts` 编译为 `electron/main.js` 后再调用 `electron-builder`。如需更精细的安装包配置，可继续扩展 `electron/build.ts` 中的 `build` 配置。
> - React 侧目前已接入批量预览与写回的 REST 调用；翻译、归纳、候选生成等细化操作可在 `apiClient` 中继续扩展对应接口，然后在 Figma 组件里调用。

## 后续集成建议

1. **预设同步**：当前 `usePresets` 仍使用本地 `localStorage`。可通过 Backend 提供的 `/profiles`、`/templates` 接口，实现团队共享配置。
2. **候选管理与复审**：`ImageReviewPanel` 仍基于示例数据，可引入 `apiClient.generateCandidates`、`apiClient.processText` 等方法，把候选生成、翻译、归纳统一交由 FastAPI。
3. **发布流程**：结合 GitHub Actions 或 Azure DevOps，可分别为 Windows / macOS / Linux 输出安装包，后续也可以引入自动更新。

该脚手架让 Python AI 能力与现代桌面 UI 解耦，前后端通过 HTTP 通信，可在不改变核心算法的前提下快速迭代用户体验。欢迎继续根据业务需求补充接口与 UI 动效。
