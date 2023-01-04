from ast import ExceptHandler
import random
import re

from PIL import Image
from nonebot import on_command, on_message, on_notice, require, get_driver, on_regex
from nonebot.typing import T_State
from nonebot.params import CommandArg, EventMessage
from nonebot.adapters.onebot.v11 import Message, Event, Bot
from src.libraries.image import *
from random import randint
import asyncio
from nonebot.adapters.onebot.v11 import Message, MessageSegment, GroupMessageEvent, PrivateMessageEvent

from nonebot.rule import to_me
from src.libraries.image import image_to_base64, path, draw_text, get_jlpx, text_to_image
from src.libraries.tool import hash

import os
import time
import datetime
from collections import defaultdict
from src.libraries.config import Config

driver = get_driver()

scheduler = require("nonebot_plugin_apscheduler").scheduler

helper = on_command('help')

@helper.handle()
async def _(event: Event, message: Message = CommandArg()):
    about_str = f"▾ Getting Started | 上手帮助\n您可以查询以下模块的指令帮助，部分功能是否可用取决于您所在的群管理员的设置。\n关于星酱: about\nMaimai DX 模块: maimai.help\n跑团/COC 模块: .help\nArcaea 模块: arc help\n其它功能: public.help\n群管理模块(未启用): admin.help\n星酱漂流社区(未启用): community.help\nAGLAS系统设置: sys.help"
    await helper.send(Message([
        MessageSegment("text", {"text": about_str})
    ]))

about = on_command('about')

@about.handle()
async def _(event: Event, message: Message = CommandArg()):
    pic_dir = 'src/static/mai/pic/'
    codename = 'AGLAS for QQ-Group'
    version = '2.0.1'
    debugver = 'Beta 0.93'
    about_str =  f"版本代号: {codename}\n版本号: {version} ({debugver})\nPowered by Rinfair & Killua.\n\n感谢以下开发者对AGLAS的代码贡献:\n@Killua (Kiba)\n@Diving-Fish (Mai-Bot)\n@BlueDeer233 (maimaiDX)\n@Yuri-YuzuChaN (maimaiDX)\n@SEAFHMC (Arcaea)\n@mnixry (nonebot_guild_patch)\n@Sakurai Kaede"
    image = Image.open(os.path.join(pic_dir, 'StarAbout.png')).convert('RGBA')
    await helper.send(Message([
        MessageSegment("text", {"text": "▾ About AGLAS | 关于 星酱"}),
        MessageSegment("image", {"file": f"base64://{str(image_to_base64(image), encoding='utf-8')}"}),
        MessageSegment("text", {"text": about_str})
    ]))

help_others = on_command('public.help')

@help_others.handle()
async def _(event: Event, message: Message = CommandArg()):
    help_str = '''▼ 其它功能 | Commands For Public                                             
------------------------------------------------------------------------------------------------------------------------------
戳一戳                                                                                  来戳戳我？

本群戳一戳情况                                                                    查看一下群里有几位杰出的无聊人

今日雀魂                                                                               查看今天的雀魂运势

mjxp                                                                                     看看你今天要做什么牌捏？

低情商<str1>高情商<str2>                                                 生成一张低情商高情商图片，
                                                                                              把str1/2换成自己的话。

gocho <str1> <str2>                                                         生成一张gocho图。

金龙盘旋 <str1> <str2> <str3>                                         生成一张金龙盘旋图。

投骰子<数量>                                                                       在线投骰子(?)
投百面骰子<数量>                                                             * 可以选择六面/百面

                                                                                              这个功能可以随机禁言你1-600秒，前提星酱有权限。
烟我                                                                                    * 注意:为防止误触发，
                                                                                              这个功能你需要at一下星酱再说这个命令才能执行。

                                                                                               群里摇人。
随个[男/女]群友                                                                    你也可以不带参数直接说“随个”然后后面加啥都可以。
                                                                                               当然星酱容易骂你就是了。

帮选                                                                                      帮你选 

轮盘                                                                                      与帮选类似，不过增加了选项概率。


模拟抽卡/抽卡模拟                                                               抽卡模拟器

模拟十连/十连模拟                                                               抽卡模拟器 (十连模式)

我的抽卡情况/抽卡情况                                                        查看抽卡模拟器的抽卡情况

ping                                                                                  查看AGLAS运行情况 (Code By Sakurai Kaede)
------------------------------------------------------------------------------------------------------------------------------


▼ 频道设置 | Channel                                            
------------------------------------------------------------------------------------------------------------------------------
您可能需要绑定QQ号来免账号使用以上部分功能。绑定功能如下：

绑定 <QQ号>

解绑
------------------------------------------------------------------------------------------------------------------------------


▼ 管理员模块控制 | Administrative
------------------------------------------------------------------------------------------------------------------------------

设置戳一戳: 戳一戳设置 <启用/限制 (时间-秒)/禁用>
关于设置戳一戳的详细帮助，请您直接输入"戳一戳设置"

------------------------------------------------------------------------------------------------------------------------------'''
    await help_others.send(Message([
        MessageSegment("image", {"file": f"base64://{str(image_to_base64(text_to_image(help_str)), encoding='utf-8')}"})
    ]))


