# PMO Weekly Tracker

项目进度盘点原型：

- 前端：Vue 3 + Vite
- 后端：FastAPI
- 存储：Apache Doris
- 能力：项目 x 周矩阵、文本导入、模糊项目匹配、AI 总结入口、按项目名/周查询

## 目录

- `server/` FastAPI 接口、导入解析、模糊匹配、Doris 表初始化
- `frontend/` 周盘点界面原型

## 启动

### 1. 后端

```bash
cd /Users/yujia/Desktop/workspace/PMO
python -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt
uvicorn server.main:app --reload --port 8880
```

### 2. 前端

```bash
cd /Users/yujia/Desktop/workspace/PMO/frontend
npm install
npm run dev
```

## 环境变量

根目录新增 `.env`：

```env
MYSQL_HOST=10.26.20.3
MYSQL_PORT=23336
MYSQL_USER=root
MYSQL_PASSWORD=123456
MYSQL_DATABASE=pmo
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
CORS_ORIGINS=http://localhost:5173
```

导入解析默认优先调用 Gemini Structured Output，将周报抽成 JSON 后再入库。官方文档参考：
- [Gemini Structured Outputs](https://ai.google.dev/gemini-api/docs/structured-output)
- [Gemini API reference](https://ai.google.dev/api)
