import asyncio
from code import interact
import os
import math
from xmlrpc.server import DocXMLRPCRequestHandler
import numpy as np
from typing import Optional, Dict, List
from io import BytesIO
import json
import requests
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from src.libraries.maimaidx_music import get_cover_len5_id, total_list
from src import static
import datetime, random, pickle

wm_list = ['拼机', '推分', '越级', '下埋', '夜勤', '练底力', '练手法', '打旧框', '干饭', '抓DX分', '收歌', '理论值', '打东方曲', '打索尼克曲', '单推']
bwm_list_perfect = ['拆机:然后您被机修当场处决', '女装:怎么这么好康！（然后受到了欢迎）', '耍帅:看我耍帅还AP+', '击剑:Alea jacta est!(SSS+)', '打滴蜡熊:看我今天不仅推了分，还收了歌！', '日麻:看我三倍役满!!!你们三家全都起飞!!!', '出勤:不出则已，一出惊人，当场AP，羡煞众人。', '看手元:哦原来是这样！看了手元果真推分了。', '霸机:这么久群友都没来，霸机一整天不是梦！', '打Maipad: Maipad上收歌了，上机也收了。', '唱打: Let the bass kick! ', '抓绝赞: 把把2600，轻松理论值！']
bwm_list_bad = ['拆机:不仅您被机修当场处决，还被人尽皆知。', '女装:杰哥说你怎么这么好康！让我康康！！！（被堵在卫生间角落）', '耍帅:星星全都粉掉了......', '击剑:Alea jacta est!(指在线下真实击剑)', '打滴蜡熊:滴蜡熊打你。', '日麻:我居然立直放铳....等等..三倍役满??????', '出勤:当场分数暴毙，惊呆众人。', '看手元:手法很神奇，根本学不来。', '霸机:......群友曰:"霸机是吧？踢了！"', '打Maipad: 上机还是不大会......', '唱打: 被路人拍下上传到了某音。', '抓绝赞: 捏麻麻我超！！！ --- 这是绝赞(好)的音效。']
tips_list = ['在游戏过程中,请您不要大力拍打或滑动机器!', '建议您常多备一副手套。', '游玩时注意手指安全。', '游玩过程中注意财物安全。自己的财物远比一个SSS+要更有价值。', '底力不够？建议下埋！不要强行越级，手癖难解。', '文明游玩，游戏要排队，不要做不遵守游戏规则的玩家！', '人品值和宜忌每天0点都会刷新，不喜欢总体运势可以再随一次。', '疫情防护，人人有责。游玩结束后请主动佩戴口罩！', '出勤时注意交通安全。', '迪拉熊不断吃绝赞也不要大力敲打他哟。', '热知识：DX理论值是101.0000，但是旧框没有固定的理论值。', '冷知识：每个绝赞 Perfect 等级有 2600/2550/2500，俗称理论/50落/100落。']

