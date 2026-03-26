from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple, Union

from PIL import Image, ImageDraw, ImageFont, ImageOps

from ..score import PlayerMaiScore
from ._config import ACCENT_COLOR, FONT_MAIN, PIC_DIR, SUBTEXT_COLOR


def get_char_width(o: int) -> int:
    """
    获取字符宽度

    :param o: 字符的 Unicode 编码
    :return: 字符宽度 (0, 1, 2)
    """
    widths = [
        (126, 1),
        (159, 0),
        (687, 1),
        (710, 0),
        (711, 1),
        (727, 0),
        (733, 1),
        (879, 0),
        (1154, 1),
        (1161, 0),
        (4347, 1),
        (4447, 2),
        (7467, 1),
        (7521, 0),
        (8369, 1),
        (8426, 0),
        (9000, 1),
        (9002, 2),
        (11021, 1),
        (12350, 2),
        (12351, 1),
        (12438, 2),
        (12442, 0),
        (19893, 2),
        (19967, 1),
        (55203, 2),
        (63743, 1),
        (64106, 2),
        (65039, 1),
        (65059, 0),
        (65131, 2),
        (65279, 1),
        (65376, 2),
        (65500, 1),
        (65510, 2),
        (120831, 1),
        (262141, 2),
        (1114109, 1),
    ]
    if o == 0xE or o == 0xF:
        return 0
    for num, wid in widths:
        if o <= num:
            return wid
    return 1


def coloum_width(s: str) -> int:
    """
    计算字符串的总宽度

    :param s: 输入字符串
    :return: 总宽度
    """
    res = 0
    for ch in s:
        res += get_char_width(ord(ch))
    return res


def change_column_width(s: str, length: int) -> str:
    """
    截断字符串以适应指定宽度

    :param s: 输入字符串
    :param length: 目标宽度
    :return: 截断后的字符串
    """
    res = 0
    s_list = []
    for ch in s:
        res += get_char_width(ord(ch))
        if res <= length:
            s_list.append(ch)
    return "".join(s_list)


def dx_score(dx: int) -> int:
    """
    根据 DX 分数百分比计算星级

    :param dx: DX 分数百分比
    :return: 星级 (0-5)
    """
    if dx <= 85:
        return 0
    elif dx <= 90:
        return 1
    elif dx <= 93:
        return 2
    elif dx <= 95:
        return 3
    elif dx <= 97:
        return 4
    else:
        return 5


def image_to_bytes(img: Image.Image, format="PNG") -> bytes:
    """
    将 PIL Image 对象转换为字节流

    :param img: PIL Image 对象
    :param format: 图片格式，默认为 PNG
    :return: 图片字节流
    """
    output_buffer = BytesIO()
    img.save(output_buffer, format)
    return output_buffer.getvalue()


def rounded_corners(
    image: Image.Image, radius: int, corners: Tuple[bool, bool, bool, bool] = (False, False, False, False)
) -> Image.Image:
    """
    为图片添加圆角

    :param image: 输入图片
    :param radius: 圆角半径
    :param corners: 四个角是否应用圆角 (左上, 右上, 右下, 左下)
    :return: 处理后的图片
    """
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, image.size[0], image.size[1]), radius, fill=255, corners=corners)
    new_im = ImageOps.fit(image, mask.size)
    new_im.putalpha(mask)
    return new_im


def find_all_clear_rank(scores: list[PlayerMaiScore]) -> Optional[Image.Image]:
    """
    获取最小达成率并返回其对应的 rank 图
    """
    if len(scores) < 50:
        return None

    min_ach = scores[0].achievements
    for score in scores[1:]:
        if score.achievements < min_ach:
            min_ach = score.achievements

    if min_ach < 97:
        return None
    elif min_ach < 98:
        label, color = "ALL CLEAR S", (129, 179, 77, 255)
    elif min_ach < 99:
        label, color = "ALL CLEAR S+", (90, 196, 160, 255)
    elif min_ach < 99.5:
        label, color = "ALL CLEAR SS", (82, 156, 255, 255)
    elif min_ach < 100:
        label, color = "ALL CLEAR SS+", (102, 128, 255, 255)
    elif min_ach < 100.5:
        label, color = "ALL CLEAR SSS", (161, 110, 255, 255)
    else:
        label, color = "ALL CLEAR SSS+", (235, 121, 187, 255)

    image = Image.new("RGBA", (220, 62), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, 219, 61), radius=20, fill=(255, 255, 255, 232), outline=color, width=4)
    DrawText(draw, FONT_MAIN).draw(110, 31, 22, label, color, "mm")
    return image


class DrawText:
    """
    文本绘制辅助类
    """

    def __init__(self, image: ImageDraw.ImageDraw, font: Path) -> None:
        """
        初始化 DrawText

        :param image: ImageDraw 对象
        :param font: 字体文件路径
        """
        self._img = image
        self._font = str(font)

    def draw(
        self,
        pos_x: int,
        pos_y: int,
        size: int,
        text: Union[str, int, float],
        color: Tuple[int, int, int, int] = (255, 255, 255, 255),
        anchor: str = "lt",
        stroke_width: int = 0,
        stroke_fill: Tuple[int, int, int, int] = (0, 0, 0, 0),
        multiline: bool = False,
    ) -> None:
        """
        绘制文本

        :param pos_x: X 坐标
        :param pos_y: Y 坐标
        :param size: 字体大小
        :param text: 文本内容
        :param color: 文本颜色 (RGBA)
        :param anchor: 锚点位置
        :param stroke_width: 描边宽度
        :param stroke_fill: 描边颜色 (RGBA)
        :param multiline: 是否多行文本
        """
        try:
            font = ImageFont.truetype(self._font, size)
        except OSError:
            font = ImageFont.load_default()
        if multiline:
            self._img.multiline_text(
                (pos_x, pos_y), str(text), color, font, anchor, stroke_width=stroke_width, stroke_fill=stroke_fill
            )
        else:
            self._img.text(
                (pos_x, pos_y), str(text), color, font, anchor, stroke_width=stroke_width, stroke_fill=stroke_fill
            )
