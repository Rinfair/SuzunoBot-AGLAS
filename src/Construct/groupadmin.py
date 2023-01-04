import random
import re

from nonebot import on_command, on_message, on_notice, require, get_driver, on_regex
from nonebot.typing import T_State
from nonebot.adapters.cqhttp import Message, Event, Bot
from random import randint
from src.libraries.image import *

from collections import defaultdict

from nonebot.rule import to_me
from src.libraries.config import Config

driver = get_driver()

scheduler = require("nonebot_plugin_apscheduler").scheduler

help_admin = on_command('admin.help')

@help_admin.handle()
async def _(bot: Bot, event: Event, state: T_State):
    help_str = '''▼ 群管理功能 | Commands For Group Admin                                          
----------------------------------------------------------------------------------------------------------------------------------------
/AGLAS 烟我 | /AGLAS 抽奖       -->       对发送者随机禁言 60 - 600 秒

/AGLAS 睡觉 | /AGLAS sleep       -->       对发送者随机禁言 36000 - 96000 秒

/AGLAS 禁言轮盘 [1-6之间的数字] | /AGLAS round [1-6之间的数字]      -->       发送者输入一个数字，若与随机数相等，则禁言 60-960 秒。

[@我]禁言 [QQ号] | [@我]ban [QQ号]      -->       对输入的QQ号随机禁言 60 - 9600 秒，需要发送者是管理员才会执行。

[@我]强制睡眠 [QQ号] | [@我]forcesleep [QQ号]      -->       对输入的QQ号随机禁言 36000 - 96000 秒，需要发送者是管理员才会执行。

请注意：以上命令都需要 AGLAS（星酱） 是管理员身份才可以使用。
----------------------------------------------------------------------------------------------------------------------------------------'''
    await help_admin.send(Message([{
        "type": "image",
        "data": {
            "file": f"base64://{str(image_to_base64(text_to_image(help_str)), encoding='utf-8')}"
        }
    }]))


selfban = on_command("/AGLAS 烟我", aliases={'/AGLAS 抽奖', '/aglas 烟我', '/aglas 抽奖'})

@selfban.handle()
async def _(bot: Bot, event: Event, state: T_State):
    try:
        ids = event.get_session_id()
    except:
        pass
    else:
        if ids.startswith("group"):
            _, group_id, user_id = event.get_session_id().split("_")
            t = random.randint(60,600)
            typing = ['烤烟', '晒烟', '晾烟', '晒黄烟', '晒红烟', '香料烟', '华子', '二手烟']
            typing_type = random.randint(0,7)
            try:
                await bot.set_group_ban(group_id=group_id, user_id=user_id, duration=t)
                await selfban.send(f'▾ 自助禁言\n这是您的{t}秒（60-600秒随机）{typing[typing_type]}，大哥请！')
            except Exception as e:
                print(e)
                await selfban.finish(f"▿ 自助禁言 - 出现问题\n我不是管理员，或者你是管理员/群主，所以....我烟个锤子。\n[Exception Occurred]\n{e}")
        else:
            await selfban.finish("私聊我烟个锤子....或者您在用频道? 这个功能还没有支持频道呢。")

ban = on_command("ban", aliases={'禁言'}, rule=to_me(), priority=17)

@ban.handle()
async def _(bot: Bot, event: Event, state: T_State):
    argv = str(message).strip().split(" ")
    if argv[0] == "":
        await ban.finish("▿ 禁言 - 无账号\n没有账号我禁个锤子。")
    else:
        try:
            ids = event.get_session_id()
        except:
            pass
        else:
            if ids.startswith("group"):
                group_members = await bot.get_group_member_list(group_id=event.group_id)
                for m in group_members:
                    if m['user_id'] == event.user_id:
                        break
                if m['role'] != 'owner' and m['role'] != 'admin' and str(m['user_id']) not in Config.superuser:
                    await ban.finish("你不是管理烟个锤子哦。")
                    return
                _, group_id, user_id = event.get_session_id().split("_")
                t = random.randint(60,9600)
                try:
                    await bot.set_group_ban(group_id=group_id, user_id=argv[0], duration=t)
                    await ban.send(f'▾ 禁言\nta已经被烟了{t}秒（60-9600秒随机）。')
                except Exception as e:
                    print(e)
                    await ban.finish(f"▿ 禁言 - 出现问题\n我不是管理员，或者ta是管理员/群主，或者这个QQ号不在这个群，所以....我烟个锤子。\n[Exception Occurred]\n{e}")
            else:
                await ban.finish("▿ 禁言 - 出现问题\n私聊我烟个锤子....或者您在用频道? 这个功能还没有支持频道呢。")

