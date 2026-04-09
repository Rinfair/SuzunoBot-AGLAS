from __future__ import annotations

import random
from typing import Protocol

from nonebot.adapters.onebot.v11 import Message, MessageSegment

from .utils import find_card_key, load_fortune_descriptions, load_image_base64, load_spread_data, load_tarot_data


class RandomLike(Protocol):
    def choice(self, seq): ...

    def randint(self, a: int, b: int) -> int: ...

    def random(self) -> float: ...

    def sample(self, population, k: int): ...


def _make_text_image_message(text: str, image_name: str | None, *, rotate_180: bool = False) -> Message:
    message = Message(MessageSegment.text(text))
    if not image_name:
        return message

    image = load_image_base64(image_name, rotate_180=rotate_180)
    if image is None:
        message.append(MessageSegment.text("图片加载失败\n"))
        return message

    message.append(MessageSegment.image(image))
    return message


def build_tarot_reply(rng: RandomLike | None = None) -> Message:
    rng = rng or random
    cards, tarot_urls = load_tarot_data()
    card_key = rng.choice(list(cards.keys()))
    card = cards[card_key]

    is_upright = bool(rng.choice([True, False]))
    direction = "up" if is_upright else "down"
    card_name = card["name_cn"]
    card_meaning = card["meaning"][direction]
    image_name = tarot_urls.get(f"tarot_{card_key}")
    position = "正位" if is_upright else "逆位"

    return _make_text_image_message(
        f"塔罗牌名称：{card_name}\n牌位：{position}\n含义：{card_meaning}\n",
        image_name,
        rotate_180=not is_upright,
    )


def build_spread_reply(rng: RandomLike | None = None) -> tuple[str, list[Message]]:
    rng = rng or random
    spread_data = load_spread_data()["formations"]
    cards, tarot_urls = load_tarot_data()

    spread_name = rng.choice(list(spread_data.keys()))
    spread_info = spread_data[spread_name]
    cards_num = spread_info["cards_num"]
    position_templates = spread_info.get("representations", [])
    positions = list(rng.choice(position_templates)) if position_templates else []
    if len(positions) < cards_num:
        positions.extend([f"牌位{i + 1}" for i in range(len(positions), cards_num)])

    selected_cards = rng.sample(list(cards.keys()), cards_num)
    messages = [Message(MessageSegment.text(f"老师，你抽到的牌阵是：{spread_name}\n"))]

    for index, card_key in enumerate(selected_cards):
        card = cards[card_key]
        is_upright = rng.random() < 0.5
        direction = "up" if is_upright else "down"
        position = "正位" if is_upright else "逆位"
        card_name = card["name_cn"]
        card_meaning = card["meaning"][direction]
        image_name = tarot_urls.get(f"tarot_{card_key}")
        label = positions[index] if index < len(positions) else f"牌位{index + 1}"

        messages.append(
            _make_text_image_message(
                f"{label}：{card_name}（{position}）\n解释：{card_meaning}\n",
                image_name,
                rotate_180=not is_upright,
            )
        )

    return spread_name, messages


def build_fortune_reply(rng: RandomLike | None = None) -> Message:
    rng = rng or random
    cards, tarot_urls = load_tarot_data()
    card_key = rng.choice(list(cards.keys()))
    card = cards[card_key]
    fortune_score = rng.randint(1, 100)
    score_floor = (fortune_score - 1) // 10 * 10 + 1
    score_range = f"{score_floor}-{score_floor + 9}"
    fortune_description = rng.choice(load_fortune_descriptions()[score_range])
    image_name = tarot_urls.get(f"tarot_{card_key}")

    return _make_text_image_message(
        (
            f"今日塔罗牌：{card['name_cn']}\n"
            f"今日运势指数：{fortune_score}\n"
            f"运势解读：{fortune_description}\n"
        ),
        image_name,
    )


def build_reading_reply(query: str, rng: RandomLike | None = None) -> Message:
    rng = rng or random
    cards, tarot_urls = load_tarot_data()
    card_key = find_card_key(cards, query) if query else rng.choice(list(cards.keys()))
    if card_key is None:
        return Message(MessageSegment.text("未找到指定的塔罗牌，请输入正确的卡牌编号或中文名称。\n"))

    card = cards[card_key]
    image_name = tarot_urls.get(f"tarot_{card_key}")
    description = "\n".join(card["description"])
    return _make_text_image_message(
        f"塔罗牌名称：{card['name_cn']}\n原作者解读：\n{description}\n",
        image_name,
    )
