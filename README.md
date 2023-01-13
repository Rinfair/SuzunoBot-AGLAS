<div align="center">

![SuzunoBot-AGLAS](https://socialify.git.ci/Rinfair-CSP-A016/SuzunoBot-AGLAS/image?description=1&descriptionEditable=%E5%9F%BA%E4%BA%8E%20Kiba%20%26%20MaiBot%20%E9%A1%B9%E7%9B%AE%E5%BC%80%E5%8F%91%E7%9A%84%20NoneBot%20%E6%A1%86%E6%9E%B6%E7%9A%84%E5%A4%9A%E5%8A%9F%E8%83%BD%E9%9F%B3%E6%B8%B8%20Bot%EF%BC%8C%20%E7%89%88%E6%9C%AC%20v2.0.1%20Beta%200.95&font=KoHo&forks=1&issues=1&language=1&logo=https%3A%2F%2Fs2.loli.net%2F2023%2F01%2F06%2FmOJSs68BjPKqnoh.jpg&name=1&pattern=Circuit%20Board&pulls=1&stargazers=1&theme=Auto)

<p align="center">

[![Nonebot2](https://img.shields.io/badge/Onebot-Nonebot2-red?style=for-the-badge&logo=appveyor&color=blue)](https://github.com/nonebot/nonebot2)
[![cqhttp](https://img.shields.io/badge/OneBot-go--cqhttp-green.svg?style=for-the-badge&logo=appveyor&color=blue)](https://github.com/Mrs4s/go-cqhttp)
[![Release-version](https://img.shields.io/github/v/release/Rinfair-CSP-A016/SuzunoBot-AGLAS?include_prereleases&label=Version&display_name=tag&style=for-the-badge)](https://github.com/Rinfair-CSP-A016/SuzunoBot-AGLAS/releases)
[![Release date](https://img.shields.io/github/release-date-pre/Rinfair-CSP-A016/SuzunoBot-AGLAS?style=for-the-badge)](https://github.com/Rinfair-CSP-A016/SuzunoBot-AGLAS/releases)
[![license](https://img.shields.io/github/license/Rinfair-CSP-A016/SuzunoBot-AGLAS?style=for-the-badge)](https://github.com/Rinfair-CSP-A016/SuzunoBot-AGLAS/blob/master/LICENSE)

<div align="left">

## 欢迎使用

欢迎您使用 SuzunoBot 并搭建属于您自己的 SuzunoBot-AGLAS！

SuzunoBot-AGLAS 项目是基于 Mai-Bot 与 Kiba 项目融合改造创建的适用于为 Maimai DX/Maimai/雀魂/Arcaea 玩家服务的多功能 Bot。本代码的部分原始内容您可以参阅 [mai-bot](https://github.com/Diving-Fish/mai-bot)、[Kiba](https://github.com/KilluaSakata/Kiba)。

在此感谢 Diving-Fish 的 Mai-Bot / Chiyuki 开源项目以及 Killua 的 Kiba 开源项目。

接下来，本手册为您提供对SuzunoBot最基础的配置教程与支持。更多内容请阅读Wiki。

有关SuzunoBot-AGLAS的更新内容，请参阅[更新日志](https://github.com/Rinfair-CSP-A016/SuzunoBot-AGLAS/blob/master/CHANGELOG.md)。

## Step 1. 安装 Python

请自行前往 https://www.python.org/ 下载 Python 3 版本（> 3.7）并将其添加到环境变量（在安装过程中勾选 Add Python to system PATH）。对大多数用户来说，您应该下载 Windows installer (64-bit)。**此项目开发者使用Python 3.10.9**

在 Linux 系统上，可能需要其他方法安装 Python 3，请自行查找。

## Step 2. 初步设置

建议使用 git 对此项目进行版本管理。您也可以直接在本界面下载代码的压缩包进行运行。

在运行项目之前，您需要进入`src/static`文件夹，解压`static.zip`，到`src/static`中。在此之后，**您需要打开控制台（Terminal），并切换到该项目所在的目录。**

在 Windows 10 / Windows Server 2016 以上的系统上，您可以直接在项目的根目录（即 bot.py）文件所在的位置按下 Shift + 右键，点击【在此处打开 PowerShell 窗口】。
如果您使用的是更旧的操作系统（比如 Windows 7），请自行查找关于`命令提示符(Command Prompt)`，`Windows Powershell`以及`cd`命令的教程。

打开控制台后，您可以输入
```
python --version
```
控制台应该会打印出 Python 的版本。如果提示找不到 `python` 命令，请检查环境变量，**建议您安装 Python 时勾选 Add Python to system PATH**。

之后，输入以下命令自动安装依赖。
```
pip install -r requirements.txt
```
依赖项目安装完成后，您应设置目录的Config.py。

Config.py在`src/libraries`文件夹中。使用编辑工具打开后，在 bot_id 一栏中输入您拟运行 Kiba 项目的 QQ 号码，输入完成之后保存关闭。

**注意：除 Config.py 外，除非自主添加/删除功能，您不应编辑其他的 '*.py' 文件。否则可能导致 Bot 无法按预期运行。**

## Step 3. 运行项目

以上的操作均完成后，回到项目的主文件夹，打开命令提示符或 Powershell。输入此命令运行：
```
python bot.py
```
如果输出类似如下所示的内容，代表运行成功：
```
......
08-02 11:26:49 [INFO] uvicorn | Application startup complete.
08-02 11:26:49 [INFO] uvicorn | Uvicorn running on http://127.0.0.1:10219 (Press CTRL+C to quit)
```
如果输出了【ERROR】的红色输出，请您再次检查依赖项是否安装齐。

## Step 4. 连接 CQ-HTTP

前往 https://github.com/Mrs4s/go-cqhttp > Releases，下载适合自己操作系统的可执行文件。

go-cqhttp 在初次启动时会询问代理方式，选择反向 websocket 代理即可。

之后用任何文本编辑器打开`config.yml`文件，设置反向 ws 地址、上报方式：
```yml
message:
  post-format: array
  
servers:
  - ws-reverse:
      universal: ws://127.0.0.1:10219/onebot/v11/ws
```
然后设置您的 QQ 号和密码。您也可以不设置密码，选择扫码登陆的方式。

登陆成功后，后台应该会发送一条类似的信息：
```
08-02 11:50:51 [INFO] nonebot | WebSocket Connection from CQHTTP Bot 114514 Accepted!
```
至此，您可以和对应的 QQ 号聊天并使用 SuzunoBot-AGLAS 的所有功能了。

**注：自v2.0.1 Beta 0.93起，由于SuzunoBot-AGLAS使用nonebot-plugin-arcaeabot，您需要申请ArcaeaUnlimitedAPI的apiurl以及token才能使用arcaea模块的相关功能，具体请参考[nonebot-plugin-arcaeabot](https://github.com/SEAFHMC/nonebot-plugin-arcaeabot)的相关文档**

## FAQ

我不是 Windows 系统？
> 请您自行查阅其他系统上的 Python 安装方式。cqhttp提供了其他系统的可执行文件，您也可以自行配置 golang module 环境进行编译。

配置 nonebot 或 cq-http 过程中出错？
> 请查阅 https://github.com/nonebot/nonebot2 以及 https://github.com/Mrs4s/go-cqhttp 中的文档。

部分消息发不出来？
> 您的账号被风控了。解决方式：换号或者让这个号保持登陆状态和一定的聊天频率，持续一段时间。

歌曲查询显示的图片，左下角"Generated by AGLAS"是否可以更改？
> maimai查询方案由Killua设计，您可以自主使用PhotoShop等修图软件更改此样式。但请保留"Powered by Killua"字样。

我有其他问题？
> 若本仓库Wiki不能给你有关帮助，欢迎提出issue，我会尽快回应。

## 帮助与说明

SuzunoBot-AGLAS 主要提供了如下功能：

命令 | 功能
--- | ---
help | 查看帮助文档
今日舞萌 | 查看今天的舞萌运势
XXXmaimaiXXX什么 | 随机一首歌
随个[dx/标准][绿黄红紫白]<难度> | 随机一首指定条件的乐曲
随[数量]首[dx/标准][绿黄红紫白]<难度> | 随机指定数量的指定条件的乐曲<br>注意:数量不得超过4个。
查歌<乐曲标题的一部分> | 查询符合条件的乐曲
[绿黄红紫白]id<歌曲编号> | 查询乐曲信息或谱面信息
<歌曲别名>是什么歌 | 查询乐曲别名对应的乐曲
定数查歌 <定数> <br> 定数查歌 <定数下限> <定数上限> |  查询定数对应的乐曲
分数线 <难度+歌曲id> <分数线> | 展示歌曲的分数线
XrY | 在限定的上、下限随机数，要求X、Y均为正整数，且X必须小于Y。
今日性癖/jrxp | 你出勤时候的性癖是什么？
戳一戳 | 戳一戳bot试试吧。
本群戳一戳情况 | 看一下本群谁那么闲得慌
今日雀魂/雀魂运势 | 查看今天的雀魂运势
mjxp | 你打麻将的时候性癖是什么？
低情商<字段1>高情商<字段2> | 输出一张低情商与高情商的图
gocho <字段1> <字段2> | 输出一张gocho的图片
金龙盘旋 <字段1> <字段2> <字段3> | 输出一张金龙盘旋图
投骰子[数量] | 投指定数量的骰子
猜歌 | 开始一轮猜歌 (Preview)*<br>* 注意:目前猜歌是 Alpha Preview 阶段。<br> 已知问题:无法判断用户发布的答案的对错。
烟我 | 随机禁言1-600秒。<br>*注意:需要Bot有管理员权限。
b40 / b50 | 根据[查分器](https://www.diving-fish.com/maimaidx/prober/)数据，展示您的 Best 40 或模拟您的 Best 50。

更多的功能，您可以对Bot下达'help'命令。

## License

[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2FRinfair-CSP-A016%2FStarBot-AGLAS.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2FRinfair-CSP-A016%2FStarBot-AGLAS?ref=badge_large)

您可以自由使用本项目的代码用于商业或非商业的用途，但必须附带MIT License。
