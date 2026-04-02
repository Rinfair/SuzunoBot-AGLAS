# maimaidx 文档

## 1. 概览

当前插件位于 [`src/plugins/maimaidx`](../src/plugins/maimaidx)。

当前结构原则：

- 所有根指令统一收敛到单文件 [`alconna.py`](../src/plugins/maimaidx/alconna.py)。
- 数据库存储、自定义资料、启动修复统一收敛到 [`storage.py`](../src/plugins/maimaidx/storage.py)。
- 图片渲染全部收敛到 [`painters/render_core.py`](../src/plugins/maimaidx/painters/render_core.py) 与同目录下的少量场景文件。
- 仓库根目录 [`database/`](../database/) 用于存放运行数据库文件，便于重置。
- 旧的 `commands/` 包、旧 `database/` 子包以及旧 `painters/_base.py` / `_config.py` 已移除，不再参与运行时加载。

## 2. 启动流程

1. [`bot.py`](../bot.py) 读取根目录 `.env`，注册 OneBot V11，按 `plugin-list.json` 或 `src/plugins/` 加载插件。
2. [`src/plugins/maimaidx/__init__.py`](../src/plugins/maimaidx/__init__.py) 加载 [`alconna.py`](../src/plugins/maimaidx/alconna.py) 与 [`storage.py`](../src/plugins/maimaidx/storage.py)。
3. 启动钩子执行 [`ensure_database_schema`](../src/plugins/maimaidx/storage.py)：
   - 创建缺失表
   - 自动补齐缺失列
   - 迁移旧版 `data/maimaidx/profile.json`
4. 启动钩子刷新歌曲缓存；如果本地歌曲库为空，则自动初始化歌曲和别名数据。

## 3. 文件结构与职责

### 3.1 插件入口

- [`src/plugins/maimaidx/__init__.py`](../src/plugins/maimaidx/__init__.py)
  - 插件入口
  - 启动时数据库自检
  - 空库自动初始化
  - 歌曲缓存预热

- [`src/plugins/maimaidx/alconna.py`](../src/plugins/maimaidx/alconna.py)
  - 单文件指令入口
  - 统一定义全部根指令 matcher 与 handler
  - 统一处理 OneBot V11 私聊/群聊图片回复
  - 保留 `Rikka` 风格命令语义与交互方式

- [`src/plugins/maimaidx/config.py`](../src/plugins/maimaidx/config.py)
  - 插件配置定义

- [`src/plugins/maimaidx/utils.py`](../src/plugins/maimaidx/utils.py)
  - 日志初始化
  - 歌曲查找
  - 私聊/群聊回复段处理

### 3.2 存储层

- [`src/plugins/maimaidx/storage.py`](../src/plugins/maimaidx/storage.py)
  - ORM 表定义
  - 绑定信息读写
  - 歌曲缓存与曲库 CRUD
  - 用户自定义资料（当前为 `plate_number`，默认 `plate_1`）
  - 启动时表结构修复
  - 旧配置迁移

当前主要数据表：

- `maimaidx_userbindinfo`
- `maimaidx_maisong`
- `maimaidx_maisongalias`
- `maimaidx_playcount`
- `maimaidx_userprofile`

### 3.3 渲染层

- [`src/plugins/maimaidx/renderer.py`](../src/plugins/maimaidx/renderer.py)
  - 渲染服务入口
  - 封面补齐
  - 头像/姓名框/名牌板资源检查
  - QQ 头像回退

- [`src/plugins/maimaidx/painters/render_core.py`](../src/plugins/maimaidx/painters/render_core.py)
  - maimaiDX 风格公共资源加载
  - 卡片绘制
  - 顶部资料区绘制
  - 背景、字体、图标、DX 星标、Rank 资源处理

