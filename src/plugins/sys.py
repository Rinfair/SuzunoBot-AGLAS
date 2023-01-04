from ast import If
from http.client import FAILED_DEPENDENCY
from io import SEEK_END
from pdb import Restart
from nonebot import on_command
from nonebot.permission import SUPERUSER
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import Message, Event, Bot, MessageSegment
import platform
import time
from nonebot.rule import to_me
from src.libraries.config import Config
from src.ControlTools.tools import restart
from nonebot.typing import T_State
from src.libraries.image import image_to_base64, text_to_image

using_distro = False
try:
    import distro
    using_distro = True
except ImportError:
    pass

sys_help = on_command('sys.help')
@sys_help.handle()
async def _(bot: Bot, event: Event, message: Message = CommandArg()):
    help_str = '''▼ 系统设置帮助 | Commands For AGLAS System
------------------------------------------------------------------------------------------------------------------------------
以下设置，除显示系统状态外，都需要操作者的身份是群管理或者是星酱管理员时这些操作才会执行。
部分高权限、高风险操作只有发送者的身份是星酱管理员才可以执行，这些命令将在这里以[*]标注。

警告: 操作以[!]标注的这些设置会直接影响星酱的稳定性，严禁随意使用。发生严重后果的， AGLAS 会将操
作者所在群退出并拉黑操作者。 若操作者为星酱管理员，取消其管理权限。

这些操作，除系统状态外，都需要 @星酱 才会执行。

[ ][ ] 系统状态 / ping              --  显示星酱当前的系统状态。

[!][*] restart / 重启              --  在不重启计算机的情况下，重启星酱服务。
注: 切勿很短时间内重启多次，会影响服务。

[!][*] 群发 / send              --  向星酱所在的所有群发送消息，您不得使用此命令发送有害信息。
------------------------------------------------------------------------------------------------------------------------------'''
    await sys_help.send(Message([
        MessageSegment("image", {"file": f"base64://{str(image_to_base64(text_to_image(help_str)), encoding='utf-8')}"})
    ]))


start = time.time()
start = int(start)

systeminfo = on_command("systeminfo", aliases={"系统状态", "ping", "Ping"} ,priority=5)
@systeminfo.handle()
async def _(bot: Bot, event: Event):
    python_version = platform.python_version()
    arch = platform.architecture()
    node = platform.node()
    platform_version = platform.platform()
    processor = platform.processor()
    build_time = platform.python_build()
    system = platform.system()
    release = platform.release()
    m, s = divmod((int(time.time()) - start), 60)
    h, m = divmod(m, 60)
    result = "▾ Pong! | 系统状态\n"
    flag = False
    if using_distro == True:
        flag = True
        if distro.name() == "" and distro.version() == "":
            flag = False
    if flag == False:
        result += "系统类型: " + system + "\n系统版本号: " + release + "\n系统架构: " + arch[0] + "\n处理器信息: " + processor + "\n设备名: " + node + "\n系统版本: " + platform_version + "\nPython 版本: " + python_version + "\nPython 构建时间: " + build_time[1] + "\nAGLAS 运行时间: " + str(h) + "h " + str(m) + "min " + str(s) + "s"
        await systeminfo.send(result)
    elif flag == True:
        distro_name = distro.name()
        distro_version = distro.version()
        result += "系统类型: " + system + "\n系统版本号: " + release + "\n系统架构: " + arch[0] + "\n处理器信息: " + processor + "\n设备名: " + node + "\nLinux 发行版: " + distro_name + "\nLinux 发行版版本: " + distro_version + "\nPython 版本: " + python_version + "\nPython 构建时间: " + build_time[1] + "\nAGLAS 运行时间: " + str(h) + "h " + str(m) + "min " + str(s) + "s"
        await systeminfo.send(result)


restartbot = on_command("restart", aliases={"重启", "重新启动", "reset"} ,rule=to_me() ,priority=5)
@restartbot.handle()
async def _(bot: Bot, event: Event):
    if str(event.user_id) not in Config.superuser:
        await restartbot.send("您还不是星酱的管理员，无法重新启动星酱。请联系管理员。")
        return
    else:
        flag = False
        if using_distro == True:
            flag = True
            if distro.name() == "" and distro.version() == "":
                flag = False
        if flag == False:
            await restartbot.send("正在重新启动 AGLAS Server......\n请稍候，重启操作需要1-3分钟。")
            restart()
        else:
            await restartbot.send("重启命令当前只支持 Windows 版本。请您手动登录服务器以重新启动。")


sendmsg = on_command("sendmsg", aliases={"send", "群发"} ,rule=to_me() ,priority=5)
@sendmsg.handle()
async def _(bot: Bot, event: Event, message: Message = CommandArg()):
    if str(event.user_id) not in Config.superuser:
        await sendmsg.send("您还不是星酱的管理员，无法给所有参与的群发送通知。请联系管理员。")
        return
    else:
        msg = str(message).strip()
        await sendmsg.send("正在群发此通知消息，请稍候......\n为了防止风控，每 10 秒发送一个群。")
        send = '▾星酱管理员的群发消息:\n' + msg
        group_list = await bot.get_group_list()
        complete = 0
        failed = 0
        for group in group_list:
            time.sleep(10)
            try:
                await sendmsg.send(group_id=group['group_id'],message=send)
                complete += 1
            except:
                failed += 1
                continue
        await sendmsg.send(f"群发完成。共发送成功 {complete} 个群，发送失败 {failed} 个群。")