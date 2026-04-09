# dashboard

`dashboard` 是当前仓库的通用信息模块，目录位于 [`src/plugins/dashboard`](../src/plugins/dashboard)。

## 功能

- 统一接管项目级帮助命令
- 输出项目信息
- 输出主机负载与进程状态
- 输出已加载插件列表
- 提供简单存活检测

## 指令

- `help` / `帮助`
- `项目信息`
- `系统状态`
- `插件列表`
- `ping`

## 模板与数据文件

所有聊天输出都通过独立模板与数据文件生成，修改文案或排版时不需要改 Python 源码：

- 模板目录：[`src/plugins/dashboard/templates`](../src/plugins/dashboard/templates)
- 数据目录：[`src/plugins/dashboard/data`](../src/plugins/dashboard/data)

当前文件说明：

- [`about.txt`](../src/plugins/dashboard/templates/about.txt)：项目信息输出模板
- [`help.txt`](../src/plugins/dashboard/templates/help.txt)：帮助总览模板
- [`help_section.txt`](../src/plugins/dashboard/templates/help_section.txt)：帮助分组模板
- [`help_item.txt`](../src/plugins/dashboard/templates/help_item.txt)：帮助条目模板
- [`status.txt`](../src/plugins/dashboard/templates/status.txt)：主机负载模板
- [`plugins.txt`](../src/plugins/dashboard/templates/plugins.txt)：插件列表模板
- [`plugin_item.txt`](../src/plugins/dashboard/templates/plugin_item.txt)：插件条目模板
- [`ping.txt`](../src/plugins/dashboard/templates/ping.txt)：存活检测模板
- [`project.json`](../src/plugins/dashboard/data/project.json)：项目名称、作者、仓库等元数据
- [`commands.json`](../src/plugins/dashboard/data/commands.json)：帮助命令目录

模板和 JSON 数据都会在每次调用命令时重新读取，因此直接编辑文件后即可生效。

## 配置

可选环境变量：

```env
DASHBOARD_DISK_USAGE_PATH=./
```

用于 `系统状态` 命令统计磁盘占用时指定目标路径；默认监控仓库根目录。

## 测试

```bash
python scripts/dashboard_smoke_test.py
```

覆盖项：

- 项目级插件加载
- 模板与数据文件完整性
- `help`
- `项目信息`
- `系统状态`
- `插件列表`
- `ping`