async def _group_poke(bot: Bot, event: Event) -> bool:
    value = (event.notice_type == "notify" and event.sub_type == "poke" and event.target_id == int(bot.self_id))
    return value


poke = on_notice(rule=_group_poke, priority=10, block=True)
poke_dict = defaultdict(lambda: defaultdict(int))

async def invoke_poke(group_id, user_id) -> str:
    db = get_driver().config.db
    ret = "default"
    ts = int(time.time())
    c = await db.cursor()
    await c.execute(f"select * from group_poke_table where group_id={group_id}")
    data = await c.fetchone()
    if data is None:
        await c.execute(f'insert into group_poke_table values ({group_id}, {ts}, 1, 0, "default")')
    else:
        t2 = ts
        if data[3] == 1:
            return "disabled"
        if data[4].startswith("limited"):
            duration = int(data[4][7:])
            if ts - duration < data[1]:
                ret = "limited"
                t2 = data[1]
        await c.execute(f'update group_poke_table set last_trigger_time={t2}, triggered={data[2] + 1} where group_id={group_id}')
    await c.execute(f"select * from user_poke_table where group_id={group_id} and user_id={user_id}")
    data2 = await c.fetchone()
    if data2 is None:
        await c.execute(f'insert into user_poke_table values ({user_id}, {group_id}, 1)')
    else:
        await c.execute(f'update user_poke_table set triggered={data2[2] + 1} where user_id={user_id} and group_id={group_id}')
    await db.commit()
    return ret

@poke.handle()
async def _(bot: Bot, event: Event, state: T_State):
    v = "default"
    if event.__getattribute__('group_id') is None:
        event.__delattr__('group_id')
    else:
        group_dict = poke_dict[event.__getattribute__('group_id')]
        group_dict[event.sender_id] += 1
        if v == "disabled":
            await poke.finish()
            return
    r = randint(1, 20)
    if v == "limited":
        await poke.send(Message([
            MessageSegment("poke", {"qq": f"{event.sender_id}"})
        ]))
    elif r == 2:
        await poke.send(Message('戳你🐎'))
    elif r == 3:
        url = await get_jlpx('戳', '你妈', '闲着没事干')
        await poke.send(Message([
            MessageSegment("image", {"file": url})
        ]))
    elif r == 4:
        img_p = Image.open(path)
        draw_text(img_p, '戳你妈', 0)
        draw_text(img_p, '有尝试过玩Cytus II吗', 400)
        await poke.send(Message([
            MessageSegment.image(f"base64://{str(image_to_base64(img_p), encoding='utf-8')}")
        ]))
    elif r == 5:
        await poke.send(Message('你有尝试玩过歌曲B.M.S.吗？'))
    elif r <= 7 and r > 5:
        await poke.send(Message([
            MessageSegment("image", {"file": f"https://www.diving-fish.com/images/poke/{r - 5}.gif"})
        ]))
    elif r <= 12 and r > 7:
        await poke.send(Message([
            MessageSegment("image", {"file": f"https://www.diving-fish.com/images/poke/{r - 7}.jpg"})
        ]))
    elif r <= 17 and r > 12:
        await poke.send(Message(f'哦我的上帝，看这里，我找到了一位超级无聊的人。'))
    elif r <= 19 and r > 17:
        t = random.randint(60,90)
        try:
            await bot.set_group_ban(group_id=event.__getattribute__('group_id'), user_id=event.sender_id, duration=t)
            await poke.send(f'别戳了！！烟你{t}秒冷静一下。')
        except Exception as e:
            print(e)
            await poke.send(Message('一天到晚就知道戳戳戳，戳自己肚皮不行吗？'))
    elif r == 1:
        await poke.send(Message('你不许再戳了！'))
    else:
        await poke.send(Message([
            MessageSegment("poke", {"qq": f"{event.sender_id}"})
        ]))

