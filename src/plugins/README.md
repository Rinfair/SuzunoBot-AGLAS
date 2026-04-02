# Local Plugins

这里是项目的 NoneBot2 本地插件根目录。

[`bot.py`](../../bot.py) 会优先读取 [`plugin-list.json`](../../plugin-list.json)；如果该文件不存在，则直接扫描本目录。

## 当前插件结构

- [`maimaidx`](./maimaidx) 是当前内嵌的舞萌主插件。
- 运行数据库位于仓库根目录 [`database/`](../../database/)，不放在插件目录内部。
- `maimaidx` 内部当前采用：
  - [`alconna.py`](./maimaidx/alconna.py)：单文件根指令入口
  - [`storage.py`](./maimaidx/storage.py)：数据库与用户自定义资料
  - [`renderer.py`](./maimaidx/renderer.py)：渲染服务入口
  - [`painters/`](./maimaidx/painters)：图片绘制实现
  - 顶部名片板默认使用 `plate_1.png`
  - 旧 `commands/` 包和旧 `database/` 子包已移除，不再参与运行时加载

## 扩展约定

如果新增独立插件，建议直接新增：

- 目录插件：`src/plugins/<plugin_name>/__init__.py`
- 单文件插件：`src/plugins/<plugin_name>.py`

通常不需要修改 [`bot.py`](../../bot.py)。

如果继续扩展 `maimaidx`：

1. 根指令优先继续维护在 [`src/plugins/maimaidx/alconna.py`](./maimaidx/alconna.py)。
2. 只有在明确存在高复用逻辑时，再额外抽取模块。
3. 用户可自定义信息优先放到 [`storage.py`](./maimaidx/storage.py)，不要再新增本地 json。
4. 图片渲染统一走 [`painters/render_core.py`](./maimaidx/painters/render_core.py) 这套 maimaiDX 风格资源与布局。

## 代码来源说明

`maimaidx` 当前采用组合式来源：

- 命令交互、触发方式和多数指令语义：参考 `Rikka`
- 图片资源、卡片布局和主要渲染方案：参考 `Yuri-YuzuChaN/maimaiDX`
- 数据库存储、启动自检、QQ 头像回退、`.plate` 持久化：当前仓库实现

更完整的来源表、指令清单、配置项与排障说明见 [`docs/maimaidx.md`](../../docs/maimaidx.md)。
