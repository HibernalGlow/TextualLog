"""
TextualLog - 基于 Textual 的终端日志可视化工具

提供了在终端中创建多面板日志显示界面的功能，
支持日志文件监控、实时进度条显示和系统状态监控。
"""

# 从各个模块导入核心组件
from .models import CPUInfo, DiskIOInfo, SystemStatus
from .widgets import LogPanel, SystemStatusFooter
from .handler import TextualLogHandler
from .app import TextualLogger
from .manager import TextualLoggerManager
from .__main__ import main

# 导出常用函数，方便用户直接从包导入使用
set_layout = TextualLoggerManager.set_layout
close = TextualLoggerManager.close

# 定义版本号
__version__ = "0.1.0"

# 定义__all__，显式列出可以从模块导入的名称
__all__ = [
    "TextualLoggerManager",
    "TextualLogger", 
    "TextualLogHandler",
    "LogPanel", 
    "SystemStatusFooter",
    "CPUInfo", 
    "DiskIOInfo", 
    "SystemStatus",
    "set_layout", 
    "close",
    "main"
]

# 添加命令行入口点
