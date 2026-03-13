# RAGSystem-GeoPLUS

`RAGSystem-GeoPLUS` 是 `RAGSystem` 的 Geo 增强仓库。

定位：

- `RAGSystem`：主线平台仓库
- `RAGSystem-GeoPLUS`：锁步跟随主线的 Geo / 地图 / 时空分析增强仓库

这个仓库不是长期漂移的产品分叉。非 Geo 专属能力应先进入主线，再同步到 GeoPLUS。

## 仓库关系

当前本地远程关系约定为：

- `origin`：`RAGSystem-GeoPLUS`
- `upstream`：`RAGSystem`

同步主线的标准方式：

```powershell
git fetch upstream
git checkout master
git merge upstream/master
git push origin master
```

## 改动边界

应该进入 GeoPLUS 的改动：

- Geo API、Geo Service、Geo Capability
- 地图工作台与图层面板
- 时空分析工具
- 地理多模态落图能力
- 对主线新扩展点的 Geo 侧适配

不应只留在 GeoPLUS 的改动：

- 通用工具协议
- 通用事件协议
- 通用可视化结果协议
- 通用执行与观测能力
- 非 Geo 垂类功能

## 当前系统

仓库当前仍以现有主线代码为基础：

- `backend-fastapi/`：FastAPI 后端，提供 Agent、Execution、MCP、Model Adapter、Files、Vector 等能力
- `frontend-client/`：聊天、执行监控、Agent 配置、MCP 管理前端

## 快速启动

后端：

```powershell
cd backend-fastapi
python main.py
```

前端：

```powershell
cd frontend-client
npm install
npm run dev
```

## 最小配置

建议至少准备：

```powershell
cd backend-fastapi
Copy-Item .env.example .env
Copy-Item model_adapter\configs\providers.yaml.example model_adapter\configs\providers.yaml
Copy-Item agents\configs\agent_configs.yaml.example agents\configs\agent_configs.yaml
Copy-Item mcp\configs\mcp_servers.yaml.example mcp\configs\mcp_servers.yaml
```

可选：

```powershell
Copy-Item config\yaml\config.yaml.example config\yaml\config.yaml
```

## 当前文档

- [docs/README.md](docs/README.md)
- [docs/geoplus/README.md](docs/geoplus/README.md)
- [docs/geoplus/REPO_GOVERNANCE.md](docs/geoplus/REPO_GOVERNANCE.md)
- [docs/geoplus/MAINLINE_EXTENSION_POINTS.md](docs/geoplus/MAINLINE_EXTENSION_POINTS.md)
- [backend-fastapi/agents/README.md](backend-fastapi/agents/README.md)
- [backend-fastapi/model_adapter/README.md](backend-fastapi/model_adapter/README.md)
- [frontend-client/README.md](frontend-client/README.md)
