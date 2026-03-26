# SuzunoBot-AGLAS

本仓库已重构为以 `maimai` 为核心的 NoneBot2 项目。

`maimai` 相关实现已基于 [Moemu/Nonebot-Plugin-Rikka](https://github.com/Moemu/Nonebot-Plugin-Rikka) 重写并直接嵌入本地 `src/plugins/maimaidx/`，不再作为独立第三方插件存在。旧项目中的无关插件、通用库和历史功能模块已删除。

同时保留了标准的本地插件目录加载方式，后续如果需要继续开发新功能，可以直接在 `src/plugins/` 下新增新的插件目录或单文件插件，无需改动当前 `maimai` 主体结构。

## 目录

- `bot.py`：NoneBot 启动入口
- `plugin-list.json`：扫描本地 `src/plugins`
- `src/plugins/maimaidx/`：嵌入后的 maimai 主插件，包含命令、数据库、渲染、迁移脚本与数据更新逻辑
- `src/plugins/README.md`：后续新增本地插件的放置约定
- `static/`：运行时静态资源目录

## Step 1. 安装依赖

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## Step 2. 准备资源与配置

1. 运行时静态资源目录为项目根目录 `static/`。
2. 如需补充或覆盖资源包，可使用 `Resource.7z` 解压到 `static/`。
   备用链接：<https://cloud.yuzuchan.moe/f/nXt6/Resource.7z>
3. 该备用链接当前会跳转到带签名的下载地址，如遇到临时 `404`，通常是签名地址失效，重新打开原链接再试即可。
4. 当前渲染链路已对部分缺失素材做兼容回退，资源包不完整时仍可启动，但渲染效果会以现有本地资源为准。
5. 如需完整查分能力，请在 `.env` 中配置：
   `lxns_developer_api_key`
   `divingfish_developer_api_key`
   `enable_arcade_provider`
6. 默认已在 `.env` 中设置 `ALEMBIC_STARTUP_CHECK=false`，首次启动会以非交互方式同步数据库结构，避免 `python bot.py` 卡在迁移确认提示。

## Step 3. 运行项目

```bash
python bot.py
```

## 首次使用建议

1. 如需显式管理数据库迁移，可按 `nonebot-plugin-orm` 的方式执行升级。本仓库已包含 `src/plugins/maimaidx/migrations/`。
2. 启动后使用超级用户执行：

```text
.update songs
.update alias
.update chart
```

## 说明

- 渲染链路基于 Rikka 的 `painters` / `renderer` 结构迁移，并针对本地资源做了兼容处理。
- 成绩导入、发票、解锁等扩展流程仍保留了接口代理，后续如需继续开发，可再把对应实现嵌入本项目或按需提供本地扩展模块。
- 当前项目结构已经恢复为标准 NoneBot2 本地插件工程，可以继续增加新的插件模块。
