from collections import defaultdict

from nonebot import on_command, on_regex
from nonebot.typing import T_State
from nonebot.adapters import Event, Bot
from nonebot.adapters.cqhttp import Message, MessageSegment, GroupMessageEvent, PrivateMessageEvent

from src.libraries.tool import hash
from src.libraries.maimaidx_music import *
from src.libraries.image import *
from src.libraries.maimai_best_40 import generate
import re

import datetime


maj_list = ['立直', '断幺九', '门前清自摸', '自风', '场风', '一杯口', '抢杠', '岭上开花', '海底捞月/河底捞鱼', '一发', '三色同顺/同刻', '三杠子', '对对和', '三暗刻', '小三元', '混老头', '七对子', '混全带幺九', '一气通贯', '纯全带幺九', '混一色', '二杯口', '清一色', '大三元', '四暗刻', '字一色', '绿一色', '清老头', '国士无双(十三幺)', '小四喜', '四杠子', '九莲宝灯', '纯正九莲宝灯', '大四喜', '四暗刻单骑', '国士无双十三面']
maj_list_perfect = ['赢古役:竟然做成了...分数？拿来吧你！', '线下麻:行，看我线下表演岭上开花。', '耍帅:一到九，九莲宝灯！潇洒摊牌等给分吧。', '天和:你们继续，我先吃点好的。', '大竹林:我就是一有点大的七对子啦。', '七对子:轻轻松松立直都能和啊。', '立直:你们随便打，我就和9种牌。', '流局满贯:我就不和国士无双。欸，就是玩儿。来满贯了，快给我分。', '九种九牌不流局:听牌了，国士十三面，你们随便打。']
maj_list_bad = ['做古役:....我忘了打开古役开关了。', '线下麻:遇到了鸽子 × 3。', '耍帅:一到九，无役！又不是混清老头，还不是带幺九....', '天和:我一张牌还都没出呢...你咋和牌了？', '大竹林:哦...不就是七对子嘛...役满???', '七对子:立直啦，流局也没和上牌那种。', '立直:不是吧，立直放铳放了个役满......', '流局满贯:红中....碰!!', '九种九牌不流局:啊这...赔了三家立直棒钱吗......"']
majtips_list = ['发牌姬不会一直发好牌的......运气很重要。', '胜不骄，败不馁。', '排位场就不要想着做大牌了...越早跑路越好！', '你永远不知道你的对手在做什么好牌。', '底力不够？建议下埋！不要强行越级，手癖难解。', '时常看弃牌，万一避免了被点个国士无双呢？', '必要时可以弃和保命。', 'All Last不是结束，他还只是开始。', '什么大牌都怕断幺九。']


mjr = on_regex(r".*日麻.*什么")


@mjr.handle()
async def _(bot: Bot, event: Event, state: T_State):
    await mjr.finish(Message[
        {"type": "text", "data": {"text": f"可以是 {maj_list[random.randint(0,35)]}。"}}
    ])



mjxp = on_command('mjxp', aliases={'麻将性癖'})


@mjxp.handle()
async def _(bot: Bot, event: Event, state: T_State):
    nickname = event.sender.nickname
    xp = random.randint(0,35)
    s = f"▾ [Sender: {nickname}]\n  麻将癖好\n你今天打麻将的癖好是做{maj_list[xp]}! 不满意的话再随一个吧。"
    await mjxp.finish(Message([
        {"type": "text", "data": {"text": s}}
    ]))


jrmj = on_command('雀魂运势', aliases={'今日雀魂'})

@jrmj.handle()
async def _(bot: Bot, event: Event, state: T_State):   
    qq = int(event.get_user_id())
    nickname = event.sender.nickname
    h = hash(qq)
    rp = h % 100
    luck = hash(int((h * 6) / 2)) % 100
    ap = hash(int(((luck) / (rp * 2)) * (h / 3))) % 100
    maj_value = []
    good_value = {}
    bad_value = {}
    good_count = 0
    bad_count = 0
    dwm_value_1 = random.randint(0,8)
    dwm_value_2 = random.randint(0,8)
    tips_value = random.randint(0,8)
    now = datetime.datetime.now()  
    for i in range(36):
        maj_value.append(h & 3)
        h >>= 2
    s = f"▾ [Sender: {nickname}]\n  雀魂运势板\n⏲️ | {now.year}/{now.month}/{now.day} {now.hour}:{now.strftime('%M')}:{now.strftime('%S')}\n"
    s += f"\n★ 一姬之签 | Drawing\n---------------------\n"
    s += f"人品值: {rp}%\n"
    s += f"大和率: {luck}%"
    if rp >= 50 and rp < 70:
        s += "            小吉\n"
    elif rp >= 70 and rp < 90:
        s += "             吉\n"
    elif rp >= 90:
        s += "            大吉\n"
    elif rp >= 30 and rp < 50:
        s += "            小凶\n"
    elif rp >= 10 and rp < 30:
        s += "             凶\n"
    else:
        s += "            大凶\n"
    s += f"役满率: {ap}%\n---------------------\n\n★ 打牌运势 | Fortune\n"

    if dwm_value_1 == dwm_value_2:
        s += f'平 | 今天总体上平平无常。那就正常打麻将吧？\n'
    else:
        s += f'宜 | {maj_list_perfect[dwm_value_1]}\n'
        s += f'忌 | {maj_list_bad[dwm_value_2]}\n'
    s += "\n★ 牌型推荐 | Keywords\n"
    for i in range(36):
        if maj_value[i] == 3:
            good_value[good_count] = i
            good_count = good_count + 1
        elif maj_value[i] > 0 and maj_value[i] < 3:
            bad_value[bad_count] = i
            bad_count = bad_count + 1
    if good_count == 0:
        s += "推荐 | 🚫 没有最适合的牌型"
    else:
        s += f'推荐 | 共 {good_count} 项 >\n'
        for i in range(good_count):
            s += f'{maj_list[good_value[i]]} '
    if bad_count == 0:
        s += '\n次推荐 | 🚫 没有最适合的牌型'
    else:
        s += f'\n次推荐 | 共 {bad_count} 项 >\n'
        for i in range(bad_count):
            s += f'{maj_list[bad_value[i]]} '
    s += f"\n\n★ 星之锦囊 | AGLAS \'s Hints\n{majtips_list[tips_value]}"
    await jrmj.finish(Message([
        {"type": "text", "data": {"text": s}}
    ]))
