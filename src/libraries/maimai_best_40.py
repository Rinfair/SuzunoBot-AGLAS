# Code by Killua, Credits: Xyb, Diving_Fish
import asyncio
from code import interact
import os
import math
from tokenize import Double
from xmlrpc.server import DocXMLRPCRequestHandler
import numpy as np
from typing import Optional, Dict, List, Tuple
from io import BytesIO
import json
import requests
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from src.libraries.maimaidx_music import get_cover_len5_id, total_list
from src import static


scoreRank = 'D C B BB BBB A AA AAA S S+ SS SS+ SSS SSS+'.lower().split(' ')
combo = ' FC FC+ AP AP+'.split(' ')
diffs = 'Basic Advanced Expert Master Re:Master'.split(' ')


class ChartInfo(object):
    def __init__(self, idNum: str, diff: int, tp: str, achievement: float, ra: int, comboId: int, scoreId: int, dxScore: int,
                 syncId: int, title: str, ds: float, lv: str):
        self.idNum = idNum
        self.diff = diff
        self.tp = tp
        self.achievement = achievement
        self.ra = ra
        self.comboId = comboId
        self.scoreId = scoreId
        self.syncId = syncId
        self.dxScore = dxScore
        self.title = title
        self.ds = ds
        self.lv = lv

    def __str__(self):
        return '%-50s' % f'{self.title} [{self.tp}]' + f'{self.ds}\t{diffs[self.diff]}\t{self.ra}'

    def __eq__(self, other):
        return self.ra == other.ra

    def __lt__(self, other):
        return self.ra < other.ra

    @classmethod
    def from_json(cls, data):
        rate = ['d', 'c', 'b', 'bb', 'bbb', 'a', 'aa', 'aaa', 's', 'sp', 'ss', 'ssp', 'sss', 'sssp']
        ri = rate.index(data["rate"])
        fc = ['', 'fc', 'fcp', 'ap', 'app']
        fs = ['', 'fs', 'fsp', 'fsd', 'fsdp']
        fi = fc.index(data["fc"])
        fsi = fs.index(data["fs"])
        return cls(
            idNum=total_list.by_title(data["title"]).id,
            title=data["title"],
            diff=data["level_index"],
            ra=data["ra"],
            ds=data["ds"],
            comboId=fi,
            syncId=fsi,
            scoreId=ri,
            dxScore=data["dxScore"],
            lv=data["level"],
            achievement=data["achievements"],
            tp=data["type"]
        )


class BestList(object):

    def __init__(self, size: int):
        self.data = []
        self.size = size

    def push(self, elem: ChartInfo):
        if len(self.data) >= self.size and elem < self.data[-1]:
            return
        self.data.append(elem)
        self.data.sort()
        self.data.reverse()
        while (len(self.data) > self.size):
            del self.data[-1]

    def pop(self):
        del self.data[-1]

    def __str__(self):
        return '[\n\t' + ', \n\t'.join([str(ci) for ci in self.data]) + '\n]'

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        return self.data[index]


