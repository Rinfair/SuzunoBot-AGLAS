from nonebot import get_plugin_config
from pydantic import BaseModel


class Config(BaseModel):
    batarot_forward_mode: bool = False
    """True 时牌阵占卜改为逐条发送，False 时群聊优先使用合并转发。"""


config = get_plugin_config(Config)
