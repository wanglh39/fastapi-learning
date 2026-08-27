# 阶段 9 · 沉淀与部署

!!! info "本章定位"
    收尾：完善文档站、补齐笔记深度、画架构图、配置 CI/CD 与部署方案，让学习成果成书上线。

---

## 本章学习目标

读完本章后，你应当能够：

1. 完善 MkDocs 文档站导航与首页
2. 保证每章 ≥ 700 行深度，补齐初学者友好解释
3. 画出整体架构图与造轮子类图
4. 配置 GitHub Actions 自动构建文档站并发布到 GitHub Pages
5. 编写 Dockerfile 与部署方案

---

## 小节目录

1. [9.1 文档站完善](#91-文档站完善)
2. [9.2 笔记深度校验](#92-笔记深度校验)
3. [9.3 架构图与类图](#93-架构图与类图)
4. [9.4 GitHub Pages 自动部署](#94-github-pages-自动部署)
5. [9.5 Docker 容器化](#95-docker-容器化)
6. [9.6 部署方案对比](#96-部署方案对比)
7. [9.7 CI/CD 流水线](#97-cicd-流水线)
8. [小结与全篇收官](#小结与全篇收官)

---

## 9.1 文档站完善

待补充：补全 mkdocs.yml 导航、首页 hero、各章节间的前后导航、版本化配置。

---

## 9.2 笔记深度校验

待补充：逐章检查是否 ≥ 700 行、是否面向初学者、代码示例是否可运行、图表是否到位。**约束：深度与数量只增不减**，发现不足则扩充而非删减。

---

## 9.3 架构图与类图

待补充：用 mermaid 画出：

- mini-fastapi 整体类图（MiniFastAPI / Router / Route / Depends / Response 关系）
- 请求分发序列图
- business-app 分层架构图
- 部署拓扑图

---

## 9.4 GitHub Pages 自动部署

待补充：`.github/workflows/docs.yml` 在 push 到 main 时自动 `mkdocs build` 并部署到 GitHub Pages。讲解 workflow 各步骤。

---

## 9.5 Docker 容器化

待补充：多阶段构建 Dockerfile——builder 阶段用 `uv sync` 装依赖，runtime 阶段只拷产物，镜像体积优化。

---

## 9.6 部署方案对比

待补充：对比 uvicorn 裸跑、gunicorn + uvicorn workers、Docker Compose、K8s 四种方案的适用场景与取舍。

---

## 9.7 CI/CD 流水线

待补充：GitHub Actions 流水线——lint（ruff）→ typecheck（mypy）→ test（pytest）→ build docs → deploy Pages。每个阶段的作用与失败处理。

---

## 小结与全篇收官

待补充：回顾从 ASGI 地基到业务部署的完整路径，总结 FastAPI 设计哲学的核心洞察（类型优先、组合优先、异步原生），给出后续进阶方向（性能调优、WebSocket、后台任务、LangChain 集成等）。

---

!!! todo "待填充标记说明"
    本文件为大纲骨架，标注「待补充」处为后续要展开的内容点。每个待补充点都已规划好要讲的核心问题与示例方向，填充时直接展开即可达到 ≥ 700 行深度。**笔记深度与数量只增不减**，本骨架的小节结构在填充时只会扩充不会删减。