- [`src/plugins/maimaidx/painters/b50.py`](../src/plugins/maimaidx/painters/b50.py)：Best/AP/PC/N50 主图
- [`src/plugins/maimaidx/painters/score.py`](../src/plugins/maimaidx/painters/score.py)：成绩列表、推分推荐
- [`src/plugins/maimaidx/painters/song.py`](../src/plugins/maimaidx/painters/song.py)：单曲详情图
- [`src/plugins/maimaidx/painters/process.py`](../src/plugins/maimaidx/painters/process.py)：等级/牌子进度图
- [`src/plugins/maimaidx/painters/analysis.py`](../src/plugins/maimaidx/painters/analysis.py)：成分分析图
- [`src/plugins/maimaidx/painters/trend.py`](../src/plugins/maimaidx/painters/trend.py)：趋势图
- [`src/plugins/maimaidx/painters/utils.py`](../src/plugins/maimaidx/painters/utils.py)：文本宽度计算、字体绘制、图片字节流

### 3.4 查分与业务逻辑

- [`src/plugins/maimaidx/score/_schema.py`](../src/plugins/maimaidx/score/_schema.py)：统一数据结构
- [`src/plugins/maimaidx/score/providers/diving_fish.py`](../src/plugins/maimaidx/score/providers/diving_fish.py)：水鱼接口
- [`src/plugins/maimaidx/score/providers/lxns.py`](../src/plugins/maimaidx/score/providers/lxns.py)：落雪接口
- [`src/plugins/maimaidx/score/providers/maimai.py`](../src/plugins/maimaidx/score/providers/maimai.py)：maimai.py 聚合能力
- [`src/plugins/maimaidx/functions/`](../src/plugins/maimaidx/functions)：运势、推荐、进度、状态、分析等业务逻辑
- [`src/plugins/maimaidx/updater/songs.py`](../src/plugins/maimaidx/updater/songs.py)：曲库与别名更新
- [`src/plugins/maimaidx/updater/resources.py`](../src/plugins/maimaidx/updater/resources.py)：资源缺失补齐

## 4. 功能代码来源

| 功能 | 主要文件 | 代码来源 |
| --- | --- | --- |
| 指令语义、查分使用方式、绑定/解绑/默认源等交互逻辑 | `alconna.py` | 以 `Rikka` 的命令设计、触发方式和交互习惯为参考，在当前仓库内整合为单文件入口 |
| `B50`、成绩列表、单曲、进度等图片布局与静态资源调用 | `painters/render_core.py`、`painters/*.py` | 以 `Yuri-YuzuChaN/maimaiDX` 的静态资源、布局比例和绘制方案为参考，并适配当前数据结构 |
| QQ 头像回退、`.plate` 持久化、自动建表、空库自动初始化 | `storage.py`、`renderer.py`、`__init__.py` | 当前仓库新增 |
| 落雪/水鱼/maimai.py 查分整合 | `score/providers/*.py` | 基于现有仓库实现整理，保留原有 provider 适配方式 |
| 趋势图、成分分析、运势、状态页截图 | `functions/*.py`、`painters/analysis.py`、`painters/trend.py` | 当前仓库业务逻辑，图像风格与渲染入口已统一到现结构 |

参考项目：

