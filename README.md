# SuzunoBot-AGLAS

本仓库当前以 `src/plugins/maimaidx` 为核心，并额外内置：

- `src/plugins/dashboard`：项目级帮助、信息与系统状态模块
- `src/plugins/batarot`：独立塔罗牌插件

当前实现的关键点：

- 指令触发统一收敛到单文件 [`src/plugins/maimaidx/alconna.py`](src/plugins/maimaidx/alconna.py)，逻辑风格直接参考 `Rikka`。
- 图片渲染统一使用 `maimaiDX` 资源与布局方案。
- 数据库存储统一到单文件 [`src/plugins/maimaidx/storage.py`](src/plugins/maimaidx/storage.py)。
- 顶部名片板默认使用 `plate_1.png`，未设置或读取失败时自动回退到 `plate_1.png`。
- `.maistatus` 的文本服务器状态检测依赖可选插件 `nonebot-plugin-rikka-extra`；未安装时会跳过文本状态，只返回状态页截图。
- 运行数据库固定在仓库根目录 [`database/`](database/) 下，便于管理和重置。

完整结构、指令、配置项、排障和代码来源见 [`docs/maimaidx.md`](docs/maimaidx.md)。

## 目录

- [`bot.py`](bot.py)：NoneBot 启动入口
- [`plugin-list.json`](plugin-list.json)：本地插件根目录声明；缺失时回退为扫描 `src/plugins/`
- [`src/plugins/dashboard`](src/plugins/dashboard)：项目级帮助与状态模块
- [`src/plugins/maimaidx`](src/plugins/maimaidx)：舞萌主插件
- [`src/plugins/batarot`](src/plugins/batarot)：碧蓝档案塔罗牌插件
- [`database/`](database/)：运行数据库目录，默认生成 `suzunobot.sqlite3`
- [`scripts/dashboard_smoke_test.py`](scripts/dashboard_smoke_test.py)：通用模块烟雾测试
- [`scripts/maimaidx_smoke_test.py`](scripts/maimaidx_smoke_test.py)：插件烟雾测试
- [`scripts/batarot_smoke_test.py`](scripts/batarot_smoke_test.py)：塔罗牌插件烟雾测试
- [`docs/dashboard.md`](docs/dashboard.md)：通用模块说明
- [`docs/maimaidx.md`](docs/maimaidx.md)：完整文档
- [`docs/batarot.md`](docs/batarot.md)：塔罗牌插件接入说明

## Step 1. 安装依赖

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## Step 2. 准备资源与配置

1. 运行时静态资源目录为项目根目录 `static/`。
2. 如需补充或覆盖资源包，可将 `Resource.7z` 解压到 `static/`。
3. 备用下载链接：[Resource.7z](https://cloud.yuzuchan.moe/f/nXt6/Resource.7z)
4. 数据库默认写入 `database/suzunobot.sqlite3`。
5. 插件启动时会自动：
   - 检查并修复数据库结构
   - 迁移旧版 `data/maimaidx/profile.json`
   - 在本地空曲库时自动初始化歌曲与别名数据

`.env` 建议至少包含：

```env
ENVIRONMENT=prod
COMMAND_START=["", ".", "/"]
HOST=127.0.0.1
PORT=10219
NICKNAME=["SuzunoBot-AGLAS"]
SQLALCHEMY_DATABASE_URL=sqlite+aiosqlite:///./database/suzunobot.sqlite3
ALEMBIC_STARTUP_CHECK=false
```

完整参数表见 [`docs/maimaidx.md`](docs/maimaidx.md)。

## Step 3. 运行项目

```bash
python bot.py
```

正常情况下会看到：

- `Succeeded to load plugin "maimaidx"`
- `检查 maimaidx 数据库结构中...`
- `更新乐曲缓存中...`
- `Application startup complete`
- `Uvicorn running on http://127.0.0.1:10219`

## 测试

快速回归：

```bash
python scripts/dashboard_smoke_test.py
python scripts/maimaidx_smoke_test.py
```

连同更新流程一起验证：

```bash
python scripts/maimaidx_smoke_test.py --with-update
```

当前烟雾测试会覆盖：

- 数据库结构检查与空库自动初始化
- 歌曲查询与别名查询
- `B50` / 成绩列表 / 单曲图渲染
- 水鱼 / maimai.py / 落雪公开链路
- 运势、进度、推荐、分析、状态页截图

塔罗牌插件加载与 I/O 验证：

```bash
python scripts/batarot_smoke_test.py
```

## 结构概览

- `alconna.py`：单文件指令入口，统一定义所有根指令 matcher、处理函数和 OneBot V11 图片回复逻辑
- `storage.py`：ORM 表定义、CRUD、自定义资料和启动自检
- `renderer.py`：渲染服务入口，负责封面、头像、名牌板和图片输出
- `painters/render_core.py`：maimaiDX 风格公共渲染核心
- `score/providers/`：落雪 / 水鱼 / maimai.py 查分实现
- `functions/`：推荐、进度、运势、分析、状态截图等业务逻辑

## 代码来源

本仓库当前实现是组合式整理，不再保留“兼容层”命名：

- 指令触发逻辑、指令语义和多数业务流程：参考 `Rikka`
- 图片素材、卡片布局和主要绘制方案：参考 `Yuri-YuzuChaN/maimaiDX`
- 当前仓库补充内容：数据库自检、QQ 头像回退、`.plate` 持久化、NoneBot 启动集成、烟雾测试

更细的文件级来源说明见 [`docs/maimaidx.md`](docs/maimaidx.md)。
