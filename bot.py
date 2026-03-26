#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path

import nonebot
from nonebot.adapters.onebot.v11 import Adapter

# Custom your logger
# 
# from nonebot.log import logger, default_format
# logger.add("error.log",
#            rotation="00:00",
#            diagnose=False,
#            level="ERROR",
#            format=default_format)

BASE_DIR = Path(__file__).resolve().parent
PLUGIN_LIST_FILE = BASE_DIR / "plugin-list.json"
PLUGIN_DIR = BASE_DIR / "src" / "plugins"

# You can pass some keyword args config to init function
nonebot.init(_env_file=BASE_DIR / ".env")
# nonebot.load_builtin_plugins()
app = nonebot.get_asgi()

driver = nonebot.get_driver()
driver.register_adapter(Adapter)
driver.config.help_text = {}


if PLUGIN_LIST_FILE.exists():
    nonebot.load_from_json(str(PLUGIN_LIST_FILE), encoding="utf-8")
else:
    nonebot.load_plugins(str(PLUGIN_DIR))

# Modify some config / config depends on loaded configs
# 
# config = driver.config
# do something...


if __name__ == "__main__":
    nonebot.run()