async def send_poke_stat(group_id: int, bot: Bot):
    if group_id not in poke_dict:
        return
    else:
        group_stat = poke_dict[group_id]
        sorted_dict = {k: v for k, v in sorted(group_stat.items(), key=lambda item: item[1], reverse=True)}
        index = 0
        data = []
        for k in sorted_dict:
            data.append((k, sorted_dict[k]))
            index += 1
            if index == 3:
                break
        await bot.send_msg(group_id=group_id, message="▾ 戳一戳总结\n欢迎来到“金中指奖”的颁奖现场！\n接下来公布一下上次重启以来，本群最JB闲着没事 -- 干玩戳一戳的获奖者。")
        await asyncio.sleep(1)
        if len(data) == 3:
            await bot.send_msg(group_id=group_id, message=Message([
                MessageSegment("text", {"text": "▾ 戳一戳总结 - 铜牌\n铜中指奖的获得者是"}),
                MessageSegment("at", {"qq": f"{data[2][0]}"}),
                MessageSegment("text", {"text": f"!!\n累计戳了 {data[2][1]} 次！\n让我们恭喜这位闲的没事干的家伙！"}),
            ]))
            await asyncio.sleep(1)
        if len(data) >= 2:
            await bot.send_msg(group_id=group_id, message=Message([
                MessageSegment("text", {"text": "▾ 戳一戳总结 - 银牌\n银中指奖的获得者是"}),
                MessageSegment("at", {"qq": f"{data[1][0]}"}),
                MessageSegment("text", {"text": f"!!\n累计戳了 {data[1][1]} 次！\n这太几把闲得慌了，请用中指戳戳自己肚皮解闷!"}),
            ]))
            await asyncio.sleep(1)
        await bot.send_msg(group_id=group_id, message=Message([
            MessageSegment("text", {"text": "▾ 戳一戳总结 - 金牌\n最几把离谱的!!金中指奖的获得者是"}),
            MessageSegment("at", {"qq": f"{data[0][0]}"}),
            MessageSegment("text", {"text": f"!!!\nTA一共戳了{data[0][1]}次，此时此刻我想询问获奖者一句话:就那么喜欢听我骂你吗?"}),
        ]))


poke_stat = on_command("本群戳一戳情况")


@poke_stat.handle()
async def _(bot: Bot, event: Event, message: Message = CommandArg()):
    try:
        group_id = event.group_id
        await send_poke_stat(group_id, bot)
    except Exception as e:
        await poke_setting.finish(f"▿ 戳一戳总结 - 现在是私聊或频道？\n私聊看群戳一戳情况...有点大病(确信)。\n如果是频道模式，则暂时不支持。\n如果都不是，看下下面的错误记录。\n[Exception Occurred]\n{e}")


poke_setting = on_command("戳一戳设置")


