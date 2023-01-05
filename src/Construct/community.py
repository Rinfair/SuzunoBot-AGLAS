from ast import ExceptHandler
import random
import re

from PIL import Image
from nonebot import on_command, on_message, on_notice, require, get_driver, on_regex
from nonebot.typing import T_State
from nonebot.adapters.cqhttp import Message, Event, Bot
from src.libraries.image import *
from random import randint
import asyncio
from nonebot.adapters.cqhttp import Message, MessageSegment, GroupMessageEvent, PrivateMessageEvent
from nonebot_plugin_guild_patch import GuildMessageEvent

from nonebot.rule import to_me
from src.libraries.image import image_to_base64, path, draw_text, get_jlpx, text_to_image
from src.libraries.tool import hash

import os
import time
import datetime
from collections import defaultdict
from src.libraries.config import Config

plp_help = on_command('community.help')

@plp_help.handle()
async def _(bot: Bot, event: Event, state: T_State):
    help_str = '''▼ 漂流社区功能 | Commands For Ark-Star Community                                          
------------------------------------------------------------------------------------------------------------------------------
扔瓶子                                                                                   扔个瓶子给星酱。说不定会被别人读到哦。

捞瓶子                                                                                    捞一个瓶子，看看上面留言什么了？

回复瓶子 <漂流瓶 ID>                                                         给这个瓶子做评论吧！
 
看回复 <漂流瓶 ID>                                                             查看漂流瓶下面的回复！

删瓶子 <漂流瓶 ID>                                                             删除您发布的漂流瓶。
                                                                                             * 管理员使用此指令可删除其他人瓶子。

当前瓶子数量                                                                        查询社区当前漂流瓶子数量，此命令不受社区限制。

我的漂流瓶                                                                           我的漂流社区情况
------------------------------------------------------------------------------------------------------------------------------

▼ 管理员模块控制 | Administrative
------------------------------------------------------------------------------------------------------------------------------

设置漂流社区: 
漂流瓶设置 <完全启(禁)用/启(禁)用扔瓶子/启(禁)用捞瓶子/启(禁)用扔瓶子/启(禁)用回复/启（禁）用慢速(群聊可用)> 
<QQ号(可选)/慢速间隔时间(秒,可选)> <群号(可选)>

社区设置帮助请直接输入"漂流瓶设置"

删瓶子: 见上表可用命令中的说明，管理员允许删除任何人的漂流瓶。
------------------------------------------------------------------------------------------------------------------------------'''
    await plp_help.send(Message([{
        "type": "image",
        "data": {
            "file": f"base64://{str(image_to_base64(text_to_image(help_str)), encoding='utf-8')}"
        }
    }]))

plp_settings = on_command("漂流瓶设置")