class DrawBest(object):

    def __init__(self, sdBest: BestList, dxBest: BestList, userName: str, playerRating: int, musicRating: int, qqId: int or str = None, b50: bool = False, platenum: int or str = 0, platetitle: int or str = 0):
        self.sdBest = sdBest
        self.dxBest = dxBest
        self.userName = self._stringQ2B(userName)
        self.playerRating = playerRating
        self.musicRating = musicRating
        self.qqId = qqId
        self.b50 = b50
        self.rankRating = self.playerRating - self.musicRating
        self.fail = 0
        if self.b50:
            self.playerRating = 0
            for sd in sdBest:
                self.playerRating += computeRa(sd.ds, sd.achievement, True)
            for dx in dxBest:
                self.playerRating += computeRa(dx.ds, dx.achievement, True)
        self.platenum = platenum
        self.platetitle = platetitle
        self.pic_dir = 'src/static/mai/pic/'
        self.cover_dir = 'src/static/mai/cover/'
        if self.b50:
            self.img = Image.open(self.pic_dir + 'b50.png').convert('RGBA')
        else:
            self.img = Image.open(self.pic_dir + 'b40.png').convert('RGBA')
        self.ROWS_IMG = [2]
        if self.b50:
            for i in range(8):
                self.ROWS_IMG.append(140 + 144 * i)
        else:
            for i in range(6):
                self.ROWS_IMG.append(140 + 144 * i)
        self.COLOUMS_IMG = []
        for i in range(6):
            self.COLOUMS_IMG.append(2 + 258 * i)
        for i in range(4):
            self.COLOUMS_IMG.append(2 + 258 * i)
        self.draw()

    def _Q2B(self, uchar):
        """单个字符 全角转半角"""
        inside_code = ord(uchar)
        if inside_code == 0x3000:
            inside_code = 0x0020
        else:
            inside_code -= 0xfee0
        if inside_code < 0x0020 or inside_code > 0x7e:  # 转完之后不是半角字符返回原来的字符
            return uchar
        return chr(inside_code)

    def _stringQ2B(self, ustring):
        """把字符串全角转半角"""
        return "".join([self._Q2B(uchar) for uchar in ustring])

    def _getCharWidth(self, o) -> int:
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

    def _coloumWidth(self, s: str):
        res = 0
        for ch in s:
            res += self._getCharWidth(ord(ch))
        return res

    def _changeColumnWidth(self, s: str, len: int) -> str:
        res = 0
        sList = []
        for ch in s:
            res += self._getCharWidth(ord(ch))
            if res <= len:
                sList.append(ch)
        return ''.join(sList)

    def _resizePic(self, img: Image.Image, time: float):
        return img.resize((int(img.size[0] * time), int(img.size[1] * time)))

    def diffpic(self, diff: str) -> str:
        pic = ''
        if diff == 0:
            pic = 'BSC'
        elif diff == 1:
            pic = 'ADV'
        elif diff == 2:
            pic = 'EXP'
        elif diff == 3:
            pic = 'MST'
        elif diff == 4:
            pic = 'MST_Re'
        return f'UI_PFC_MS_Info02_{pic}.png' 

    def full_dxScore_calc(self, id: str, diff: str) -> str:
        music = total_list.by_id(id)
        chart = music['charts'][int(diff)]
        if len(chart['notes']) == 4:
            fulldxScore = (int(chart['notes'][0]) + int(chart['notes'][1]) + int(chart['notes'][2]) + int(chart['notes'][3])) * 3
        else:
            fulldxScore = (int(chart['notes'][0]) + int(chart['notes'][1]) + int(chart['notes'][2]) + int(chart['notes'][3]) + int(chart['notes'][4])) * 3
        return str(fulldxScore)

    def percent_dxScore_calc(self, userdxScore: int, fulldxScore: str) -> str:
        p = (int(userdxScore)/int(fulldxScore)) * 100
        if p >= 97:
            return "5"
        elif p >= 95:
            return "4"
        elif p >= 93:
            return "3"
        elif p >= 90:
            return "2"
        elif p >= 85:
            return "1"
        else:
            return ""

    def rank (self)-> str:
        ranker = '00'
        if self.rankRating == 250:
            ranker = '00'
        elif self.rankRating == 500:
            ranker = '00'
        elif self.rankRating == 750:
            ranker = '00'
        elif self.rankRating == 1000:
            ranker = '01'
        elif self.rankRating == 1200:
            ranker = '02'
        elif self.rankRating == 1400:
            ranker = '03'
        elif self.rankRating == 1500:
            ranker = '04'
        elif self.rankRating == 1600:
            ranker = '05'
        elif self.rankRating == 1700:
            ranker = '06'
        elif self.rankRating == 1800:
            ranker = '07'
        elif self.rankRating == 1850:
            ranker = '08'
        elif self.rankRating == 1900:
            ranker = '09'
        elif self.rankRating == 1950:
            ranker = '10'
        elif self.rankRating == 2000:
            ranker = '11'
        elif self.rankRating == 2010:
            ranker = '12'
        elif self.rankRating == 2020:
            ranker = '13'
        elif self.rankRating == 2030:
            ranker = '14'
        elif self.rankRating == 2040:
            ranker = '15'
        elif self.rankRating == 2050:
            ranker = '16'
        elif self.rankRating == 2060:
            ranker = '17'
        elif self.rankRating == 2070:
            ranker = '18'
        elif self.rankRating == 2080:
            ranker = '19'
        elif self.rankRating == 2090:
            ranker = '20'
        elif self.rankRating == 2100:
            ranker = '21'
        return f'UI_CMN_DaniPlate_{ranker}.png'

    def _findRaPic(self) -> str:
        num = '10'
        if self.playerRating < 1000:
            num = '01'
        elif self.playerRating < 2000:
            num = '02'
        elif self.playerRating < (3000 if not self.b50 else 4000):
            num = '03'
        elif self.playerRating < (4000 if not self.b50 else 7000):
            num = '04'
        elif self.playerRating < (5000 if not self.b50 else 10000):
            num = '05'
        elif self.playerRating < (6000 if not self.b50 else 12000):
            num = '06'
        elif self.playerRating < (7000 if not self.b50 else 13000):
            num = '07'
        elif self.playerRating < (8000 if not self.b50 else 14500):
            num = '08'
        elif self.playerRating < (8500 if not self.b50 else 15000):
            num = '09'
        return f'UI_CMN_DXRating_S_{num}.png'

    def set_trans(self, img):
        img = img.convert("RGBA")
        x, y = img.size
        for i in range(x):
            for k in range(y):
                color = img.getpixel((i, k))
                color = color[:-1] + (100, )
                img.putpixel((i, k), color)
        return img

    def _drawRating(self, ratingBaseImg: Image.Image):
        COLOUMS_RATING = [74, 92, 110, 129, 147]
        theRa = self.playerRating
        i = 4
        while theRa:
            digit = theRa % 10
            theRa = theRa // 10
            digitImg = Image.open(os.path.join(self.pic_dir, f'UI_NUM_Drating_{digit}.png')).convert('RGBA')
            digitImg = self._resizePic(digitImg, 0.7)
            ratingBaseImg.paste(digitImg, (COLOUMS_RATING[i] - 2, 14), mask=digitImg.split()[3])
            i -= 1
        return ratingBaseImg

    def _drawBestList(self, img: Image.Image, sdBest: BestList, dxBest: BestList):
        itemW = 246
        itemH = 132
        Color = [(69, 193, 36), (255, 186, 1), (255, 90, 102), (134, 49, 200), (217, 197, 233)]
        levelTriagle = [(itemW, 0), (itemW - 12, 0), (itemW, 12)]
        rankPic = 'D C B BB BBB A AA AAA S Sp SS SSp SSS SSSp'.split(' ')
        comboPic = ' FC FCp AP APp'.split(' ')
        syncPic = ' FS FSp FSD FSDp'.split(' ')
        imgDraw = ImageDraw.Draw(img)
        font2 = ImageFont.truetype('src/static/HOS.ttf', 8, encoding='utf-8')
        font3 = ImageFont.truetype('src/static/HOS.ttf', 12, encoding='utf-8')
        titleFontName = 'src/static/adobe_simhei.otf'
        for num in range(0, len(sdBest)):
            i = num // 5
            j = num % 5
            chartInfo = sdBest[num]
            pngPath = os.path.join(self.cover_dir, f'{get_cover_len5_id(chartInfo.idNum)}.png')
            if not os.path.exists(pngPath):
                pngPath = os.path.join(self.cover_dir, f'{get_cover_len5_id(chartInfo.idNum)}.jpg')
            if not os.path.exists(pngPath):
                pngPath = os.path.join(self.cover_dir, '01000.png')
            temp = Image.open(pngPath).convert('RGB')
            temp = self._resizePic(temp, itemW / temp.size[0]) 
            temp = temp.crop((0, (temp.size[1] - itemH) / 2, itemW, (temp.size[1] + itemH) / 2))
            temp = temp.filter(ImageFilter.GaussianBlur(2))
            temp = temp.point(lambda p: p * 0.72)
            mbImg = Image.open(os.path.join(self.pic_dir, 'mb.png')).convert('RGBA')
            temp.paste(mbImg, (0, 0), mbImg.split()[3])
            tempDraw = ImageDraw.Draw(temp)
            fullScore = self.full_dxScore_calc(chartInfo.idNum, chartInfo.diff)
            dxper = self.percent_dxScore_calc(int(chartInfo.dxScore), fullScore)
            if chartInfo.tp == 'SD':
                sdImg = Image.open(os.path.join(self.pic_dir, 'UI_UPE_Infoicon_StandardMode.png')).convert('RGBA')
                sdImg = self._resizePic(sdImg, 0.6)
                if dxper == "":
                    temp.paste(sdImg, (170, 6), sdImg.split()[3])
                else:
                    temp.paste(sdImg, (170, 16), sdImg.split()[3])
            elif chartInfo.tp == 'DX':
                dxImg = Image.open(os.path.join(self.pic_dir, 'UI_UPE_Infoicon_DeluxeMode.png')).convert('RGBA')
                dxImg = self._resizePic(dxImg, 0.6)
                if dxper == "":
                    temp.paste(dxImg, (170, 6), dxImg.split()[3])
                else:
                    temp.paste(dxImg, (170, 16), dxImg.split()[3])
            if dxper != "":
                dxstar = Image.open(os.path.join(self.pic_dir, f'dxstar_{dxper}.png')).convert('RGBA')
                dxstar = self._resizePic(dxstar, 0.65)
                temp.paste(dxstar, (170, 4), dxstar.split()[3])
            diffImg = Image.open(os.path.join(self.pic_dir, self.diffpic(chartInfo.diff))).convert('RGBA')
            temp.paste(diffImg, (0, 0), diffImg.split()[3])
            font = ImageFont.truetype(titleFontName, 16, encoding='utf-8')
            idfont = ImageFont.truetype('src/static/ExoM.ttf', 13, encoding='utf-8')
            trackid = chartInfo.idNum
            if int(chartInfo.idNum) < 10000 and chartInfo.tp == 'DX':
                trackid = str(int(trackid) + 10000)
            tempDraw.text((48, 6), f'{trackid}', 'white', idfont)
            title = chartInfo.title
            if self._coloumWidth(title) > 12:
                title = self._changeColumnWidth(title, 11) + '...'
            tempDraw.text((32, 27), title, 'white', font)
            font = ImageFont.truetype('src/static/Poppins.otf', 26, encoding='utf-8')
            tempDraw.text((30, 42), f'{"%.4f" % chartInfo.achievement}%', 'white', font)
            rankImg = Image.open(os.path.join(self.pic_dir, f'UI_GAM_Rank_{rankPic[chartInfo.scoreId]}.png')).convert('RGBA')
            rankImg = self._resizePic(rankImg, 0.8)
            temp.paste(rankImg, (156, 40), rankImg.split()[3])
            if chartInfo.comboId:
                comboImg = Image.open(os.path.join(self.pic_dir, f'UI_MSS_MBase_Icon_{comboPic[chartInfo.comboId]}_S.png')).convert('RGBA')
                comboImg = self._resizePic(comboImg, 0.6)
                temp.paste(comboImg, (172, 81), comboImg.split()[3])
            else:
                comboImg = Image.open(os.path.join(self.pic_dir, f'UI_MSS_MBase_Icon_Blank.png')).convert('RGBA')
                comboImg = self._resizePic(comboImg, 0.6)
                temp.paste(comboImg, (172, 81), comboImg.split()[3])
            if chartInfo.syncId:
                syncImg = Image.open(os.path.join(self.pic_dir, f'UI_MSS_MBase_Icon_{syncPic[chartInfo.syncId]}_S.png')).convert('RGBA')
                syncImg = self._resizePic(syncImg, 0.6)
                temp.paste(syncImg, (201, 81), syncImg.split()[3])
            else:
                syncImg = Image.open(os.path.join(self.pic_dir, f'UI_MSS_MBase_Icon_Blank.png')).convert('RGBA')
                syncImg = self._resizePic(syncImg, 0.6)
                temp.paste(syncImg, (201, 81), syncImg.split()[3])
            font = ImageFont.truetype('src/static/HOS.ttf', 11, encoding='utf-8')
            tempDraw.text((82, 76), f'{chartInfo.dxScore} / {fullScore}', 'black', font)
            font = ImageFont.truetype('src/static/Exo.ttf', 18, encoding='utf-8')
            tempDraw.text((36, 102), f'{chartInfo.ds}', 'black', font)
            font = ImageFont.truetype('src/static/Exo.ttf', 13, encoding='utf-8')
            tempDraw.text((90, 105), f'{int((int(chartInfo.dxScore)/int(fullScore)) * 100)}%', 'black', font)
            font = ImageFont.truetype('src/static/ExoM.ttf', 21, encoding='utf-8')
            tempDraw.text((135, 99), f'{chartInfo.ra if not self.b50 else computeRa(chartInfo.ds, chartInfo.achievement, True)}', 'black', font)
            font = ImageFont.truetype('src/static/Poppins.otf', 13, encoding='utf-8')
            if num >= 9:
                font = ImageFont.truetype('src/static/Poppins.otf', 13, encoding='utf-8')
                tempDraw.text((177, 105), f'#{num + 1}/{len(sdBest)}', 'black', font)
            else:
                font = ImageFont.truetype('src/static/Poppins.otf', 13, encoding='utf-8')
                tempDraw.text((181, 105), f'#{num + 1}/{len(sdBest)}', 'black', font)
            alphaPath = os.path.join(self.pic_dir, f'alpha.png')
            alpha = Image.open(alphaPath).convert('L')
            alpha = ImageOps.invert(alpha)
            temp.putalpha(alpha)
            img.paste(temp, (self.COLOUMS_IMG[j] + 4, self.ROWS_IMG[i + 1] + 4), mask=temp.split()[3])
        for num in range(len(sdBest), sdBest.size):
            i = num // 5
            j = num % 5
            temp = Image.open(os.path.join(self.cover_dir, f'01000.png')).convert('RGB')
            temp = self._resizePic(temp, itemW / temp.size[0])
            temp = temp.crop((0, (temp.size[1] - itemH) / 2, itemW, (temp.size[1] + itemH) / 2))
            temp = temp.filter(ImageFilter.GaussianBlur(2))
            alphaPath = os.path.join(self.pic_dir, f'alpha.png')
            alpha = Image.open(alphaPath).convert('L')
            alpha = ImageOps.invert(alpha)
            temp.putalpha(alpha)
            img.paste(temp, (self.COLOUMS_IMG[j] + 4, self.ROWS_IMG[i + 1] + 4), mask=temp.split()[3])

        for num in range(0, len(dxBest)):
            i = num // 5 
            j = num % 5
            chartInfo = dxBest[num]
            pngPath = os.path.join(self.cover_dir, f'{get_cover_len5_id(chartInfo.idNum)}.png')
            if not os.path.exists(pngPath):
                pngPath = os.path.join(self.cover_dir, f'{get_cover_len5_id(chartInfo.idNum)}.jpg')
            if not os.path.exists(pngPath):
                pngPath = os.path.join(self.cover_dir, '01000.png')
            temp = Image.open(pngPath).convert('RGB')
            temp = self._resizePic(temp, itemW / temp.size[0])
            temp = temp.crop((0, (temp.size[1] - itemH) / 2, itemW, (temp.size[1] + itemH) / 2))
            temp = temp.filter(ImageFilter.GaussianBlur(2))
            temp = temp.point(lambda p: p * 0.72)
            mbImg = Image.open(os.path.join(self.pic_dir, 'mb.png')).convert('RGBA')
            temp.paste(mbImg, (0, 0), mbImg.split()[3])
            tempDraw = ImageDraw.Draw(temp)
            fullScore = self.full_dxScore_calc(chartInfo.idNum, chartInfo.diff)
            dxper = self.percent_dxScore_calc(int(chartInfo.dxScore), fullScore)
            if chartInfo.tp == 'SD':
                sdImg = Image.open(os.path.join(self.pic_dir, 'UI_UPE_Infoicon_StandardMode.png')).convert('RGBA')
                sdImg = self._resizePic(sdImg, 0.6)
                if dxper == "":
                    temp.paste(sdImg, (170, 6), sdImg.split()[3])
                else:
                    temp.paste(sdImg, (170, 16), sdImg.split()[3])
            elif chartInfo.tp == 'DX':
                dxImg = Image.open(os.path.join(self.pic_dir, 'UI_UPE_Infoicon_DeluxeMode.png')).convert('RGBA')
                dxImg = self._resizePic(dxImg, 0.6)
                if dxper == "":
                    temp.paste(dxImg, (170, 6), dxImg.split()[3])
                else:
                    temp.paste(dxImg, (170, 16), dxImg.split()[3])
            if dxper != "":
                dxstar = Image.open(os.path.join(self.pic_dir, f'dxstar_{dxper}.png')).convert('RGBA')
                dxstar = self._resizePic(dxstar, 0.65)
                temp.paste(dxstar, (170, 4), dxstar.split()[3])
            diffImg = Image.open(os.path.join(self.pic_dir, self.diffpic(chartInfo.diff))).convert('RGBA')
            temp.paste(diffImg, (0, 0), diffImg.split()[3])
            font = ImageFont.truetype(titleFontName, 16, encoding='utf-8')
            idfont = ImageFont.truetype('src/static/ExoM.ttf', 13, encoding='utf-8')
            trackid = chartInfo.idNum
            if int(chartInfo.idNum) < 10000 and chartInfo.tp == 'DX':
                trackid = str(int(trackid) + 10000)
            tempDraw.text((48, 6), f'{trackid}', 'white', idfont)
            title = chartInfo.title
            if self._coloumWidth(title) > 12:
                title = self._changeColumnWidth(title, 11) + '...'
            tempDraw.text((32, 27), title, 'white', font)
            font = ImageFont.truetype('src/static/Poppins.otf', 26, encoding='utf-8')
            tempDraw.text((30, 42), f'{"%.4f" % chartInfo.achievement}%', 'white', font)
            rankImg = Image.open(os.path.join(self.pic_dir, f'UI_GAM_Rank_{rankPic[chartInfo.scoreId]}.png')).convert('RGBA')
            rankImg = self._resizePic(rankImg, 0.8)
            temp.paste(rankImg, (156, 40), rankImg.split()[3])
            if chartInfo.comboId:
                comboImg = Image.open(os.path.join(self.pic_dir, f'UI_MSS_MBase_Icon_{comboPic[chartInfo.comboId]}_S.png')).convert('RGBA')
                comboImg = self._resizePic(comboImg, 0.6)
                temp.paste(comboImg, (172, 81), comboImg.split()[3])
            else:
                comboImg = Image.open(os.path.join(self.pic_dir, f'UI_MSS_MBase_Icon_Blank.png')).convert('RGBA')
                comboImg = self._resizePic(comboImg, 0.6)
                temp.paste(comboImg, (172, 81), comboImg.split()[3])
            if chartInfo.syncId:
                syncImg = Image.open(os.path.join(self.pic_dir, f'UI_MSS_MBase_Icon_{syncPic[chartInfo.syncId]}_S.png')).convert('RGBA')
                syncImg = self._resizePic(syncImg, 0.6)
                temp.paste(syncImg, (201, 81), syncImg.split()[3])
            else:
                syncImg = Image.open(os.path.join(self.pic_dir, f'UI_MSS_MBase_Icon_Blank.png')).convert('RGBA')
                syncImg = self._resizePic(syncImg, 0.6)
                temp.paste(syncImg, (201, 81), syncImg.split()[3])
            font = ImageFont.truetype('src/static/HOS.ttf', 11, encoding='utf-8')
            tempDraw.text((82, 76), f'{chartInfo.dxScore} / {fullScore}', 'black', font)
            font = ImageFont.truetype('src/static/Exo.ttf', 18, encoding='utf-8')
            tempDraw.text((36, 102), f'{chartInfo.ds}', 'black', font)
            font = ImageFont.truetype('src/static/Exo.ttf', 13, encoding='utf-8')
            tempDraw.text((90, 105), f'{int((int(chartInfo.dxScore)/int(fullScore)) * 100)}%', 'black', font)
            font = ImageFont.truetype('src/static/ExoM.ttf', 21, encoding='utf-8')
            tempDraw.text((135, 99), f'{chartInfo.ra if not self.b50 else computeRa(chartInfo.ds, chartInfo.achievement, True)}', 'black', font)
            if num >= 9:
                font = ImageFont.truetype('src/static/Poppins.otf', 13, encoding='utf-8')
                tempDraw.text((177, 105), f'#{num + 1}/{len(dxBest)}', 'black', font)
            else:
                font = ImageFont.truetype('src/static/Poppins.otf', 13, encoding='utf-8')
                tempDraw.text((181, 105), f'#{num + 1}/{len(dxBest)}', 'black', font)
            alphaPath = os.path.join(self.pic_dir, f'alpha.png')
            alpha = Image.open(alphaPath).convert('L')
            alpha = ImageOps.invert(alpha)
            temp.putalpha(alpha)
            if self.b50:
                img.paste(temp, (self.COLOUMS_IMG[j] + 4, self.ROWS_IMG[i + 1] + 1081), mask=temp.split()[3])
            else:
                img.paste(temp, (self.COLOUMS_IMG[j] + 4, self.ROWS_IMG[i + 1] + 781), mask=temp.split()[3])
        for num in range(len(dxBest), dxBest.size):
            i = num // 5
            j = num % 5
            temp = Image.open(os.path.join(self.cover_dir, f'01000.png')).convert('RGB')
            temp = self._resizePic(temp, itemW / temp.size[0])
            temp = temp.crop((0, (temp.size[1] - itemH) / 2, itemW, (temp.size[1] + itemH) / 2))
            temp = temp.filter(ImageFilter.GaussianBlur(2))
            alphaPath = os.path.join(self.pic_dir, f'alpha.png')
            alpha = Image.open(alphaPath).convert('L')
            alpha = ImageOps.invert(alpha)
            temp.putalpha(alpha)
            if self.b50:
                img.paste(temp, (self.COLOUMS_IMG[j] + 4, self.ROWS_IMG[i + 1] + 1081), mask=temp.split()[3])
            else:
                img.paste(temp, (self.COLOUMS_IMG[j] + 4, self.ROWS_IMG[i + 1] + 781), mask=temp.split()[3])

    @staticmethod
    def _drawRoundRec(im, color, x, y, w, h, r):
        drawObject = ImageDraw.Draw(im)
        drawObject.ellipse((x, y, x + r, y + r), fill=color)
        drawObject.ellipse((x + w - r, y, x + w, y + r), fill=color)
        drawObject.ellipse((x, y + h - r, x + r, y + h), fill=color)
        drawObject.ellipse((x + w - r, y + h - r, x + w, y + h), fill=color)
        drawObject.rectangle((x + r / 2, y, x + w - (r / 2), y + h), fill=color)
        drawObject.rectangle((x, y + r / 2, x + w, y + h - (r / 2)), fill=color)

    def draw(self):
        if self.qqId:
            if self.platenum == 0:
                plateImg = Image.open(os.path.join(self.pic_dir, 'plate_1.png')).convert('RGBA')
            else:
                plateImg = Image.open(os.path.join(self.pic_dir, f'plate_{self.platenum}.png')).convert('RGBA')
            plateImg = self._resizePic(plateImg, 2)
            self.img.paste(plateImg, (9, 8), mask=plateImg.split()[3])
            resp = requests.get(f'http://q1.qlogo.cn/g?b=qq&nk={self.qqId}&s=100')
            qqLogo = Image.open(BytesIO(resp.content))
            borderImg1 = Image.fromarray(np.zeros((200, 200, 4), dtype=np.uint8)).convert('RGBA')
            borderImg2 = Image.fromarray(np.zeros((200, 200, 4), dtype=np.uint8)).convert('RGBA')
            self._drawRoundRec(borderImg1, (255, 0, 80), 0, 0, 200, 200, 40)
            self._drawRoundRec(borderImg2, (255, 255, 255), 3, 3, 193, 193, 30)
            borderImg1.paste(borderImg2, (0, 0), mask=borderImg2.split()[3])
            borderImg = borderImg1.resize((108, 108))
            borderImg.paste(qqLogo, (4, 4))
            borderImg = self._resizePic(borderImg, 0.995)
            self.img.paste(borderImg, (20, 17), mask=borderImg.split()[3])
        else:
            splashLogo = Image.open(os.path.join(self.pic_dir, 'UI_CMN_TabTitle_MaimaiTitle_Ver214.png')).convert('RGBA')
            splashLogo = self._resizePic(splashLogo, 0.65)
            self.img.paste(splashLogo, (10, 35), mask=splashLogo.split()[3])

        ratingBaseImg = Image.open(os.path.join(self.pic_dir, self._findRaPic())).convert('RGBA')
        ratingBaseImg = self._drawRating(ratingBaseImg)
        ratingBaseImg = self._resizePic(ratingBaseImg, 0.8)
        self.img.paste(ratingBaseImg, (240 if not self.qqId else 139, 12), mask=ratingBaseImg.split()[3])
        daniplateImg = Image.open(os.path.join(self.pic_dir, self.rank())).convert('RGBA')
        daniplateImg = self._resizePic(daniplateImg, 0.65)
        self.img.paste(daniplateImg, (395 if not self.qqId else 295, 9), mask=daniplateImg.split()[3])
        namePlateImg = Image.open(os.path.join(self.pic_dir, 'UI_TST_PlateMask.png')).convert('RGBA')
        namePlateImg = namePlateImg.resize((285, 40))
        namePlateDraw = ImageDraw.Draw(namePlateImg)
        font1 = ImageFont.truetype('src/static/HOS.ttf', 28, encoding='unic')
        namePlateDraw.text((12, 3), ' '.join(list(self.userName)), 'black', font1)
        nameDxImg = Image.open(os.path.join(self.pic_dir, 'UI_CMN_Name_DX.png')).convert('RGBA')
        nameDxImg = self._resizePic(nameDxImg, 0.9)
        namePlateImg.paste(nameDxImg, (230, 4), mask=nameDxImg.split()[3])
        self.img.paste(namePlateImg, (240 if not self.qqId else 139, 52), mask=namePlateImg.split()[3])

        shougouImg = Image.open(os.path.join(self.pic_dir, 'UI_CMN_Shougou_Rainbow.png')).convert('RGBA')
        shougouDraw = ImageDraw.Draw(shougouImg)
        font2 = ImageFont.truetype('src/static/HOS.ttf', 14, encoding='utf-8')
        font2s = ImageFont.truetype('src/static/HOS.ttf', 26, encoding='utf-8')
        font3 = ImageFont.truetype('src/static/HOS_Med.ttf', 48, encoding='utf-8')
        font4 = ImageFont.truetype('src/static/HOS_Med.ttf', 14, encoding='utf-8')
        if self.platetitle == 0:
            playCountInfo = f'段位: {self.rankRating} | 底分: {self.musicRating}' if not self.b50 else f'Best 50 底分模式'
        else:
            playCountInfo = f'{self.platetitle}'
        shougouImgW, shougouImgH = shougouImg.size
        playCountInfoW, playCountInfoH = shougouDraw.textsize(playCountInfo, font2)
        textPos = ((shougouImgW - playCountInfoW - font2.getoffset(playCountInfo)[0]) / 2, 5)
        shougouDraw.text(textPos, playCountInfo, (104, 186, 255), font2)
        shougouImg = self._resizePic(shougouImg, 1.05)
        self.img.paste(shougouImg, (240 if not self.qqId else 139, 95), mask=shougouImg.split()[3])
        
        splashImg = Image.open(os.path.join(self.pic_dir, 'Splash.png')).convert('RGBA')
        splashImg = self._resizePic(splashImg, 0.2)
        self.img.paste(splashImg, (685, 2), mask=splashImg.split()[3])

        ratingImg = Image.open(os.path.join(self.pic_dir, 'Rating.png')).convert('RGBA')
        ratingDraw = ImageDraw.Draw(ratingImg)
        font = ImageFont.truetype('src/static/Poppins.otf', 68, encoding='utf-8')
        try:
            ratingDraw.text((146, 25), f'{self.sdBest[0].ra if not self.b50 else computeRa(self.sdBest[0].ds, self.sdBest[0].achievement, True)}','white', font)
            ratingDraw.text((424, 25), f'{self.sdBest[int(len(self.sdBest)-1)].ra if not self.b50 else computeRa(self.sdBest[int(len(self.sdBest))-1].ds, self.sdBest[int(len(self.sdBest))-1].achievement, True)}', 'white', font)
            ratingDraw.text((695, 25), f'{self.dxBest[0].ra if not self.b50 else computeRa(self.dxBest[0].ds, self.dxBest[0].achievement, True)}', 'black', font)
            ratingDraw.text((972, 25), f'{self.dxBest[int(len(self.dxBest)-1)].ra if not self.b50 else computeRa(self.dxBest[int(len(self.dxBest))-1].ds, self.dxBest[int(len(self.dxBest))-1].achievement, True)}', 'black', font)
        except:
            errorImg = Image.open(os.path.join(self.pic_dir, f'Attention.png')).convert('RGBA')
            ratingImg.paste(errorImg, (0, 0), mask=errorImg.split()[3])
        self.img.paste(ratingImg, (6, 1360 if not self.b50 else 1660), mask=ratingImg.split()[3])

        self._drawBestList(self.img, self.sdBest, self.dxBest)
        total_sd = 0
        total_dx = 0
        for i in range(len(self.sdBest)):
            total_sd += self.sdBest[i].ra if not self.b50 else computeRa(self.sdBest[i].ds, self.sdBest[i].achievement, True)
        for i in range(len(self.dxBest)):
            total_dx += self.dxBest[i].ra if not self.b50 else computeRa(self.dxBest[i].ds, self.dxBest[i].achievement, True)
        authorBoardImg = Image.open(os.path.join(self.pic_dir, 'UI_CMN_MiniDialog_01.png')).convert('RGBA')
        authorBoardDraw = ImageDraw.Draw(authorBoardImg)
        authorBoardDraw.text((82 if not self.b50 else 75, 144), f'{total_sd}', 'black', font3)
        authorBoardDraw.text((320 if not self.b50 else 313, 144), f'{total_dx}', 'black', font3)
        authorBoardImg = self._resizePic(authorBoardImg, 0.45)
        self.img.paste(authorBoardImg, (1070, 10), mask=authorBoardImg.split()[3])
        dxImg = Image.open(os.path.join(self.pic_dir, 'UI_RSL_MBase_Parts_01.png')).convert('RGBA')
        dxImg = self._resizePic(dxImg, 0.5)
        self.img.paste(dxImg, (8, 1187 if self.b50 else 890), mask=dxImg.split()[3])

        # self.img.show()

    def getDir(self):
        return self.img