@poke_setting.handle()
async def _(bot: Bot, event: Event, message: Message = CommandArg()):
    db = get_driver().config.db
    try:
        group_members = await bot.get_group_member_list(group_id=event.group_id)
        for m in group_members:
            if m['user_id'] == event.user_id:
                break
        if m['role'] != 'owner' and m['role'] != 'admin' and str(m['user_id']) not in Config.superuser:
            await poke_setting.finish("这个...只有管理员可以设置戳一戳, 但是你不要去戳我....嗯..尽量别戳啦。")
            return
    except Exception as e:
        await poke_setting.finish(f"▿ 戳一戳设置 - 现在是私聊或频道？\n私聊设置个锤子戳一戳，你别戳不就完事了。\n如果是频道模式，则暂时不支持设置戳一戳。\n如果都不是，看下下面的错误记录。\n[Exception Occurred]\n{e}")
    argv = str(message).strip().split(' ')
    try:
        if argv[0] == "默认":
            c = await db.cursor()
            await c.execute(f'update group_poke_table set disabled=0, strategy="default" where group_id={event.group_id}')
        elif argv[0] == "限制":
            c = await db.cursor()
            await c.execute(
                f'update group_poke_table set disabled=0, strategy="limited{int(argv[1])}" where group_id={event.group_id}')
        elif argv[0] == "禁用":
            c = await db.cursor()
            await c.execute(
                f'update group_poke_table set disabled=1 where group_id={event.group_id}')
        else:
            raise ValueError
        await poke_setting.send(f"▾ 戳一戳设置 - 成功\n戳一戳已成功设置为: {argv[0]}")
        await db.commit()
    except (IndexError, ValueError):
        await poke_setting.finish("▾ 戳一戳设置 - 帮助\n本命令的格式:\n戳一戳设置 <默认/限制 (秒)/禁用>\n\n - 默认:将启用默认的戳一戳设定，包括随机性抽中禁言 1 - 1 分 30 秒。\n - 限制 (秒):在戳完一次星酱的指定时间内，调用戳一戳只会让星酱反过来戳你。在指定时间外时，与默认相同。\n- 禁用:禁用戳一戳的相关功能。")
        pass

shuffle = on_command('shuffle')


@shuffle.handle()
async def _(event: Event, message: Message = CommandArg()):
    argv = int(str(message))
    if argv > 100:
        await shuffle.finish('▿ 随机排列 - 数字过大\n随机排列太多了会刷屏，请输入100以内的数字。')
        return
    d = [str(i + 1) for i in range(argv)]
    random.shuffle(d)
    await shuffle.finish(','.join(d))

roll = on_regex(r"^([1-9]\d*)r([1-9]\d*)")

@roll.handle()
async def _(event: Event, message: Message = EventMessage()):
    regex = "([1-9]\d*)r([1-9]\d*)"
    groups = re.match(regex, str(message)).groups()
    try:
        num = random.randint(int(groups[0]),int(groups[1]))
        await roll.send(f"▾ 随机数\n您的随机数是{num}。")
    except Exception:
        await roll.send("▿ 随机数 - 错误\n语法有错哦，您是不是输入的浮点数还是落了一个？或者左面比右面的数字大？这都是不可以的。")

tz = on_regex(r"^投骰子([1-9]\d*)")

@tz.handle()
async def _(event: Event, message: Message = EventMessage()):
    regex = "投骰子([1-9]\d*)"
    groups = re.match(regex, str(message)).groups()
    try:
        if int(groups[0]) > 10:
            await roll.send("▿ 骰子 - 过多\n骰子数量不能大于10个。你是要刷屏嘛？")
        else:
            s = "▾ 骰子\n结果如下:"
            for i in range(int(groups[0])):
                num = random.randint(1,6)
                s += f'\n第 {i + 1} 个骰子 投掷结果是: {num}点'
            await roll.send(s)
    except Exception:
        await roll.send("▿ 骰子 - 错误\n语法上可能有错哦。再检查一下试试吧！")

tz_100 = on_regex(r"^投百面骰子([1-9]\d*)")

@tz_100.handle()
async def _(event: Event, message: Message = EventMessage()):
    regex = "投百面骰子([1-9]\d*)"
    groups = re.match(regex, str(message)).groups()
    try:
        if int(groups[0]) > 10:
            await roll.send("▿ 百面骰子 - 过多\n骰子数量不能大于10个。你是要刷屏嘛？")
        else:
            s = "▾ 百面骰子\n结果如下:"
            for i in range(int(groups[0])):
                num = random.randint(1,100)
                s += f'\n第 {i + 1} 个骰子 投掷结果是: {num}点'
            await roll.send(s)
    except Exception:
        await roll.send("▿ 百面骰子 - 错误\n语法上可能有错哦。再检查一下试试吧！")

