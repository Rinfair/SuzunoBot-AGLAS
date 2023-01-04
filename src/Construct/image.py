from src.libraries.image import *
from src.libraries.gosen_choyen import generate
from nonebot import on_command, on_message, on_notice, on_regex
from nonebot.typing import T_State
from nonebot.adapters import Event, Bot
from nonebot.adapters.cqhttp import Message

from src.libraries.img_template import img_template_parser, edit_base_img

high_eq = on_regex(r'低情商.+高情商.+')


@high_eq.handle()
async def _(bot: Bot, event: Event, state: T_State):
    regex = '低情商(.+)高情商(.+)'
    groups = re.match(regex, str(message)).groups()
    left = groups[0].strip()
    right = groups[1].strip()
    nickname = event.sender.nickname
    if len(left) > 15 or len(right) > 15:
        await high_eq.send(f"▿ [Sender: {nickname}]\n  AGLAS Image Creator - 文字过多\n为了图片质量，请不要多于15个字符嗷。")
        return
    await jlpx.send(f"▾ [Sender: {nickname}]\n  AGLAS Image Creator - 高低情商\n正在生成，请耐心等待。如 5 分钟内没有输出图像，可能是被吞了，届时请再试一次。")
    img_p = Image.open(path)
    draw_text(img_p, left, 0)
    draw_text(img_p, right, 400)
    await high_eq.send(Message([{
        "type": "image",
        "data": {
            "file": f"base64://{str(image_to_base64(img_p), encoding='utf-8')}"
        }
    }]))


jlpx = on_command('金龙盘旋')


@jlpx.handle()
async def _(bot: Bot, event: Event, state: T_State):
    argv = str(message).strip().split(' ')
    nickname = event.sender.nickname
    if len(argv) != 3:
        await jlpx.send(f"▿ [Sender: {nickname}]\n  AGLAS Image Creator - 参数不足\n金龙盘旋需要三个参数！")
        return
    await jlpx.send(f"▾ [Sender: {nickname}]\n  AGLAS Image Creator - 金龙盘旋\n正在生成，请耐心等待。如 5 分钟内没有输出图像，可能是被吞了，届时请再试一次。")
    url = await get_jlpx(argv[0], argv[1], argv[2])
    if url == -1:
        await jlpx.send("当前金龙盘旋生成的服务器Request无返回，请稍后重试。")
        return
    await jlpx.send(Message([{
        "type": "image",
        "data": {
            "file": f"{url}"
        }
    }]))


gocho = on_command('gocho')


@gocho.handle()
async def _(bot: Bot, event: Event, state: T_State):
    argv = str(message).strip().split(' ')
    nickname = event.sender.nickname
    if len(argv) != 2:
        await gocho.send(f"▿ [Sender: {nickname}]\n  AGLAS Image Creator - 参数不足\nGocho 需要两个参数！")
        return
    await gocho.send(f"▾ [Sender: {nickname}]\n  AGLAS Image Creator - Gocho\n正在生成，请耐心等待。如 5 分钟内没有输出图像，可能是被吞了，届时请再试一次。")
    i = generate(argv[0], argv[1])
    await gocho.send(Message([{
        "type": "image",
        "data": {
            "file": f"base64://{str(image_to_base64(i), encoding='utf-8')}"
        }
    }]))


img_template = on_command("img_template", aliases={"imgt"})


@img_template.handle()
async def _(bot: Bot, event: Event):
    arg = message
    nickname = event.sender.nickname
    try:
        base, img = await img_template_parser(arg)
        b64 = await edit_base_img(base, img)
        await img_template.send(Message([{
            "type": "image",
            "data": {
                "file": f"base64://{str(b64, encoding='utf-8')}"
            }
        }]))
    except Exception as e:
        await img_template.send(f"▿ [Sender: {nickname}]\n  AGLAS Image Templator - Exception\n[Exception Occurred]\n{str(e)}")
