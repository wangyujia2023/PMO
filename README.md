# PMO Weekly Tracker

项目进度盘点原型：

- 前端：Vue 3 + Vite
- 后端：FastAPI
- 存储：MySQL
- 能力：项目 x 周矩阵、JSON 导入、模糊项目匹配、按项目名/周查询、编辑与删除

## 目录

- `server/` FastAPI 接口、导入解析、模糊匹配、MySQL 表初始化
- `frontend/` 周盘点界面原型
- `scripts/` 初始化与启动脚本

## 启动

### 1. 初始化

```bash
chmod +x scripts/init.sh scripts/start.sh
./scripts/init.sh
```

### 2. 启动

```bash
./scripts/start.sh
```

前端访问：`http://服务器IP:28822`

后端接口：`http://服务器IP:28823/api`

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
CORS_ORIGINS=http://localhost:28822
```

导入解析默认优先调用 Gemini Structured Output，将周报抽成 JSON 后再入库。官方文档参考：
- [Gemini Structured Outputs](https://ai.google.dev/gemini-api/docs/structured-output)
- [Gemini API reference](https://ai.google.dev/api)