random_person = on_regex("随个([男女]?)群友")

@random_person.handle()
async def _(bot:Bot, event: Event, message: Message = EventMessage()):
    try:
        mt = event.message_type
        if mt == "guild":
            await random_person.finish("▿ 随人 - 未支持\n随人功能暂时不支持频道。")
            return
        gid = event.group_id
        glst = await bot.get_group_member_list(group_id=gid, self_id=int(bot.self_id))
        v = re.match("随个([男女]?)群友", str(message)).group(1)
        if v == '男':
            for member in glst[:]:
                if member['sex'] != 'male':
                    glst.remove(member)
        elif v == '女':
            for member in glst[:]:
                if member['sex'] != 'female':
                    glst.remove(member)
        m = random.choice(glst)
        await random_person.finish(Message([
            MessageSegment("text", {"text": f"▾ To "}),
            MessageSegment("at", {"qq": event.user_id}),
            MessageSegment("text", {"text": f"\n随人\n{m['card'] if m['card'] != '' else m['nickname']}({m['user_id']})"}),
            ]))
    except AttributeError:
        await random_person.finish("你搁这随啥呢？爬去群里用。")

snmb = on_command("随个", priority=19)

@snmb.handle()
async def _(bot: Bot, event: Event, message: Message = CommandArg()):
    try:
        mt = event.message_type
        if mt == "guild":
            await snmb.finish(Message([
                MessageSegment("text", {"text": "随你"}),
                MessageSegment("image", {"file": "https://www.diving-fish.com/images/emoji/horse.png"})
            ]))
        gid = event.group_id
        if random.random() < 0.5:
            await snmb.finish(Message([
                MessageSegment("text", {"text": "随你"}),
                MessageSegment("image", {"file": "https://www.diving-fish.com/images/emoji/horse.png"})
            ]))
        else:
            glst = await bot.get_group_member_list(group_id=gid, self_id=int(bot.self_id))
            m = random.choice(glst)
            await random_person.finish(Message([
                MessageSegment("text", {"text": f"▾ To "}),
                MessageSegment("at", {"qq": event.user_id}),
                MessageSegment("text", {"text": f"\n随人\n{m['card'] if m['card'] != '' else m['nickname']}({m['user_id']})"}),
            ]))
    except AttributeError:
        await random_person.finish("你搁这随啥呢？爬去群里用。")


select = on_command("帮选", aliases={"帮我选"})
@select.handle()
async def _(event: Event, message: Message = CommandArg()):
    nickname = event.sender.nickname
    argv = str(message).strip().split(" ")
    xnmb = random.randint(0,20)
    if len(argv) == 1:
        await select.finish("▿ 帮选 - 参数不足\n选你🐎。")
        return
    elif len(argv) is not None:
        if xnmb == 1:
            await select.finish("▾ 帮选\n选你🐎，自己选去。")
            return
        elif xnmb >= 16 and xnmb <= 18:
            await select.finish("▾ 帮选\n我都不选。")
            return
        elif xnmb > 18:
            await select.finish("▾ 帮选\n小孩子才做选择，成年人我都要。")
            return
        else:
            result = random.randint(0, len(argv) - 1)
            await select.finish(f"▾ 帮选\n我选 {argv[result]}。")
            return
    else:
        await select.finish("▿ 帮选 - 无参数\n选你🐎。")
        return

