# PMO Weekly Tracker

项目进度盘点原型：

- 前端：Vue 3 + Vite
- 后端：FastAPI
- 存储：MySQL
- 能力：项目 x 周矩阵、全年矩阵、月度盘点、JSON 导入、模糊项目匹配、多模型配置、编辑与删除

## 目录

- `server/` FastAPI 接口、导入解析、模糊匹配、MySQL 表初始化
- `frontend/` 周盘点界面原型
- `scripts/` 初始化与启动脚本

## 启动

### 1. 准备配置

```bash
chmod +x init.sh start.sh scripts/init.sh scripts/start.sh
cp .env.example .env
vi .env
```

把 `.env` 里的 MySQL 密码和模型 API Key 改成服务器真实配置。

### 2. 初始化

```bash
./init.sh
```

如果直接执行 `./init.sh` 时还没有 `.env`，脚本会自动生成 `.env` 并提示你先补配置。

### 3. 启动

```bash
./start.sh
```

前端访问：`http://服务器IP:28822`

后端接口：`http://服务器IP:28823/api`

## 环境变量

根目录新增 `.env`：

```env
MYSQL_HOST=10.26.20.3
MYSQL_PORT=23336
MYSQL_USER=root
MYSQL_PASSWORD=你的密码
MYSQL_DATABASE=pmo
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
CORS_ORIGINS=http://localhost:28822
```

## 部署

服务器上拉代码后执行：

```bash
git clone git@github.com:wangyujia2023/PMO.git
cd PMO
chmod +x init.sh start.sh scripts/init.sh scripts/start.sh
cp .env.example .env
vi .env
./init.sh
./start.sh
```

默认端口：

- 前端：`28822`
- 后端：`28823`

如果要改端口：

```bash
FRONTEND_PORT=28822 BACKEND_PORT=28823 ./start.sh
```