sleepy = on_command("/AGLAS 睡觉", aliases={'/AGLAS sleep', '/aglas 睡觉', '/aglas sleep'})

@sleepy.handle()
async def _(bot: Bot, event: Event, state: T_State):
    try:
        ids = event.get_session_id()
    except:
        pass
    else:
        if ids.startswith("group"):
            _, group_id, user_id = event.get_session_id().split("_")
            t = random.randint(36000,96000)
            try:
                await bot.set_group_ban(group_id=group_id, user_id=user_id, duration=t)
                await sleepy.send(f'▾ 睡眠\n这是您的{t}秒（36000-96000秒随机）精致睡眠，晚安咯。')
            except Exception as e:
                print(e)
                await sleepy.finish(f"▿ 睡眠 - 出现问题\n我不是管理员，或者你是管理员/群主，所以....自己睡觉吧不要聊了。\n[Exception Occurred]\n{e}")
        else:
            await sleepy.finish("▿ 睡眠 - 出现问题\n私聊我是没有用滴....或者您在用频道? 这个功能还没有支持频道呢。")

forcesleep = on_command("forcesleep", aliases={'强制睡眠'}, rule=to_me(), priority=17)

@forcesleep.handle()
async def _(bot: Bot, event: Event, state: T_State):
    argv = str(message).strip().split(" ")
    if argv[0] == "":
        await forcesleep.finish("▿ 强制睡眠 - 无账号\n没有账号我禁个锤子。")
    else:
        try:
            ids = event.get_session_id()
        except:
            pass
        else:
            if ids.startswith("group"):
                group_members = await bot.get_group_member_list(group_id=event.group_id)
                for m in group_members:
                    if m['user_id'] == event.user_id:
                        break
                if m['role'] != 'owner' and m['role'] != 'admin' and str(m['user_id']) not in Config.superuser:
                    await forcesleep.finish("你不是管理还想让人强制入睡是吧？")
                    return
                _, group_id, user_id = event.get_session_id().split("_")
                t = random.randint(36000,96000)
                try:
                    await bot.set_group_ban(group_id=group_id, user_id=argv[0], duration=t)
                    await forcesleep.send(f'▾ 强制睡眠\nta已经强制按倒，并进行{t}秒（36000-96000秒随机）精致睡眠。')
                except Exception as e:
                    print(e)
                    await forcesleep.finish(f"▿ 强制睡眠 - 出现问题\n我不是管理员，或者ta是管理员/群主，或者这个QQ号不在这个群，所以....我没有办法。\n[Exception Occurred]\n{e}")
            else:
                await forcesleep.finish("▿ 强制睡眠 - 出现问题\n私聊我烟个锤子....或者您在用频道? 这个功能还没有支持频道呢。")

rounding = on_command("/AGLAS 禁言轮盘", aliases={'/AGLAS round', '/aglas 禁言轮盘', '/aglas round'})
@rounding.handle()
async def _(bot: Bot, event: Event, state: T_State):
    argv = str(message).strip().split(" ")
    if argv[0] == "":
        await rounding.finish("请在命令后面加一位 1-6 区间的数字。")
    else:
        try:
            ids = event.get_session_id()
        except:
            pass
        else:
            if ids.startswith("group"):
                _, group_id, user_id = event.get_session_id().split("_")
                t = random.randint(60,960)
                try:
                    num = random.randint(1,6)
                    if int(argv[0]) > 6 or int(argv[0]) < 1:
                        await bot.set_group_ban(group_id=group_id, user_id=user_id, duration=960)
                        await rounding.send(f'▿ 禁言轮盘\n不遵守游戏规则！惩罚性禁言 960 秒。')
                    elif int(argv[0]) == num:
                        await bot.set_group_ban(group_id=group_id, user_id=user_id, duration=t)
                        await rounding.send(f'▾ 禁言轮盘\n命中随机数！您被禁言 {t} 秒。')
                    else:
                        await rounding.send(f'▾ 禁言轮盘\n没有命中随机数！随机数是 {num}。')
                        return
                except Exception as e:
                    print(e)
                    await rounding.finish(f"▿ 禁言轮盘 - 出现问题\n我不是管理员，或者你是管理员/群主，所以....dame。\n[Exception Occurred]\n{e}")
            else:
                await rounding.finish("▿ 禁言轮盘 - 出现问题\n私聊我是没有用滴....或者您在用频道? 这个功能还没有支持频道呢。")