rolling = on_command("轮盘")
@rolling.handle()
async def _(event: Event, message: Message = CommandArg()):
    nickname = event.sender.nickname
    argv = str(message).strip().split(" ")
    roll = 'A B C D E F G H I J K L M N O P Q R S T U V W X Y Z AA AB AC AD AE AF AG AH AI AJ AK AL AM AN AO AP AQ AR AS AT AU AV AW AX AY AZ'.split(' ')
    rollnum = 0
    sum = 0
    total = 0
    las = []
    rani = 0
    msg = f'▾ [Sender: {nickname}]\n  轮盘'
    if len(argv) % 2 != 0:
        await rolling.finish(f"▿ [Sender: {nickname}]\n  轮盘\n请注意格式：\n轮盘 <选项A> <A占比> <选项B> <B占比>......\n注意：所有选项占比的和必须等于 100。要求占比必须是整数，要不然...骂你嗷。")
        return
    try:
        for i in range(len(argv)):
            if i % 2 == 0:
                continue
            rollnum += 1
            sum += int(argv[i])
    except Exception as e:
        await rolling.finish(f"▿ [Sender: {nickname}]\n  轮盘\n....您输入的概率确定是整数还是**粗口**的其他语言？\n[Exception Occurred]\n{e}")
        return
    if sum != 100:
        await rolling.finish(f"▿ [Sender: {nickname}]\n  轮盘\n注意：所有选项占比的和必须等于 100。")
        return
    else:
        if rollnum > 52:
            await rolling.finish(f"▿ [Sender: {nickname}]\n  轮盘\n注意：您超出了52个选项，不支持过多选项。")
            return
        else:
            rollnum = 0
        for i in range(len(argv)):
            if i % 2 != 0:
                continue
            msg += f'\n{roll[rollnum]}: {argv[i]}, 占比: {argv[i + 1]}% ({total + 1} -'
            for j in range(int(argv[i + 1])):
                total += 1
            las.append(total)
            msg += f' {total})'
            rollnum += 1
        ran = random.randint(1,100)
        for i in range(len(argv)):
            if i % 2 != 0:
                continue
            if i == 0:
                if ran <= las[rani]:
                    ran_select = i
            else:
                if rani + 1 == len(las) and ran > int(las[rani - 1]):
                    ran_select = i
                else:
                    if ran > int(las[rani - 1]) and ran <= int(las[rani + 1]):
                        ran_select = i
            rani += 1
    msg += f'\n随机数是 {ran}，所以随机到的选项是: {argv[ran_select]}。'
    await rolling.finish(msg)


guild_bind = on_command("绑定")

@guild_bind.handle()
async def _(event: GuildMessageEvent, message: Message = CommandArg()):
    qq = str(event.get_message()).strip()
    nickname = event.sender.nickname
    uid = event.user_id
    db = get_driver().config.db
    c = await db.cursor()
    if qq == "":
        await guild_bind.finish(f"▿ [Sender: {nickname}]\n  绑定 - 错误\n您没有输入您的 QQ 号码。")
        return
    await c.execute(f'select * from gld_table where uid="{uid}"')
    data = await c.fetchone()
    if data is None:
        await c.execute(f'insert into gld_table values ({qq}, {uid})')
        await db.commit()
        await guild_bind.finish(f"▾ [Sender: {nickname}]\n  绑定\n您已成功绑定为您所输入的 QQ 号，现在您可以正常免输入用户名来使用 B40 / B50 / 底分分析 / 将牌查询 等内容，并可以在频道内使用漂流社区了。\n请注意！根据频道管理守则，您 **务必撤回** 您的绑定消息，以免造成不必要的损失。")
        return
    else:
        await c.execute(f'update gld_table set qq={qq} where uid={uid}')
        await db.commit()
        await guild_bind.finish(f"▾ [Sender: {nickname}]\n  绑定\n您已成功换绑为您所输入的 QQ 号。\n请注意！根据频道管理守则，您 **务必撤回** 您的绑定消息，以免造成不必要的损失。")

guild_unbind = on_command("解绑")

@guild_unbind.handle()
async def _(event: GuildMessageEvent, message: Message = CommandArg()):
    nickname = event.sender.nickname
    uid = event.user_id
    db = get_driver().config.db
    c = await db.cursor()
    await c.execute(f'select * from gld_table where uid="{uid}"')
    data = await c.fetchone()
    if data is None:
        await guild_bind.finish(f"▿ [Sender: {nickname}]\n  解绑\n您还没有绑定。")
        return
    else:
        await c.execute(f'delete from gld_table where uid="{uid}"')
        await db.commit()
        await guild_bind.finish(f"▾ [Sender: {nickname}]\n  解绑\n您已成功解绑。")

