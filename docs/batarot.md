# batarot

`batarot` 是当前仓库内置的碧蓝档案塔罗牌独立插件，目录位于 [`src/plugins/batarot`](../src/plugins/batarot)。

## 来源与接入结论

- 上游仓库：`Perseus037/nonebot_plugin_batarot`
- 上游 README 声明的核心能力与实际代码一致，主要包括 4 个命令、4 份数据 JSON 和 22 张本地塔罗牌图片
- 上游 `pyproject.toml` 中声明了 `nonebot-plugin-htmlrender`、`nonebot-plugin-apscheduler`、`aiohttp` 等依赖，但当前代码路径里并未直接使用
- 上游运行时真正依赖的核心点主要是：
  - `nonebot2`
  - `nonebot-adapter-onebot`
  - `Pillow`
  - 原仓库额外依赖 `nonebot_plugin_saa` 做多适配器发送

本仓库接入时做了以下本地化整理：

- 目录名改为 `batarot`，不保留 `nonebot_plugin_*` 外部包命名
- 去掉 `nonebot_plugin_saa` 依赖，改为当前项目已使用的 OneBot V11 原生消息发送
- 保留上游本地图片与 JSON 数据文件，继续按独立模块加载
- 修复 `ba塔罗牌解读` 无参数或带空格参数时的解析边界问题
- 修复图片缺失时 `MessageFactory` 与字符串混用导致的异常分支不稳定问题
- 将牌阵牌位说明改为按牌阵模板顺序取值，避免同一牌阵内位置描述重复

## 指令

- `ba塔罗牌`
- `ba占卜`
- `ba运势`
- `ba塔罗牌解读`
- `ba塔罗牌解读 <编号或中文名>`

兼容上游保留的别名：

- `batarot`
- `divination`
- `fortune`
- `reading`
- `tarot`
- `塔罗牌`
- `占卜`
- `运势`
- `塔罗牌解读`

## 配置

当前仅保留一项插件配置：

```env
BATAROT_FORWARD_MODE=false
```

- `false`：群聊中的 `ba占卜` 优先使用 OneBot 合并转发
- `true`：群聊和私聊都改为逐条普通消息发送

## 测试

加载与 I/O 烟雾测试脚本：

```bash
python scripts/batarot_smoke_test.py
```

测试会覆盖：

- 项目级插件加载
- 塔罗数据、牌阵数据、运势数据与本地图片完整性
- `ba塔罗牌`
- `ba占卜`
- `ba运势`
- `ba塔罗牌解读`
- 无效输入的错误分支
