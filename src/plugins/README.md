# Local Plugins

This directory is reserved for local NoneBot2 plugins.

You can continue extending this project by adding:

- a package plugin: `src/plugins/<plugin_name>/__init__.py`
- a single-file plugin: `src/plugins/<plugin_name>.py`

`bot.py` will keep loading this directory as the local plugin root, so new
plugins can be added without changing the embedded `maimaidx` plugin.