guild_view = on_command("查询绑定")
@guild_view.handle()
async def _(event: GuildMessageEvent, message: Message = CommandArg()):
    qq = str(event.get_message()).strip()
    nickname = event.sender.nickname
    uid = event.user_id
    db = get_driver().config.db
    c = await db.cursor()
    await c.execute(f'select * from gld_table where uid="{uid}"')
    data = await c.fetchone()
    if data is None:
        await guild_bind.finish(f"▿ [Sender: {nickname}]\n  绑定查询\n您还没有绑定。")
        return
    else:
        await guild_bind.finish(f"▾ [Sender: {nickname}]\n  绑定查询\nQQ ID:{data[0]}\n频道 ID:{data[1]}")

acard = on_command("抽卡模拟", aliases={"模拟抽卡"})
@acard.handle()
async def _(event: Event, message: Message = CommandArg()):
    nickname = event.sender.nickname
    mt = event.message_type
    user = event.user_id
    db = get_driver().config.db
    c = await db.cursor()
    if mt == "guild":
        await c.execute(f'select * from gld_table where uid="{event.user_id}"')
        data = await c.fetchone()
        if data is None:
            await acard.send(f"▿ [Sender: {nickname}]\n  抽卡模拟器 - 错误\n在频道内，您需要绑定 QQ 号才可使用抽卡模拟器。请进行绑定后再试一次。")
            return
        else:
            user = data[0]
    await c.execute(f'select * from acard_table where id="{user}"')
    data1 = await c.fetchone()
    if data1 is None:
        await c.execute(f'insert into acard_table values ({user},1,0,0,0,0,0,0)')
    s = f'▾ [Sender: {nickname}]\n  抽卡模拟器\n'
    cardnum = random.randint(1,100)
    if cardnum <= 2:
        if data1 is None:
            await c.execute(f'update acard_table set six=1 where id={user}')
        else:
            await c.execute(f'update acard_table set six={data1[2] + 1}, times={data1[1] + 1} where id={user}')
        s += "欧皇诞生！恭喜您抽中★6卡！\n"
    elif cardnum > 2 and cardnum <= 10:
        if data1 is None:
            await c.execute(f'update acard_table set five=1 where id={user}')
        else:
            await c.execute(f'update acard_table set five={data1[3] + 1}, times={data1[1] + 1} where id={user}')
        s += "金色闪耀！恭喜您抽中★5卡！\n"
    elif cardnum > 10 and cardnum <= 50:
        if data1 is None:
            await c.execute(f'update acard_table set four=1 where id={user}')
        else:
            await c.execute(f'update acard_table set four={data1[4] + 1}, times={data1[1] + 1} where id={user}')
        s += "您抽中了★4卡。\n"
    elif cardnum > 50 and cardnum <= 70:
        if data1 is None:
            await c.execute(f'update acard_table set three=1 where id={user}')
        else:
            await c.execute(f'update acard_table set three={data1[5] + 1}, times={data1[1] + 1} where id={user}')
        s += "您抽中了★3卡。\n"
    elif cardnum > 70 and cardnum <= 90:
        if data1 is None:
            await c.execute(f'update acard_table set two=1 where id={user}')
        else:
            await c.execute(f'update acard_table set two={data1[6] + 1}, times={data1[1] + 1} where id={user}')
        s += "有点非......您抽中了★2卡。\n"
    else:
        if data1 is None:
            await c.execute(f'update acard_table set one=1 where id={user}')
        else:
            await c.execute(f'update acard_table set one={data1[7] + 1}, times={data1[1] + 1} where id={user}')
        s += "天哪......您抽中了★1卡......\n"
    s += "抽卡说明 >\n1.爆率:\n★6: 2% ★5: 8% ★4: 40%\n★3: 20% ★2: 20% ★1: 10%\n"
    s += "2.卡的星数等级越高越稀有。\n3.此模拟器不设累计次数增加高星爆率的行为。"
    await db.commit()
    await acard.send(s)