- [Yuri-YuzuChaN/maimaiDX](https://github.com/Yuri-YuzuChaN/maimaiDX)
- [Moemu/Nonebot-Plugin-Rikka](https://github.com/Moemu/Nonebot-Plugin-Rikka)

## 5. 指令清单

以下根指令当前均由 [`src/plugins/maimaidx/alconna.py`](../src/plugins/maimaidx/alconna.py) 定义：

### 5.1 帮助与信息

| 指令 | 示例 | 说明 |
| --- | --- | --- |
| `.help` | `.help` | 帮助信息 |
| `.rikka` | `.rikka` | 插件状态信息 |

### 5.2 账号与个性化

| 指令 | 示例 | 说明 |
| --- | --- | --- |
| `.bind` | `.bind lxns <token>` | 绑定落雪或水鱼 |
| `.unbind` | `.unbind lxns` | 解绑查分器 |
| `.source` | `.source divingfish` | 设置默认查分器 |
| `.plate` | `.plate 10` | 设置顶部名牌板 |

说明：

- 未设置 `.plate` 时默认使用 `plate_1.png`
- 即使数据库中的 `plate_number` 缺失、非法或读取失败，渲染也会回退到 `plate_1.png`

### 5.3 成绩与图片

| 指令 | 示例 | 说明 |
| --- | --- | --- |
| `.b50` | `.b50` | Best 50 |
| `.ap50` | `.ap50` | AP50 |
| `.r50` | `.r50` | Recent 50 |
| `.pc50` | `.pc50` | 游玩次数 Top 50 |
| `.n50` | `.n50` | 拟合系数 Top 50 |
| `.score` | `.score 8` | 单曲成绩 |
| `.scorelist` | `.scorelist 12+` | 条件成绩列表 |
| `.trend` | `.trend` | DX Rating 趋势图 |

### 5.4 歌曲与别名

| 指令 | 示例 | 说明 |
| --- | --- | --- |
| `.minfo` | `.minfo ouroboros` | 歌曲详情 |
| `.random` | `.random 13+` | 随机抽歌 |
| `.alias` | `.alias query 群青讃歌` | 别名管理 |

### 5.5 进度、分析、推荐

| 指令 | 示例 | 说明 |
| --- | --- | --- |
| `等级进度` | `.13+ sss 进度` | 等级进度 |
| `牌子进度` | `.真极进度 难` | 牌子进度 |
| `成分分析` | `.analysis` | 成分分析 |
| `推分推荐` | `.recommend` | 推分推荐 |
| `今日舞萌` | `今日舞萌` | 今日运势 |
| `舞萌状态` | `舞萌状态` | 状态页截图 |

### 5.6 导入与维护

| 指令 | 示例 | 说明 |
| --- | --- | --- |
| `.import` | `.import <qr>` | 导入成绩或同步 |
| `.ticket` | `.ticket <qr>` | 发六倍票 |
| `.logout` | `.logout <qr>` | 强制登出 |
| `.unlock` | `.unlock <qr>` | 解锁 |
| `.update` | `.update songs` | 更新曲库、别名或 chart |

## 6. `.env` 参数

### 6.1 NoneBot / 项目级

| 参数名 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `ENVIRONMENT` | `str` | `prod` | NoneBot 环境 |
| `COMMAND_START` | `list[str]` | `["", ".", "/"]` | 允许 `.help`、`/help` 和无前缀中文指令 |
| `HOST` | `str` | `127.0.0.1` | 服务监听地址 |
| `PORT` | `int` | `10219` | 服务端口 |
| `SUPERUSERS` | `list[str]` | `[]` | 超级用户列表 |
| `NICKNAME` | `list[str]` | `["SuzunoBot-AGLAS"]` | Bot 名称 |
| `SQLALCHEMY_DATABASE_URL` | `str` | `sqlite+aiosqlite:///./database/suzunobot.sqlite3` | ORM 数据库地址 |
| `ALEMBIC_STARTUP_CHECK` | `bool` | `false` | 关闭交互式迁移检查 |

### 6.2 `maimaidx` 插件级

| 参数名 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `log_level` | `str` | `"debug"` | 插件日志等级 |
| `add_alias_need_admin` | `bool` | `true` | 添加别名是否要求管理员 |
| `static_resource_path` | `str` | `"<repo>/static"` | 静态资源目录 |
| `lxns_developer_api_key` | `str \| null` | `null` | 落雪开发者密钥 |
| `divingfish_developer_api_key` | `str \| null` | `null` | 水鱼开发者密钥 |
| `enable_arcade_provider` | `bool` | `false` | 是否启用机台源 |
| `arcade_provider_http_proxy` | `str \| null` | `null` | 机台源代理 |
| `maistatus_url` | `str \| null` | `"https://status.snowy.moe/status/maimai"` | 状态页地址 |
| `scorelist_bg` | `str \| null` | `null` | 成绩图自定义背景 |
| `scorelist_font_main` | `str \| null` | `null` | 成绩图主字体 |
| `scorelist_font_color` | `tuple[int,int,int,int]` | `(124, 129, 255, 255)` | 成绩图主文字颜色 |
| `scorelist_font_num` | `str \| null` | `null` | 成绩图数字字体 |
| `scorelist_element_opacity` | `float` | `1.0` | 成绩图元素透明度 |

### 6.3 烟雾测试附加参数

| 参数名 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `LXNS_TEST_FRIEND_CODE` | `str \| null` | `null` | 落雪成功链路测试用好友码 |
| `DIVINGFISH_TEST_IMPORT_TOKEN` | `str \| null` | `null` | 水鱼私有成绩测试用导入 token |
| `ARCADE_QR_DATA` | `str \| null` | `null` | 机台源测试用二维码数据 |

## 7. 基础排障

### 7.1 指令无法触发

- 确认 `.env` 中 `COMMAND_START=["", ".", "/"]`
- 当前已验证 `.b50`、`.minfo 8`、`.score 8`、`.scorelist 12+`、`.plate 1`、`.13+ sss 进度`、`.真极进度 难`、`今日舞萌` 可解析
- 当前运行时只加载 [`src/plugins/maimaidx/alconna.py`](../src/plugins/maimaidx/alconna.py) 这一套 matcher

### 7.2 私聊无法回复

- 私聊场景不再追加 `@用户`
- 群聊场景仍会按需要返回 `@用户`
- OneBot V11 下，图片命令会直接走适配器原生图片消息发送，而不是 `UniImage`
- 本地已模拟验证 `.b50`、`.minfo`、`.score`、`.plate`、`今日舞萌` 等图片命令的私聊与群聊回复链路
- 如果私聊仍无响应，优先检查适配器与上报日志，而不是命令前缀

### 7.3 曲库为空或按标题搜歌失败

- 插件启动时会自动检查空曲库并初始化
- 也可以手动执行 `.update songs` 和 `.update alias`
- 如需彻底重置，停止机器人后删除 [`database/suzunobot.sqlite3`](../database/suzunobot.sqlite3)

### 7.4 图片资源异常

- 资源目录必须是 `static/`
- 缺失资源可使用备用链接：[Resource.7z](https://cloud.yuzuchan.moe/f/nXt6/Resource.7z)
- 头像资源缺失时会自动尝试使用 QQ 头像

### 7.5 状态页截图失败

- 先执行 `python -m playwright install chromium`
- 检查 `maistatus_url` 是否可访问

### 7.6 数据库异常

- 检查 `.env` 中 `SQLALCHEMY_DATABASE_URL`
- 检查仓库根目录 `database/` 是否存在
- 启动时会自动建表和补列；如果文件损坏，删除 sqlite 文件后重启即可
- 用户自定义名片板读取失败时，图片渲染会自动回退到 `plate_1.png`，不会中断 `B50` 等图片命令
- 当前已排查其他命令的 ORM 访问路径，未发现第二条与 `plate_number` 相同的异步懒加载风险链路

## 8. 当前验证

本地已完成：

- `python -m compileall src\plugins\maimaidx scripts\maimaidx_smoke_test.py`
- `python scripts\maimaidx_smoke_test.py`
- OneBot V11 私聊/群聊图片发送模拟
- 常用根指令解析回归：`.b50`、`.minfo 8`、`.score 8`、`.scorelist 12+`、`.plate 1`、`.maistatus`、`.trend`、`.recommend`、`.random expert 12+`、`今日舞萌`、`.13+ sss 进度`、`.真极进度 难`

结果：

- 插件加载成功
- 数据库结构检查成功
- 空库自动初始化成功
- 烟雾测试公开链路通过
- 私聊与群聊图片回复链路通过模拟验证