def computeRa(ds: float, achievement: float, spp: bool = False) -> int:
    baseRa = 22.4 if spp else 14.0
    if achievement < 50:
        baseRa = 0.0 if spp else 0.0
    elif achievement < 60:
        baseRa = 8.0 if spp else 5.0
    elif achievement < 70:
        baseRa = 9.6 if spp else 6.0
    elif achievement < 75:
        baseRa = 11.2 if spp else 7.0
    elif achievement < 80:
        baseRa = 12.0 if spp else 7.5
    elif achievement < 90:
        baseRa = 13.6 if spp else 8.5
    elif achievement < 94:
        baseRa = 15.2 if spp else 9.5
    elif achievement < 97:
        baseRa = 16.8 if spp else 10.5
    elif achievement < 98:
        baseRa = 20.0 if spp else 12.5
    elif achievement < 99:
        baseRa = 20.3 if spp else 12.7
    elif achievement < 99.5:
        baseRa = 20.8 if spp else 13.0
    elif achievement < 99.9999:
        baseRa = 21.1 if spp else 13.2
    elif achievement < 100:
        baseRa = 21.4 if spp else 13.2
    elif achievement < 100.4999:
        baseRa = 21.6 if spp else 13.5
    elif achievement < 100.5:
        baseRa = 22.2 if spp else 13.5

    return math.floor(ds * (min(100.5, achievement) / 100) * baseRa)