acard10x = on_command("十连模拟", aliases={"模拟十连"})
@acard10x.handle()
async def _(event: Event, message: Message = CommandArg()):
    nickname = event.sender.nickname
    mt = event.message_type
    user = event.user_id
    db = get_driver().config.db
    c = await db.cursor()
    if mt == "guild":
        await c.execute(f'select * from gld_table where uid="{event.user_id}"')
        data = await c.fetchone()
        if data is None:
            await acard.send(f"▿ [Sender: {nickname}]\n  抽卡模拟器 - 错误\n在频道内，您需要绑定 QQ 号才可使用抽卡模拟器。请进行绑定后再试一次。")
            return
        else:
            user = data[0]
    await c.execute(f'select * from acard_table where id="{user}"')
    data1 = await c.fetchone()
    if data1 is None:
        await c.execute(f'insert into acard_table values ({user},0,0,0,0,0,0,0)')
        times = 0
        six = 0
        five = 0
        four = 0
        three = 0
        two = 0
        one = 0
    else:
        times = data1[1]
        six = data1[2]
        five = data1[3]
        four = data1[4]
        three = data1[5]
        two = data1[6]
        one = data1[7]
    s = f'▾ [Sender: {nickname}]\n  抽卡模拟器 - 十连模式\n'
    for i in range(0,10):
        s += f'第 {i + 1} 次: '
        times += 1
        cardnum = random.randint(1,100)
        if cardnum <= 2:
            six += 1
            await c.execute(f'update acard_table set six={six}, times={times} where id={user}')
            s += "欧皇诞生！恭喜您抽中★6卡！\n"
        elif cardnum > 2 and cardnum <= 10:
            five += 1
            await c.execute(f'update acard_table set five={five}, times={times} where id={user}')
            s += "金色闪耀！恭喜您抽中★5卡！\n"
        elif cardnum > 10 and cardnum <= 50:
            four += 1
            await c.execute(f'update acard_table set four={four}, times={times} where id={user}')
            s += "您抽中了★4卡。\n"
        elif cardnum > 50 and cardnum <= 70:
            three += 1
            await c.execute(f'update acard_table set three={three}, times={times} where id={user}')
            s += "您抽中了★3卡。\n"
        elif cardnum > 70 and cardnum <= 90:
            two += 1
            await c.execute(f'update acard_table set two={two}, times={times} where id={user}')
            s += "有点非......您抽中了★2卡。\n"
        else:
            one += 1
            await c.execute(f'update acard_table set one={one}, times={times} where id={user}')
            s += "天哪......您抽中了★1卡......\n"
    s += "抽卡说明 >\n1.爆率:\n★6: 2% ★5: 8% ★4: 40%\n★3: 20% ★2: 20% ★1: 10%\n"
    s += "2.卡的星数等级越高越稀有。\n3.此模拟器不设累计次数增加高星爆率的行为。"
    await db.commit()
    await acard10x.send(s)

acardcenter = on_command("我的抽卡情况", aliases={"抽卡情况"})
@acardcenter.handle()
async def _(event: Event, message: Message = CommandArg()):
    nickname = event.sender.nickname
    mt = event.message_type
    user = event.user_id
    db = get_driver().config.db
    c = await db.cursor()
    if mt == "guild":
        await c.execute(f'select * from gld_table where uid="{event.user_id}"')
        data = await c.fetchone()
        if data is None:
            await acardcenter.send(f"▿ [Sender: {nickname}]\n  抽卡中心 - 错误\n在频道内，您需要绑定 QQ 号才可查看模拟抽卡器的抽卡情况。请进行绑定后再试一次。")
            return
        else:
            user = data[0]
    await c.execute(f'select * from acard_table where id="{user}"')
    data1 = await c.fetchone()
    if data1 is None:
        await acardcenter.send(f"▿ [Sender: {nickname}]\n  抽卡中心\n您还没有使用过模拟抽卡/模拟十连命令，快来试试吧！")
        return
    s = f'▾ [Sender: {nickname}]\n  抽卡中心\n'
    s += f'抽卡次数：{data1[1]} 次。\n'
    s += f'★6: {data1[2]} 张  ★5: {data1[3]} 张\n★4: {data1[4]} 张  ★3: {data1[5]} 张\n★2: {data1[6]} 张  ★1: {data1[7]} 张'
    await acardcenter.send(s)



