from .core import *
from .core import TextualLoggerManager

# 显式导出set_layout函数，使其可以直接导入
set_layout = TextualLoggerManager.set_layout