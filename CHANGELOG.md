# StarBot_AGLAS 更新日志 Changelog

## [v2.0.1 Beta 0.93]

- 自KibaBot 5.0.1开始重制
- 移除比大小游戏玩法
- 修复b40/b50牌子、称号数据库问题
- 开始适配Python 3.10 及 Onebot v11协议（未适配完成的插件位于`src\Construct`文件夹内）
- 修复b40、b50找不到字体、图片的问题
- Arcaea及coc模块自机器人分离，使用nonebot插件商店内的项目并保持更新
  - Arcaea模块使用[nonebot-plugin-arcaeabot](https://github.com/SEAFHMC/nonebot-plugin-arcaeabot)
  - coc模块使用[nonebot_plugin_cocdicer](https://github.com/abrahum/nonebot_plugin_cocdicer)
- 修改插件加载方式，使StarBot可以同时加载`plugin-list.json`内列出的商店插件和本体自带模块
- 修复`database.py`中漂流社区的数据表存在错误字段的问题
- 更新依赖并修复若干依赖版本冲突
- 修复可能发生的`Max retries exceeded with url`错误
- 若干功能修复
