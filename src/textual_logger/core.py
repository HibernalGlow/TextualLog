"""
核心模块，作为兼容层导入其他模块中的类和函数
保持向后兼容性，让旧代码继续正常工作
"""

# 导入所有拆分后的模块和类
from .models import CPUInfo, DiskIOInfo, SystemStatus
from .widgets import LogPanel, SystemStatusFooter
from .handler import TextualLogHandler
from .app import TextualLogger
from .manager import TextualLoggerManager
from .__main__ import main

# 导出函数，方便使用
set_layout = TextualLoggerManager.set_layout
close = TextualLoggerManager.close

# 以下是核心模块中需要保留的内容，如果有的话
# 目前所有功能都已移至其他模块，此处为空

# 如果这个文件作为脚本直接运行，调用main函数
if __name__ == "__main__":
    main()