@plp_settings.handle()
async def _(bot: Bot, event: Event, state: T_State):
    argv = str(message).strip().split(" ")
    nickname = event.sender.nickname
    db = get_driver().config.db
    now = datetime.datetime.now()
    nowtime = (now.year * 31104000) + (now.month * 2592000) + (now.day * 86400) + (now.hour * 3600) + (now.minute * 60) + now.second
    c = await db.cursor()
    mt = event.message_type
    if mt == "guild":
        await plp_settings.finish("▿ Ark-Star Community | 漂流社区设置\n暂不支持频道的漂流瓶设置。")
        return
    try:
        if len(argv) == 3:
            success = 400
            group_members = await bot.get_group_member_list(group_id=argv[2])
            for m in group_members:
                if m['user_id'] == event.user_id:
                    success = 0
                    break
            if success != 0:
                await plp_settings.finish("▿ Ark-Star Community | 漂流社区设置\n请检查您输入的群号，您不在此群或输错了号码。")
                return
            elif m['role'] != 'owner' and m['role'] != 'admin' and str(m['user_id']) not in Config.superuser:
                await plp_settings.finish("▿ Ark-Star Community | 漂流社区设置\n请检查您输入的群号，您不是此群管理员或您输错了号码。")
                return
        else:
            group_members = await bot.get_group_member_list(group_id=event.group_id)
            for m in group_members:
                if m['user_id'] == event.user_id:
                    break
            if m['role'] != 'owner' and m['role'] != 'admin' and str(m['user_id']) not in Config.superuser:
                await plp_settings.finish("▿ Ark-Star Community | 漂流社区设置\n这个...只有管理员可以设置Ark-Star Community | 漂流社区。")
                return
    except Exception as e:
        await plp_settings.finish(f"▿ Ark-Star Community | 漂流社区设置 - 现在是私聊？\n群的瓶子开关在私聊是无法设置的，或您输入了错误的群号(星酱不在这个群)。\n如果需要在私聊处理成员的拉黑，您需要在命令后面添加星酱所在群号以便查验您是否为管理员。\n请在如果不是私聊，看下下面的错误记录。\n[Exception Occurred]\n{e}")
        return
    try:
        if argv[0] == "完全启用":
            if len(argv) == 1:
                await c.execute(f'select * from group_plp_table where group_id={event.group_id}')
                data = await c.fetchone()
                if data is None:
                    await c.execute(f'insert into group_plp_table values ({event.group_id},0,0,0,0,0,{nowtime})')
                else:
                    await c.execute(f"update group_plp_table set disableinsert=0,disabletake=0,disablereply=0 where group_id={event.group_id}")
                await db.commit()
                await plp_insert.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 完成\n已成功设置为: {argv[0]}")
            else:
                await c.execute(f'select * from plp_blacklist_table where id={argv[1]}')
                data = await c.fetchone()
                if data is None:
                    await plp_insert.finish(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 限制人员功能\n您输入的 ID 没有在限制名单内。")
                else:
                    await c.execute(f"delete from plp_blacklist_table where id={argv[1]}")
                await db.commit()
                await plp_insert.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 限制人员功能\n对象 {argv[1]} 已成功设置为: {argv[0]}")
        elif argv[0] == "完全禁用":
            if len(argv) == 1:
                await c.execute(f'select * from group_plp_table where group_id={event.group_id}')
                data = await c.fetchone()
                if data is None:
                    await c.execute(f'insert into group_plp_table values ({event.group_id},1,1,1,0,0,{nowtime})')
                else:
                    await c.execute(f"update group_plp_table set disableinsert=1,disabletake=1,disablereply=1 where group_id={event.group_id}")
                await db.commit()
                await plp_insert.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 完成\n已成功设置为: {argv[0]}")
            else:
                await c.execute(f'select * from plp_blacklist_table where id={argv[1]}')
                data = await c.fetchone()
                if data is None:
                    await c.execute(f'insert into plp_blacklist_table values ({argv[1]},{event.user_id},1,1,1)')
                else:
                    await c.execute(f"update plp_blacklist_table set lastbanner={event.user_id},disableinsert=1,disabletake=1,disablereply=1 where id={argv[1]}")
                await db.commit()
                await plp_insert.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 限制人员功能\n对象 {argv[1]} 已成功设置为: {argv[0]}")
        elif argv[0] == "启用扔瓶子":
            if len(argv) == 1:
                await c.execute(f'select * from group_plp_table where group_id={event.group_id}')
                data = await c.fetchone()
                if data is None:
                    await c.execute(f'insert into group_plp_table values ({event.group_id},0,0,0,0,0,{nowtime})')
                else:
                    await c.execute(f"update group_plp_table set disableinsert=0 where group_id={event.group_id}")
                await db.commit()
                await plp_insert.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 完成\n已成功设置为: {argv[0]}")
            else:
                await c.execute(f'select * from plp_blacklist_table where id={argv[1]}')
                data = await c.fetchone()
                if data is None:
                    await plp_insert.finish(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 限制人员功能\n您输入的 ID 没有在限制名单内。")
                else:
                    await c.execute(f"update plp_blacklist_table set disableinsert=0 where id={argv[1]}")
                await db.commit()
                await plp_insert.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 限制人员功能\n对象 {argv[1]} 已成功设置为: {argv[0]}")
        elif argv[0] == "禁用扔瓶子":
            if len(argv) == 1:
                await c.execute(f'select * from group_plp_table where group_id={event.group_id}')
                data = await c.fetchone()
                if data is None:
                    await c.execute(f'insert into group_plp_table values ({event.group_id},1,0,0,0,0,{nowtime})')
                else:
                    await c.execute(f"update group_plp_table set disableinsert=1 where group_id={event.group_id}")
                await db.commit()
                await plp_insert.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 完成\n已成功设置为: {argv[0]}")
            else:
                await c.execute(f'select * from plp_blacklist_table where id={argv[1]}')
                data = await c.fetchone()
                if data is None:
                    await c.execute(f'insert into plp_blacklist_table values ({argv[1]},{event.user_id},1,0,0)')
                else:
                    await c.execute(f"update plp_blacklist_table set lastbanner={event.user_id},disableinsert=1 where id={argv[1]}")
                await db.commit()
                await plp_insert.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 限制人员功能\n对象 {argv[1]} 已成功设置为: {argv[0]}")
        elif argv[0] == "启用捞瓶子":
            if len(argv) == 1:
                await c.execute(f'select * from group_plp_table where group_id={event.group_id}')
                data = await c.fetchone()
                if data is None:
                    await c.execute(f'insert into group_plp_table values ({event.group_id},0,0,0,0,0,{nowtime})')
                else:
                    await c.execute(f"update group_plp_table set disabletake=0 where group_id={event.group_id}")
                await db.commit()
                await plp_insert.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 完成\n已成功设置为: {argv[0]}")
            else:
                await c.execute(f'select * from plp_blacklist_table where id={argv[1]}')
                data = await c.fetchone()
                if data is None:
                    await plp_insert.finish(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 限制人员功能\n您输入的 ID 没有在限制名单内。")
                else:
                    await c.execute(f"update plp_blacklist_table set disabletake=0 where id={argv[1]}")
                await db.commit()
                await plp_insert.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 限制人员功能\n对象 {argv[1]} 已成功设置为: {argv[0]}")
        elif argv[0] == "禁用捞瓶子":
            if len(argv) == 1:
                await c.execute(f'select * from group_plp_table where group_id={event.group_id}')
                data = await c.fetchone()
                if data is None:
                    await c.execute(f'insert into group_plp_table values ({event.group_id},0,1,0,0,0,{nowtime})')
                else:
                    await c.execute(f"update group_plp_table set disabletake=1 where group_id={event.group_id}")
                await db.commit()
                await plp_insert.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 完成\n已成功设置为: {argv[0]}")
            else:
                await c.execute(f'select * from plp_blacklist_table where id={argv[1]}')
                data = await c.fetchone()
                if data is None:
                    await c.execute(f'insert into plp_blacklist_table values ({argv[1]},{event.user_id},0,1,0)')
                else:
                    await c.execute(f"update plp_blacklist_table set lastbanner={event.user_id},disabletake=1 where id={argv[1]}")
                await db.commit()
                await plp_insert.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 限制人员功能\n对象 {argv[1]} 已成功设置为: {argv[0]}")
        elif argv[0] == "启用回复":
            if len(argv) == 1:
                await c.execute(f'select * from group_plp_table where group_id={event.group_id}')
                data = await c.fetchone()
                if data is None:
                    await c.execute(f'insert into group_plp_table values ({event.group_id},0,0,0,0,0,{nowtime})')
                else:
                    await c.execute(f"update group_plp_table set disablereply=0 where group_id={event.group_id}")
                await db.commit()
                await plp_insert.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 完成\n已成功设置为: {argv[0]}")
            else:
                await c.execute(f'select * from plp_blacklist_table where id={argv[1]}')
                data = await c.fetchone()
                if data is None:
                    await plp_insert.finish(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 限制人员功能\n您输入的 ID 没有在限制名单内。")
                else:
                    await c.execute(f"update plp_blacklist_table set disablereply=0 where id={argv[1]}")
                await db.commit()
                await plp_insert.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 限制人员功能\n对象 {argv[1]} 已成功设置为: {argv[0]}")
        elif argv[0] == "禁用回复":
            if len(argv) == 1:
                await c.execute(f'select * from group_plp_table where group_id={event.group_id}')
                data = await c.fetchone()
                if data is None:
                    await c.execute(f'insert into group_plp_table values ({event.group_id},0,0,1,0,0,{nowtime})')
                else:
                    await c.execute(f"update group_plp_table set disablereply=1 where group_id={event.group_id}")
                await db.commit()
                await plp_insert.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 完成\n已成功设置为: {argv[0]}")
            else:
                await c.execute(f'select * from plp_blacklist_table where id={argv[1]}')
                data = await c.fetchone()
                if data is None:
                    await c.execute(f'insert into plp_blacklist_table values ({argv[1]},{event.user_id},0,0,1)')
                else:
                    await c.execute(f"update plp_blacklist_table set lastbanner={event.user_id},disablereply=1 where id={argv[1]}")
                await db.commit()
                await plp_insert.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 限制人员功能\n对象 {argv[1]} 已成功设置为: {argv[0]}")
        elif argv[0] == "启用慢速":
            try:
                if len(argv) == 1:
                    time = 60
                else:
                    time = argv[1]
                await c.execute(f'select * from group_plp_table where group_id={event.group_id}')
                data = await c.fetchone()
                if data is None:
                    await c.execute(f'insert into group_plp_table values ({event.group_id},0,0,0,1,{argv[0]},{nowtime})')
                else:
                    await c.execute(f"update group_plp_table set slowmode=1 where group_id={event.group_id}")
                    await c.execute(f"update group_plp_table set limited={time} where group_id={event.group_id}")
                    await c.execute(f"update group_plp_table set time={nowtime} where group_id={event.group_id}")
                    await db.commit()
                    await plp_insert.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 完成\n已成功设置为: {argv[0]}\n命令冷却时间: {time} 秒。\n请注意: 扔瓶子、捞瓶子、回复瓶子共享一个冷却时间。")
            except Exception as e:
                pass
        elif argv[0] == "禁用慢速":
            try:
                await c.execute(f'select * from group_plp_table where group_id={event.group_id}')
                data = await c.fetchone()
                if data is None:
                    await c.execute(f'insert into group_plp_table values ({event.group_id},0,0,0,0,0,{nowtime})')
                else:
                    await c.execute(f"update group_plp_table set slowmode=0 where group_id={event.group_id}")
                    await c.execute(f"update group_plp_table set limited=0 where group_id={event.group_id}")
                    await c.execute(f"update group_plp_table set time={nowtime} where group_id={event.group_id}")
                await db.commit()
                await plp_insert.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 完成\n已成功设置为: {argv[0]}")
            except Exception as e:
                pass
        else:
            await plp_settings.send(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区设置 - 帮助\n格式为:漂流瓶设置 <完全启（禁）用/禁（启）用扔瓶子/禁（启）用捞瓶子/禁（启）用回复/启（禁）用慢速[仅群聊可用]> <(需要进行操作的)QQ号/间隔时长[单位:秒，选择慢速可用，不输入默认 60 秒]> <所在的群号(私聊情况下需要填写)>\n在不填写QQ号的情况下，默认是对您所在群的功能开关；填写QQ号后，转换为对此QQ号的功能开关。\n只能在处理QQ号时使用私聊。\n注意：慢速模式在私聊模式不生效且不回复，另外扔瓶子、捞瓶子、回复瓶子共享一个冷却时间。")
            return
    except Exception as e:
        pass
    

plp_insert = on_command("扔瓶子")

@plp_insert.handle()
async def _(bot: Bot, event: Event, state: T_State):
    argv = str(message).strip().split(" ")
    now = datetime.datetime.now() 
    nowtime = (now.year * 31104000) + (now.month * 2592000) + (now.day * 86400) + (now.hour * 3600) + (now.minute * 60) + now.second
    nickname = event.sender.nickname
    db = get_driver().config.db
    c = await db.cursor()
    mt = event.message_type
    user = event.user_id
    if mt == "guild":
        await c.execute(f'select * from gld_table where uid="{event.user_id}"')
        data = await c.fetchone()
        if data is None:
            await plp_reply.send(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区 - 错误\n在频道内，您需要绑定 QQ 号才可使用Ark-Star Community | 漂流社区。请进行绑定后再试一次。")
            return
        else:
            user = data[0]
    try:
        await c.execute(f'select * from group_plp_table where group_id={event.group_id}')
        data = await c.fetchone()
        if data is None:
            await c.execute(f'insert into group_plp_table values ({event.group_id},0,0,0,0,{nowtime})')
            await db.commit()
        else:
            if data[1] == 1:
                await plp_insert.send(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区 - 扔瓶子 - 错误\n管理员已禁用扔瓶子功能，请联系群管理员获得详情。")
                return
            elif data[4] == 1:
                limit = int(data[5]) + int(data[6])
                if nowtime < limit:
                    await plp_insert.send(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区 - 冷却中\n现在正在冷却时间，群管理设置的冷却时间: {data[5]} 秒。请稍后再试。")
                    return
                else:
                    await c.execute(f"update group_plp_table set time={nowtime} where group_id={event.group_id}")
                    await db.commit()
    except Exception as e:
        pass
    try:
        await c.execute(f'select * from plp_blacklist_table where id={user}')
        data = await c.fetchone()
        if data is None:
            pass
        else:
            if data[2] == 1:
                await plp_insert.send(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区 - 扔瓶子 - 错误\n您的扔瓶子功能已被限制使用。")
                return
    except Exception:
        pass
    plpid = now.year * random.randint(1,7200) + now.month * random.randint(1,4800) + now.day * random.randint(1,2400) + now.hour * random.randint(1,1200)+ now.minute * random.randint(1,600) + now.second * random.randint(1,300) + random.randint(1,9999999999)
    try:
        if len(argv) > 1:
            allmsg = ""
            for i in range(len(argv)):
                allmsg += f"{argv[i]}"
            argv[0] = allmsg
        elif len(argv) == 1 and argv[0] == "":
            await plp_insert.send(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 扔瓶子 - 帮助\n格式为:扔瓶子 瓶子内容.\n禁止发送黄赌毒、个人收款码等不允许发送的内容。否则将禁止个人使用此功能。")
            return
        elif argv[0].find("|") != -1:
            await plp_insert.send(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 扔瓶子 - 错误\n请不要在发送内容中加'|'，会干扰漂流瓶功能。")
            return
        if argv[0].find("CQ:image") != -1:
            message = argv[0].split("[")
            msg = message[0]
            piclink = message[1].split("url=")[1].split(";is_origin=0")
            await c.execute(f'insert into plp_table values ({plpid},{user},"{nickname}","{msg}|{piclink[0]}",1,0,0)')
            await db.commit()
            await plp_insert.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 扔瓶子 - 完成\n您的 图片 漂流瓶(ID: {plpid})已经扔出去啦!\n请注意: 如果您的瓶子包含了 R-18 (包括擦边球）以及任何不应在漂流瓶内出现的内容，您可能会受到 Ark-Star Community 的部分功能封禁或相应处置。如果需要撤回瓶子，请使用 “删瓶子” 指令。")
            return
        else:
            await c.execute(f'insert into plp_table values ({plpid},{user},"{nickname}","{argv[0]}",0,0,0)')
            await db.commit()
            await plp_insert.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 扔瓶子 - 完成\n您的 文字 漂流瓶(ID: {plpid})已经扔出去啦!\n请注意: 如果您的瓶子包含了不应在漂流瓶内出现的内容，您可能会受到 Ark-Star Community 的部分功能封禁或相应处置。如果需要撤回瓶子，请使用 “删瓶子” 指令。")
            return
    except Exception as e:
        pass

plp_find = on_command("捞瓶子")

@plp_find.handle()
async def _(bot: Bot, event: Event, state: T_State):
    argv = str(message).strip().split(" ")
    nickname = event.sender.nickname
    db = get_driver().config.db
    now = datetime.datetime.now()
    nowtime = (now.year * 31104000) + (now.month * 2592000) + (now.day * 86400) + (now.hour * 3600) + (now.minute * 60) + now.second
    c = await db.cursor()
    mt = event.message_type
    user = event.user_id
    if mt == "guild":
        await c.execute(f'select * from gld_table where uid="{event.user_id}"')
        data = await c.fetchone()
        if data is None:
            await plp_reply.send(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区 - 错误\n在频道内，您需要绑定 QQ 号才可使用Ark-Star Community | 漂流社区。请进行绑定后再试一次。")
            return
        else:
            user = data[0]
    try:
        await c.execute(f'select * from group_plp_table where group_id={event.group_id}')
        data = await c.fetchone()
        if data is None:
            await c.execute(f'insert into group_plp_table values ({event.group_id},0,0,0,0,{nowtime})')
            await db.commit()
        else:
            if data[2] == 1:
                await plp_find.send(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 捞瓶子 - 错误\n管理员已禁用捞瓶子功能，请联系群管理员获得详情。")
                return
            elif data[4] == 1:
                limit = int(data[5]) + int(data[6])
                if nowtime < lieditor.action.unicodeHighlight.disableHighlightingOfNonBasicAsciiCharactersmit:
                    await plp_insert.send(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区 - 冷却中\n现在正在冷却时间，群管理设置的冷却时间: {data[5]} 秒。请稍后再试。")
                    return
                else:
                    await c.execute(f"update group_plp_table set time={nowtime} where group_id={event.group_id}")
                    await db.commit()
    except Exception as e:
        pass
    try:
        await c.execute(f'select * from plp_blacklist_table where id={user}')
        data = await c.fetchone()
        if data is None:
            pass
        else:
            if data[3] == 1:
                await plp_insert.send(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区 - 扔瓶子 - 错误\n您的捞瓶子功能已被限制使用。")
                return
    except Exception:
        pass
    try:
        if len(argv) > 1:
            await plp_find.finish(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 捞瓶子 - 错误\n只能输入QQ号查找。您输入了好多条分段数据.....")
        elif argv[0] == "":
            await c.execute(f'select * from plp_table order by random() limit 1')
            data = await c.fetchone()
            if data is None:
                await plp_find.finish(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 捞瓶子 - 没有瓶子\n啊呀....星酱这目前一个瓶子都莫得。要不先扔一个看看？")
                return
            else:
                if data[4] == 0:
                    await plp_find.send(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 瓶子\nID: {data[0]} | {data[2]}({data[1]})\n👓 {data[5] + 1} | 💬 {data[6]}\n{data[3]}")
                    await c.execute(f"update plp_table set view={data[5] + 1} where id={data[0]}")
                    await db.commit()
                    return
                else:
                    message = data[3].split("|")
                    await plp_find.send(Message([
                        MessageSegment.text(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 瓶子\nID: {data[0]} | {data[2]}({data[1]})\n👓 {data[5] + 1} | 💬 {data[6]}\n{message[0]}"),
                        MessageSegment.image(f"{message[1]}")    
                    ]))
                    await c.execute(f"update plp_table set view={data[5] + 1} where id={data[0]}")
                    await db.commit()
                    return
        else:
            await c.execute(f'select * from plp_table where user_id={argv[0]}')
            data = await c.fetchall()
            if len(data) == 0:
                await c.execute(f'select * from plp_table where id={argv[0]}')
                data = await c.fetchone()
                if data is None:
                    await plp_find.finish(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 捞瓶子 - 错误\n您输入的 QQ 号码没有扔瓶子或您输入的漂流瓶 ID 不存在。")
                    return
                else:
                    if data[4] == 0:
                        msg1 = f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 瓶子 - 定向 ID 查找: {argv[0]}\n{data[2]}({data[1]})\n👓 {data[5] + 1} | 💬 {data[6]}\n{data[3]}"
                        await plp_find.send(msg1)
                        await c.execute(f"update plp_table set view={data[5] + 1} where id={data[0]}")
                        await db.commit()
                        return
                    else:
                        message = data[3].split("|")
                        await plp_find.send(Message([
                            MessageSegment.text(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 瓶子 - 定向 ID 查找: {argv[0]}\n{data[2]}({data[1]})\n👓 {data[5] + 1} | 💬 {data[6]}\n{message[0]}"),
                            MessageSegment.image(f"{message[1]}")
                        ]))
                        await c.execute(f"update plp_table set view={data[5] + 1} where id={data[0]}")
                        await db.commit()
                        return
            else:
                msg = f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 瓶子 - 定向 QQ 查找: {data[0][2]}({argv[0]})"
                if len(data) > 5:
                    msg += "\nta 扔的瓶子太多了，只显示最新四条消息。"
                    for i in range(len(data) - 4, len(data)):
                        if data[i][4] == 0:
                            msg += f"\n--------第 {i + 1} 条--------\nID: {data[i][0]}\n👓 {data[i][5] + 1} | 💬 {data[i][6]}\n{data[i][3]}"
                            await c.execute(f"update plp_table set view={data[i][5] + 1} where id={data[i][0]}")
                        else:
                            message = data[i][3].split("|")
                            msg += f"\n--------第 {i + 1} 条--------\nID: {data[i][0]}\n👓 {data[i][5] + 1} | 💬 {data[i][6]}\n{message[0]}\n[定向 QQ 查找不支持显示图片，您需要点击链接查看]\n{message[1]}"
                            await c.execute(f"update plp_table set view={data[i][5] + 1} where id={data[i][0]}")
                else:
                    for i in range(len(data)):
                        if data[i][4] == 0:
                            msg += f"\n--------第 {i + 1} 条--------\nID: {data[i][0]}\n👓 {data[i][5] + 1} | 💬 {data[i][6]}\n{data[i][3]}"
                            await c.execute(f"update plp_table set view={data[i][5] + 1} where id={data[i][0]}")
                        else:
                            message = data[i][3].split("|")
                            msg += f"\n--------第 {i + 1} 条--------\nID: {data[i][0]}\n👓 {data[i][5] + 1} | 💬 {data[i][6]}\n{message[0]}\n[定向 QQ 查找不支持显示图片，您需要点击链接查看]\n{message[1]}"
                            await c.execute(f"update plp_table set view={data[i][5] + 1} where id={data[i][0]}")
                await plp_find.send(msg)
                await db.commit()
    except Exception as e:
        pass

plp_clean = on_command("洗瓶子", rule=to_me())

@plp_clean.handle()
async def _(bot: Bot, event: Event, state: T_State):
    nickname = event.sender.nickname
    db = get_driver().config.db
    c = await db.cursor()
    if str(event.user_id) not in Config.superuser:
        await plp_clean.finish(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 洗瓶子 - 没有权限\n这个...只有星酱的管理员才可以清空瓶子。")
        return
    else:
        await c.execute(f'delete from plp_table')
        await c.execute(f'delete from plp_reply_table')
        await db.commit()
        await plp_clean.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 洗瓶子\n已清空漂流瓶数据。")
        return

plp_reply = on_command("回复瓶子")

@plp_reply.handle()
async def _(bot: Bot, event: Event, state: T_State):
    nickname = event.sender.nickname
    db = get_driver().config.db
    now = datetime.datetime.now()
    nowtime = (now.year * 31104000) + (now.month * 2592000) + (now.day * 86400) + (now.hour * 3600) + (now.minute * 60) + now.second
    c = await db.cursor()
    argv = str(message).strip().split(" ")
    mt = event.message_type
    user = event.user_id
    if mt == "guild":
        await c.execute(f'select * from gld_table where uid="{event.user_id}"')
        data = await c.fetchone()
        if data is None:
            await plp_reply.send(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区 - 错误\n在频道内，您需要绑定 QQ 号才可使用Ark-Star Community | 漂流社区。请进行绑定后再试一次。")
            return
        else:
            user = data[0]
    try:
        await c.execute(f'select * from group_plp_table where group_id={event.group_id}')
        data = await c.fetchone()
        if data is None:
            await c.execute(f'insert into group_plp_table values ({event.group_id},0,0,0,0,{nowtime})')
            await db.commit()
        else:
            if data[3] == 1:
                await plp_reply.send(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 回复瓶子 - 错误\n管理员已禁用瓶子评论回复功能，请联系群管理员获得详情。")
                return
            elif data[4] == 1:
                limit = int(data[5]) + int(data[6])
                if nowtime < limit:
                    await plp_insert.send(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区 - 冷却中\n现在正在冷却时间，群管理设置的冷却时间: {data[5]} 秒。请稍后再试。")
                    return
                else:
                    await c.execute(f"update group_plp_table set time={nowtime} where group_id={event.group_id}")
                    await db.commit()
    except Exception as e:
        pass
    try:
        await c.execute(f'select * from plp_blacklist_table where id={user}')
        data = await c.fetchone()
        if data is None:
            pass
        else:
            if data[4] == 1:
                await plp_insert.send(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区 - 扔瓶子 - 错误\n您的瓶子评论回复功能已被限制使用。")
                return
    except Exception:
        pass
    try:
        if len(argv) > 2 or len(argv) == 1 and argv[0] != "帮助":
            await plp_reply.finish(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 回复瓶子 - 错误\n参数输入有误。请参阅 “回复瓶子 帮助”")
        elif argv[0] == "帮助":
            await plp_reply.finish(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 回复瓶子 - 帮助\n命令格式是:\n回复瓶子 瓶子ID 回复内容\n注意回复无法带图片。")
        else:
            await c.execute(f'select * from plp_table where id={argv[0]}')
            data = await c.fetchone()
            if data is None:
                await plp_reply.finish(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 回复瓶子 - 错误\n没有这个瓶子捏。")
                return
            else:
                if argv[1].find("CQ:image") != -1:
                    await plp_reply.finish(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 回复瓶子 - 错误\n漂流瓶回复中不可以夹带图片！")
                    return
                else:
                    replyid = int(data[0] / random.randint(1,random.randint(199,9999)) * random.randint(random.randint(1,97), random.randint(101,199)))
                    await c.execute(f'insert into plp_reply_table values ({replyid},{argv[0]},{user},"{nickname}","{argv[1]}")')
                    await c.execute(f'update plp_table set reply={data[6] + 1} where id={argv[0]}')
                    await db.commit()
                    await plp_reply.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 回复瓶子\n已成功回复 ID 是 {argv[0]} 的漂流瓶。")
    except Exception as e:
        pass


plp_reply_view = on_command("看回复")

@plp_reply_view.handle()
async def _(bot: Bot, event: Event, state: T_State):
    nickname = event.sender.nickname
    db = get_driver().config.db
    now = datetime.datetime.now()
    nowtime = (now.year * 31104000) + (now.month * 2592000) + (now.day * 86400) + (now.hour * 3600) + (now.minute * 60) + now.second
    c = await db.cursor()
    argv = str(message).strip().split(" ")
    mt = event.message_type
    user = event.user_id
    if mt == "guild":
        await c.execute(f'select * from gld_table where uid="{event.user_id}"')
        data = await c.fetchone()
        if data is None:
            await plp_reply_view.send(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区 - 错误\n在频道内，您需要绑定 QQ 号才可使用Ark-Star Community | 漂流社区。请进行绑定后再试一次。")
            return
        else:
            user = data[0]
    try:
        await c.execute(f'select * from group_plp_table where group_id={event.group_id}')
        data = await c.fetchone()
        if data is None:
            await c.execute(f'insert into group_plp_table values ({event.group_id},0,0,0,0,{nowtime})')
            await db.commit()
        else:
            if data[3] == 1:
                await plp_reply.send(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 回复 - 错误\n管理员已禁用瓶子评论回复功能，请联系群管理员获得详情。")
                return
            elif data[4] == 1:
                limit = int(data[5]) + int(data[6])
                if nowtime < limit:
                    await plp_insert.send(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区 - 冷却中\n现在正在冷却时间，群管理设置的冷却时间: {data[5]} 秒。请稍后再试。")
                    return
                else:
                    await c.execute(f"update group_plp_table set time={nowtime} where group_id={event.group_id}")
                    await db.commit()
    except Exception as e:
        pass
    try:
        await c.execute(f'select * from plp_blacklist_table where id={user}')
        data = await c.fetchone()
        if data is None:
            pass
        else:
            if data[4] == 1:
                await plp_insert.send(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区 - 扔瓶子 - 错误\n您的瓶子评论回复功能已被限制使用。")
                return
    except Exception:
        pass
    try:
        if len(argv) > 1 or argv[0] == "":
            await plp_reply_view.finish(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 回复 - 错误\n请输入漂流瓶 ID 来查看瓶子回复。")
        else:
            await c.execute(f'select * from plp_reply_table where plpid={argv[0]}')
            data = await c.fetchall()
            if len(data) == 0:
                await plp_reply_view.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 回复 - {argv[0]}\n现在这个瓶子一个评论都没有!来坐沙发吧。")
            else:
                msg = f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区: 回复 - {argv[0]}"
                for i in range(len(data)):
                    msg += f'\n#{i + 1} | Reply ID: {data[i][0]}\n{data[i][3]}({data[i][2]}): {data[i][4]}'
                await plp_reply_view.finish(msg)
    except Exception as e:
        pass

plp_num = on_command("当前瓶子数量")

@plp_num.handle()
async def _(bot: Bot, event: Event, state: T_State):
    nickname = event.sender.nickname
    db = get_driver().config.db
    c = await db.cursor()
    await c.execute(f'select * from plp_table')
    data = await c.fetchall()
    await plp_num.finish(f"▾ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区\n现在全社区共有 {len(data)} 个漂流瓶。")

delete_plp = on_command("删瓶子")

@delete_plp.handle()
async def _(bot: Bot, event: Event, state: T_State):
    nickname = event.sender.nickname
    db = get_driver().config.db
    c = await db.cursor()
    argv = str(message).strip().split(" ")
    mt = event.message_type
    user = event.user_id
    if mt == "guild":
        await c.execute(f'select * from gld_table where uid="{event.user_id}"')
        data = await c.fetchone()
        if data is None:
            await delete_plp.send(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区 - 错误\n在频道内，您需要绑定 QQ 号才可使用Ark-Star Community | 漂流社区。请进行绑定后再试一次。")
            return
        else:
            user = data[0]
    try:
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
                    await c.execute(f'select * from plp_table where id={argv[0]}')
                    data = await c.fetchone()
                    if data is None:
                        await delete_plp.finish("▿ Ark-Star Community | 漂流社区\n找不到这个瓶子捏，看看您的 漂流瓶 ID 是否输入正确？")
                        return
                    else:
                        if event.user_id == data[1]:
                            await c.execute(f'delete from plp_table where id={argv[0]}')
                            await c.execute(f'delete from plp_reply_table where plpid={argv[0]}')
                            await db.commit()
                            await delete_plp.finish(f"▾ Ark-Star Community | 漂流社区 - 删除完成\n已删除 ID 是 {argv[0]} 的漂流瓶。")
                            return
                        else:
                            await delete_plp.finish("▿ Ark-Star Community | 漂流社区\n您没有相应的权限来删除此漂流瓶，您需要是管理员或您是瓶子发送者才有权限删除此瓶子。")
                            return
            else:
                await c.execute(f'select * from plp_table where id={argv[0]}')
                data = await c.fetchone()
                if data is None:
                    await delete_plp.finish("▿ Ark-Star Community | 漂流社区\n找不到这个瓶子捏，看看您的 漂流瓶 ID 是否输入正确？")
                    return
                else:
                    if user == data[1]:
                        await c.execute(f'delete from plp_table where id={argv[0]}')
                        await c.execute(f'delete from plp_reply_table where plpid={argv[0]}')
                        await db.commit()
                        await delete_plp.finish(f"▾ Ark-Star Community | 漂流社区 - 删除完成\n已删除 ID 是 {argv[0]} 的漂流瓶。")
                        return
                    else:
                        await delete_plp.finish("▿ Ark-Star Community | 漂流社区\n您没有相应的权限来删除此漂流瓶，您需要是瓶子发送者才有权限删除此瓶子。如您是群管理员，请在群聊内使用此指令。")
                        return
    except Exception as e:
        return
    await c.execute(f'select * from plp_table where id={argv[0]}')
    data = await c.fetchone()
    if data is None:
        await delete_plp.finish("▿ Ark-Star Community | 漂流社区\n找不到这个瓶子捏，看看您的 漂流瓶 ID 是否输入正确？")
        return
    else:
        await c.execute(f'delete from plp_table where id={argv[0]}')
        await c.execute(f'delete from plp_reply_table where plpid={argv[0]}')
        await db.commit()
        await delete_plp.finish(f"▾ Ark-Star Community | 漂流社区 - 删除完成\n已删除 ID 是 {argv[0]} 的漂流瓶。")

my_plp = on_command("我的漂流瓶")

@my_plp.handle()
async def _(bot: Bot, event: Event, state: T_State):
    nickname = event.sender.nickname
    mt = event.message_type
    db = get_driver().config.db
    is_admin = 1
    is_black = 1
    baninsert = 1
    banreply = 1
    bantake = 1
    msg = f"▾ [Sender: {nickname}]\n  我的Ark-Star Community | 漂流社区主页\n"
    c = await db.cursor()
    try:
        ids = event.get_session_id()
    except:
        pass
    else:
        user = event.user_id
        if mt == "guild":
            await c.execute(f'select * from gld_table where uid="{event.user_id}"')
            data = await c.fetchone()
            if data is None:
                await my_plp.send(f"▿ [Sender: {nickname}]\n  Ark-Star Community | 漂流社区 - 错误\n在频道内，您需要绑定 QQ 号才可使用Ark-Star Community | 漂流社区。请进行绑定后再试一次。")
                return
            else:
                user = data[0]
        if ids.startswith("group"):
            group_members = await bot.get_group_member_list(group_id=event.group_id)
            for m in group_members:
                if m['user_id'] == user:
                    break
            if m['role'] != 'owner' and m['role'] != 'admin':
                is_admin = 0
            if str(m['user_id']) in Config.superuser:
                is_admin = 2
        else:
            if str(user) in Config.superuser:
                is_admin = 2
            else:
                is_admin = -1
    await c.execute(f'select * from plp_blacklist_table where id={user}')
    data = await c.fetchone()
    if data is None:
        is_black = 0
        baninsert = 0
        banreply = 0
        bantake = 0
    else:
        if data[2] == 0:
            baninsert = 0
        if data[3] == 0:
            bantake = 0
        if data[4] == 0:
            banreply = 0
    if is_admin == -1:
        if is_black == 1:
            if baninsert == 0 and bantake == 0 and banreply == 0:
                msg += "👤 普通成员(非群聊无法确定是否为管理员)"
            elif baninsert == 1 and bantake == 1 and banreply == 1:
                msg += "👤 禁止使用"
            else:
                msg += "👤 限制功能"
        else:
            msg += "👤 普通成员(非群聊无法确定是否为管理员)"
    elif is_admin == 0:
        if is_black == 1:
            if baninsert == 0 and bantake == 0 and banreply == 0:
                msg += "👤 普通成员"
            elif baninsert == 1 and bantake == 1 and banreply == 1:
                msg += "👤 禁止使用"
            else:
                msg += "👤 限制功能"
        else:
            msg += "👤 普通成员"
    elif is_admin == 1:
        if is_black == 1:
            if baninsert == 0 and bantake == 0 and banreply == 0:
                msg += "👤 群管理员"
            else:
                msg += "👤 被限制功能的群管理员(可自行解除限制)"
        else:
            msg += "👤 群管理员"
    elif is_admin == 2:
        if is_black == 1:
            if baninsert == 0 and bantake == 0 and banreply == 0:
                msg += "👤 超级管理员"
            else:
                msg += "👤 被限制功能的超级管理员(可自行解除限制)"
        else:
            msg += "👤 超级管理员"
    await c.execute(f'select * from plp_table where user_id={user}')
    data2 = await c.fetchall()
    msg += f" | 🍾 {len(data2)}\n----------------------\n当前状态可使用以下社区功能:\n"
    if baninsert == 0:
        msg += "[√] 扔瓶子\n"
    else:
        msg += "[×] 扔瓶子\n"
    if bantake == 0:
        msg += "[√] 捞瓶子\n"
    else:
        msg += "[×] 捞瓶子\n"
    if banreply == 0:
        msg += "[√] 回复功能\n"
    else:
        msg += "[×] 回复功能\n"
    if len(data2) != 0:
        msg += "----------------------\n您扔过的漂流瓶的 ID 如下:"
        for i in range(len(data2)):
            if i == 0:
                msg += f"\n{data2[i][0]}"
            else:
                msg += f" {data2[i][0]}"
    await my_plp.finish(msg)