def load_random_numbers():
    try:
        with open('src/static/rp.pickle', 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        return {}

def save_random_numbers(random_numbers):
    with open('src/static/rp.pickle', 'wb') as f:
        pickle.dump(random_numbers, f)

random_numbers = load_random_numbers()

def get_today():
    return datetime.date.today().strftime('%Y-%m-%d')

def check_date():
    today = get_today()
    if 'date' not in random_numbers or random_numbers['date'] != today:
        random_numbers.clear()
        random_numbers['date'] = today
        save_random_numbers(random_numbers)

def getCharWidth(o) -> int:
    widths = [
        (126, 1), (159, 0), (687, 1), (710, 0), (711, 1), (727, 0), (733, 1), (879, 0), (1154, 1), (1161, 0),
        (4347, 1), (4447, 2), (7467, 1), (7521, 0), (8369, 1), (8426, 0), (9000, 1), (9002, 2), (11021, 1),
        (12350, 2), (12351, 1), (12438, 2), (12442, 0), (19893, 2), (19967, 1), (55203, 2), (63743, 1),
        (64106, 2), (65039, 1), (65059, 0), (65131, 2), (65279, 1), (65376, 2), (65500, 1), (65510, 2),
        (120831, 1), (262141, 2), (1114109, 1),
    ]
    if o == 0xe or o == 0xf:
        return 0
    for num, wid in widths:
        if o <= num:
            return wid
    return 1

def coloumWidth(s: str):
    res = 0
    for ch in s:
        res += getCharWidth(ord(ch))
    return res

def changeColumnWidth(s: str, len: int) -> str:
    res = 0
    sList = []
    for ch in s:
        res += getCharWidth(ord(ch))
        if res <= len:
            sList.append(ch)
    return ''.join(sList)

def get_offset_for_true_mm(text, draw, font):
    anchor_bbox = draw.textbbox((0, 0), text, font=font, anchor='lt')
    anchor_center = (anchor_bbox[0] + anchor_bbox[2]) // 2, (anchor_bbox[1] + anchor_bbox[3]) // 2
    mask_bbox = font.getmask(text).getbbox()
    mask_center = (mask_bbox[0] + mask_bbox[2]) // 2, (mask_bbox[1] + mask_bbox[3]) // 2
    return anchor_center[0] - mask_center[0], anchor_center[1] - mask_center[1]

async def jrwm_pic(qq: int) -> Optional[Image.Image]:
    check_date()
    today = get_today()
    combined = (qq, today)
    h = hash(str(qq) + today)
    random.seed(h)
    r = random.random()
    rp = hash(str(r) + str(combined)) % 100
    
    if combined in random_numbers:
        rp = random_numbers[combined]
        
    random_numbers[combined] = rp
    save_random_numbers(random_numbers)
    luck = hash(int((h * 4) / 3)) % 100
    ap = hash(int(((luck * 100) * (rp) * (r / 4 % 100)))) % 100
    wm_value = []
    good_value = {}
    bad_value = {}
    good_count = 0
    bad_count = 0
    dwm_value_1 = random.randint(0,11)
    dwm_value_2 = random.randint(0,11)
    tips_value = random.randint(0,11)
    now = datetime.datetime.now()
    for i in range(14):
        wm_value.append(h & 3)
        h >>= 2
    pic_dir = 'src/static/mai/pic/'         
    baseimage =  Image.open(os.path.join(pic_dir, f'StarTips.png')).convert('RGBA')
    font = ImageFont.truetype('src/static/HOS.ttf', 36, encoding='utf-8')
    fonttips = ImageFont.truetype('src/static/HOS.ttf', 24, encoding='utf-8')
    font1 = ImageFont.truetype('src/static/HOS.ttf', 38, encoding='utf-8')
    fontLV = ImageFont.truetype('src/static/HOS.ttf', 72, encoding='utf-8')
    fontBold = ImageFont.truetype('src/static/HOS_Med.ttf', 20, encoding='utf-8')
    fontBoldL = ImageFont.truetype('src/static/HOS_Med.ttf', 48, encoding='utf-8')
    imageDraw = ImageDraw.Draw(baseimage);
    imageDraw.text((48, 125), f"{now.year}/{now.month}/{now.day} {now.hour}:{now.strftime('%M')}:{now.strftime('%S')}", 'white', font)
    offset = get_offset_for_true_mm(f"{ap}", imageDraw, fontLV)
    if luck >= 50:
        imageDraw.text((962, 228), f"吉", 'black', font1)
    else:
        imageDraw.text((962, 228), f"凶", 'black', font1)
    if dwm_value_1 == dwm_value_2:
        imageDraw.text((130, 555), f"并无适宜。", 'white', font)
        imageDraw.text((130, 705), f"也并无忌惮。", 'white', font)
    else:
        imageDraw.text((130, 555), f"{bwm_list_perfect[dwm_value_1]}", 'white', font)
        imageDraw.text((130, 705), f"{bwm_list_bad[dwm_value_2]}", 'white', font)
    if ap < 10:
        imageDraw.text((197 + offset[0], 934 + offset[1]), f"{ap}", 'white', fontLV, anchor = 'mm')
    else:
        imageDraw.text((194 + offset[0], 934 + offset[1]), f"{ap}", 'white', fontLV, anchor = 'mm')
    for i in range(14):
        if wm_value[i] == 3:
            good_value[good_count] = i
            good_count = good_count + 1
        elif wm_value[i] == 0:
            bad_value[bad_count] = i
            bad_count = bad_count + 1
    if good_count == 0:
        imageDraw.text((420, 925), f"出勤诸事不宜。", 'black', font)
    else:
        imageDraw.text((420, 925), f"出勤宜做以下 {good_count} 项事:", 'black', font)
        s = ""
        for i in range(good_count):
            s += f'{wm_list[good_value[i]]} '
        slist = s.split(" ")
        newslist = ""
        for i in range(len(slist)):
            if i % 7 == 0 and i != 0:
                newslist += "\n"
            newslist += f'{slist[i]} '
        imageDraw.text((350, 1000), f"{newslist}", 'black', font)
    if bad_count == 0:
        imageDraw.text((420, 1100), f"出勤一切顺利。", 'black', font)
    else:
        imageDraw.text((420, 1100), f"出勤不宜做以下 {bad_count} 项事:", 'black', font)
        s = ""
        for i in range(bad_count):
            s += f'{wm_list[bad_value[i]]} '
        slist = s.split(" ")
        newslist = ""
        for i in range(len(slist)):
            if i % 7 == 0 and i != 0:
                newslist += "\n"
            newslist += f'{slist[i]} '
        imageDraw.text((350, 1175), f"{newslist}", 'black', font)
    imageDraw.text((110, 1425), f"{tips_list[tips_value]}", 'black', fonttips)
    music = total_list[hash(qq) % len(total_list)]
    try:
        file = requests.get(f"https://www.diving-fish.com/covers/{get_cover_len5_id(music['id'])}.jpg")
        imagedata = Image.open(BytesIO(file.content)).convert('RGBA')
        imagedata = imagedata.resize((int(400), int(400)))
    except:
         try:
             pic_cover = 'src/static/mai/cover/'
             try:
                imagedata = Image.open(os.path.join(pic_cover, f"{get_cover_len5_id(music['id'])}.jpg")).convert('RGBA')
             except:
                imagedata = Image.open(os.path.join(pic_cover, f"{get_cover_len5_id(music['id'])}.png")).convert('RGBA')
             imagedata = imagedata.resize((int(400), int(400)))
         except:
             imagedata = Image.open(os.path.join(pic_dir, f'noimage.png')).convert('RGBA')
             imagedata = imagedata.resize((int(400), int(400)))
    baseimage.paste(imagedata, (90,1801), mask=imagedata.split()[3])
    imageDraw.text((582, 1773), f"{music['id']}", 'black', fontBold)
    if coloumWidth(music["title"]) > 30:
        title = changeColumnWidth(music["title"], 20) + '...'
        imageDraw.text((539, 1823), title, 'black', fontBoldL)
    else:
        imageDraw.text((539, 1823), f"{music['title']}", 'black', fontBoldL)
    imageDraw.text((539, 1890), f"{music['basic_info']['artist']}", 'black', fonttips)
    imageDraw.text((539, 2040), f"{music['basic_info']['genre']}", 'black', fonttips)
    imageDraw.text((539, 2150), f"{music['basic_info']['from']}", 'black', fonttips)
    imageDraw.text((95, 2290), f'{"  -  ".join(music["level"])}', 'black', font1)
    return baseimage

async def charts_info(id: str, level_index: int) -> (Optional[Image.Image]):
    music = total_list.by_id(id)
    chart = music['charts'][level_index]
    ds = music['ds'][level_index]
    level = music['level'][level_index]
    stats = music['stats'][level_index]
    pic_dir = 'src/static/mai/pic/'         
    baseimage =  Image.open(os.path.join(pic_dir, f'levelid.png')).convert('RGBA')
    if level_index == 0:
        pic= 'BSC'
    elif level_index == 1:
        pic = 'ADV'
    elif level_index == 2:
        pic = 'EXP'
    elif level_index == 3:
        pic = 'MST'
    else:
        pic = 'MST_Re'
    image = Image.open(os.path.join(pic_dir, f'1{pic}.png')).convert('RGBA')
    image = image.resize((int(image.size[0] * 1), int(image.size[1] * 1)))
    try:
        tag = "{:.2f}".format(stats['fit_diff'])
    except:
        tag = "Insufficient"
    try:
        file = requests.get(f"https://www.diving-fish.com/covers/{get_cover_len5_id(music['id'])}.jpg")
        imagedata = Image.open(BytesIO(file.content)).convert('RGBA')
        imagedata = imagedata.resize((int(600), int(600)))
    except:
        try:
            pic_cover = 'src/static/mai/cover/'
            try:
                imagedata = Image.open(os.path.join(pic_cover, f"{get_cover_len5_id(music['id'])}.jpg")).convert('RGBA')
            except:
                imagedata = Image.open(os.path.join(pic_cover, f"{get_cover_len5_id(music['id'])}.png")).convert('RGBA')
            imagedata = imagedata.resize((int(600), int(600)))
        except:
            imagedata = Image.open(os.path.join(pic_dir, f'noimage.png')).convert('RGBA')
        if pic == 'MST_Re':
            imagedata.paste(image, (8,8), mask=image.split()[3])
        else:
            imagedata.paste(image, (5,8), mask=image.split()[3])
        baseimage.paste(imagedata, (0,0), mask=imagedata.split()[3])
        font = ImageFont.truetype('src/static/HOS.ttf', 19, encoding='utf-8')
        fontBold = ImageFont.truetype('src/static/HOS_Med.ttf', 13, encoding='utf-8')
        fontBoldL = ImageFont.truetype('src/static/HOS_Med.ttf', 28, encoding='utf-8')
        fontLV = ImageFont.truetype('src/static/HOS.ttf', 36, encoding='utf-8')
        fontforLV = ImageFont.truetype('src/static/Poppins.otf', 40, encoding='utf-8')
        fontBoldLV = ImageFont.truetype('src/static/HOS_Med.ttf', 26, encoding='utf-8')
        imageDraw = ImageDraw.Draw(baseimage);
        if len(chart['notes']) == 4:
            imagestandard = Image.open(os.path.join(pic_dir, f'UI_UPE_Infoicon_StandardMode.png')).convert('RGBA')
            imagestandard = imagestandard.resize((int(imagestandard.size[0] * 0.8), int(imagestandard.size[1] * 0.8)))
            baseimage.paste(imagestandard, (480,26), mask=imagestandard.split()[3])
            imageDraw.text((63, 625), f'{music["id"]}', 'black', fontBold)
            if coloumWidth(music["title"]) > 30:
                title = changeColumnWidth(music["title"], 20) + '...'
                imageDraw.text((33, 670), title, 'black', fontBoldL)
            else:
                imageDraw.text((33, 670), f'{music["title"]}', 'black', fontBoldL)
            if str(level).rfind("+") == -1:
                imageDraw.text((497, 657), f'{level}', 'white', fontforLV)
            else:
                imageDraw.text((493, 657), f'{level}', 'white', fontforLV)
            imageDraw.text((355, 840), f'{ds}', 'black', fontBoldLV)
            imageDraw.text((33, 715), f'{music["basic_info"]["artist"]}', 'black', font)
            imageDraw.text((55, 854), f'{tag}', 'black', font)
            imageDraw.text((55, 936), f'{chart["charter"]}', 'black', font)
            tap = chart['notes'][0]
            hold = chart['notes'][1]
            slide = chart['notes'][2]
            breaknote = chart['notes'][3]
            if int(tap) >= 100:
                imageDraw.text((41, 1100), f'{tap}', 'white', fontLV)
            elif int(tap) < 100 and int(tap) >= 10:
                imageDraw.text((49, 1100), f'{tap}', 'white', fontLV)
            else:
                imageDraw.text((57, 1100), f'{tap}', 'white', fontLV)
            if int(slide) >= 100:
                imageDraw.text((273, 1100), f'{slide}', 'white', fontLV)
            elif int(slide) < 100 and int(slide) >= 10:
                imageDraw.text((281, 1100), f'{slide}', 'white', fontLV)
            else:
                imageDraw.text((289, 1100), f'{slide}', 'white', fontLV)
            imageDraw.text((398, 1100), f'--', 'white', fontLV)
            if int(hold) >= 100:
                imageDraw.text((153, 1100), f'{hold}', 'white', fontLV)
            elif int(hold) < 100 and int(hold) >= 10:
                imageDraw.text((164, 1100), f'{hold}', 'white', fontLV)
            else:
                imageDraw.text((172, 1100), f'{hold}', 'white', fontLV)
            if int(breaknote) >= 100:
                imageDraw.text((502, 1100), f'{breaknote}', 'white', fontLV)
            elif int(breaknote) < 100 and int(breaknote) >= 10:
                imageDraw.text((510, 1100), f'{breaknote}', 'white', fontLV)
            else:
                imageDraw.text((518, 1100), f'{breaknote}', 'white', fontLV)
            imageDraw.text((355, 927), f'{tap + slide + hold + breaknote}', 'white', fontBoldLV)
        else:
            imagedx = Image.open(os.path.join(pic_dir, f'UI_UPE_Infoicon_DeluxeMode.png')).convert('RGBA')
            imagedx = imagedx.resize((int(imagedx.size[0] * 0.8), int(imagedx.size[1] * 0.8)))
            baseimage.paste(imagedx, (480,26), mask=imagedx.split()[3])
            imageDraw.text((63, 625), f'{music["id"]}', 'black', fontBold)
            if coloumWidth(music["title"]) > 30:
                title = changeColumnWidth(music["title"], 20) + '...'
                imageDraw.text((33, 670), title, 'black', fontBoldL)
            else:
                imageDraw.text((33, 670), f'{music["title"]}', 'black', fontBoldL)
            if str(level).rfind("+") == -1:
                imageDraw.text((497, 657), f'{level}', 'white', fontforLV)
            else:
                imageDraw.text((493, 657), f'{level}', 'white', fontforLV)
            imageDraw.text((355, 840), f'{ds}', 'black', fontBoldLV)
            imageDraw.text((33, 715), f'{music["basic_info"]["artist"]}', 'black', font)
            imageDraw.text((55, 854), f'{tag}', 'black', font)
            imageDraw.text((55, 936), f'{chart["charter"]}', 'black', font)
            tap = chart['notes'][0]
            hold = chart['notes'][1]
            slide = chart['notes'][2]
            touch = chart['notes'][3]
            breaknote = chart['notes'][4]
            if int(tap) >= 100:
                imageDraw.text((41, 1100), f'{tap}', 'white', fontLV)
            elif int(tap) < 100 and int(tap) >= 10:
                imageDraw.text((49, 1100), f'{tap}', 'white', fontLV)
            else:
                imageDraw.text((57, 1100), f'{tap}', 'white', fontLV)
            if int(slide) >= 100:
                imageDraw.text((273, 1100), f'{slide}', 'white', fontLV)
            elif int(slide) < 100 and int(slide) >= 10:
                imageDraw.text((281, 1100), f'{slide}', 'white', fontLV)
            else:
                imageDraw.text((289, 1100), f'{slide}', 'white', fontLV)
            if int(touch) >= 100:
                imageDraw.text((387, 1100), f'{touch}', 'white', fontLV)
            elif int(touch) < 100 and int(touch) >= 10:
                imageDraw.text((395, 1100), f'{touch}', 'white', fontLV)
            else:
                imageDraw.text((403, 1100), f'{touch}', 'white', fontLV)
            if int(hold) >= 100:
                imageDraw.text((153, 1100), f'{hold}', 'white', fontLV)
            elif int(hold) < 100 and int(hold) >= 10:
                imageDraw.text((164, 1100), f'{hold}', 'white', fontLV)
            else:
                imageDraw.text((172, 1100), f'{hold}', 'white', fontLV)
            if int(breaknote) >= 100:
                imageDraw.text((502, 1100), f'{breaknote}', 'white', fontLV)
            elif int(breaknote) < 100 and int(breaknote) >= 10:
                imageDraw.text((510, 1100), f'{breaknote}', 'white', fontLV)
            else:
                imageDraw.text((518, 1100), f'{breaknote}', 'white', fontLV)
            imageDraw.text((355, 927), f'{tap + slide + hold + breaknote + touch}', 'white', fontBoldLV)
    return baseimage

async def music_info(id: str) -> (Optional[Image.Image]):
    music = total_list.by_id(id)
    pic_dir = 'src/static/mai/pic/'         
    baseimage = Image.open(os.path.join(pic_dir, f'id.png')).convert('RGBA')
    try:
        file = requests.get(f"https://www.diving-fish.com/covers/{get_cover_len5_id(music['id'])}.jpg")
        imagedata = Image.open(BytesIO(file.content)).convert('RGBA')
        imagedata = imagedata.resize((int(600), int(600)))
    except:
        try:
            pic_cover = 'src/static/mai/cover/'
            try:
                imagedata = Image.open(os.path.join(pic_cover, f"{get_cover_len5_id(music['id'])}.jpg")).convert('RGBA')
            except:
                imagedata = Image.open(os.path.join(pic_cover, f"{get_cover_len5_id(music['id'])}.png")).convert('RGBA')
            imagedata = imagedata.resize((int(600), int(600)))
        except:
            imagedata = Image.open(os.path.join(pic_dir, f'noimage.png')).convert('RGBA')
        baseimage.paste(imagedata, (0,0), mask=imagedata.split()[3])
        font = ImageFont.truetype('src/static/HOS.ttf', 19, encoding='utf-8')
        fontBold = ImageFont.truetype('src/static/HOS_Med.ttf', 13, encoding='utf-8')
        fontBoldL = ImageFont.truetype('src/static/HOS_Med.ttf', 28, encoding='utf-8')
        fontLV = ImageFont.truetype('src/static/HOS.ttf', 34, encoding='utf-8')
        fontBoldLV = ImageFont.truetype('src/static/HOS_Med.ttf', 20, encoding='utf-8')
        fontTools = ImageFont.truetype('src/static/adobe_simhei.otf', 20, encoding='utf-8')
        imageDraw = ImageDraw.Draw(baseimage);
        imageDraw.text((70, 618), f'{music["id"]}', 'black', fontBold)
        if coloumWidth(music["title"]) > 30:
            title = changeColumnWidth(music["title"], 20) + '...'
            imageDraw.text((33, 660), title, 'black', fontBoldL)
        else:
            imageDraw.text((33, 660), f'{music["title"]}', 'black', fontBoldL)
        if int(music["basic_info"]["bpm"]) >= 100:
            imageDraw.text((511, 637), f'{music["basic_info"]["bpm"]}', 'black', fontLV)
        else:
            imageDraw.text((508, 637), f' {music["basic_info"]["bpm"]}', 'black', fontLV)
        imageDraw.text((37, 705), f'{music["basic_info"]["artist"]}', 'black', font)
        imageDraw.text((61, 850), f'{music["basic_info"]["genre"]}', 'black', font)
        imageDraw.text((61, 940), f'{music["basic_info"]["from"]}', 'black', font)
        imageDraw.text((50, 1065), f'{"  -  ".join(music["level"])}', 'black', fontLV)
        imageDraw.text((50, 1170), f'{" - ".join(str(music["ds"]).split(","))}', 'black', fontBoldLV)
    return baseimage