async def get_player_data(payload: Dict):
    conn = aiohttp.TCPConnector(verify_ssl=False)
    async with aiohttp.request("POST", "https://www.diving-fish.com/api/maimaidxprober/query/player", connector=conn, json=payload) as resp:
        if resp.status == 400:
            return None, 400
        elif resp.status == 403:
            return None, 403
        player_data = await resp.json()
        #out_file = open("log.json", "w")
        #json.dump(player_data, out_file)
        return player_data, 0


async def generate(payload: Dict, platenum: int or str, platetitle: int or str) -> Tuple[Optional[Image.Image], bool]:
    obj, success = await get_player_data(payload)
    if success != 0: return None, success
    qqId = None
    b50 = False
    if 'qq' in payload:
        qqId = payload['qq']
    if 'b50' in payload:
        b50 = True
        sd_best = BestList(35)
    else:
        sd_best = BestList(25)
    dx_best = BestList(15)

    dx: List[Dict] = obj["charts"]["dx"]
    sd: List[Dict] = obj["charts"]["sd"]
    for c in sd:
        sd_best.push(ChartInfo.from_json(c))
    for c in dx:
        dx_best.push(ChartInfo.from_json(c))
    pic = DrawBest(sd_best, dx_best, obj["nickname"], obj["rating"] + obj["additional_rating"], obj["rating"], qqId, b50, platenum, platetitle).getDir()
    return pic, 0
