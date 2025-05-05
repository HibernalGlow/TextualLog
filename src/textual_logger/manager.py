"""
管理器模块，提供TextualLoggerManager类和管理功能
"""

import logging
import threading
import time
import asyncio
import os
import sys
import json
import tempfile
import subprocess
from typing import Dict, Optional, Any

# 导入应用和处理器
from .app import TextualLogger
from .handler import TextualLogHandler

class TextualLoggerManager:
    """Textual日志管理器，支持动态面板和日志劫持"""
    
    _instance = None
    _app = None
    _default_layout = {
        "current_stats": {"ratio": 2, "title": "📊 总体进度", "style": "yellow"},
        "current_progress": {"ratio": 2, "title": "🔄 当前进度", "style": "cyan"},
        "performance": {"ratio": 2, "title": "⚡ 性能配置", "style": "green"},
        "process": {"ratio": 3, "title": "📝 处理日志", "style": "magenta"},
        "update": {"ratio": 2, "title": "ℹ️ 更新日志", "style": "blue"}
    }
        
    @classmethod
    def set_layout(cls, layout_config=None, log_file=None, newtab=False):
        """设置日志布局并启动应用
        
        Args:
            layout_config: 布局配置字典，格式如下：
            {
                "panel_name": {
                    "ratio": int,  # 面板比例
                    "title": str,  # 面板标题
                    "style": str   # 面板样式
                }
            }
            log_file: str, 可选，日志文件路径，如果提供则从文件读取日志
            newtab: bool, 可选，是否在 Windows Terminal 中开启新标签页，默认为 False
        """
        # 使用默认布局或自定义布局
        final_layout = layout_config or cls._default_layout
        
        # 检查是否启用新标签页功能
        if newtab and log_file:
            if sys.platform == 'win32':
                try:
                    # 将布局配置保存为临时文件
                    # 创建临时配置文件
                    temp_dir = tempfile.gettempdir()
                    config_file = os.path.join(temp_dir, f"textual_logger_config_{int(time.time())}.json")
                    with open(config_file, 'w', encoding='utf-8') as f:
                        json.dump(final_layout, f)
                        
                    # 获取模块路径
                    import textual_logger
                    module_path = os.path.dirname(os.path.abspath(textual_logger.__file__))
                    current_script = os.path.join(module_path, "__main__.py")
                        
                    # 获取当前 Python 解释器路径
                    python_executable = sys.executable
                    
                    # 构建命令行
                    cmd = f'wt new-tab -p "Windows PowerShell" "{python_executable}" "{current_script}" --config "{config_file}" --log-file "{log_file}"'
                    
                    # 执行命令
                    subprocess.Popen(cmd, shell=True)
                    
                    # 返回空应用实例，不影响调用方代码
                    return None
                except Exception as e:
                    print(f"启动新标签页失败: {e}")
                    # 失败时回退到常规模式
            else:
                print("新标签页模式仅在Windows平台可用")
        
        # 创建应用实例
        if cls._app is None:
            cls._app = TextualLogger(final_layout)
            
            # 配置根日志记录器
            root_logger = logging.getLogger()
            root_logger.setLevel(logging.DEBUG)  # 改为使用调用方的日志级别

            # 仅移除Textual自己的处理器（如果存在）
            for handler in root_logger.handlers[:]:
                if isinstance(handler, TextualLogHandler):
                    root_logger.removeHandler(handler)

            # 添加Textual处理器（保留调用方已有的处理器）
            textual_handler = TextualLogHandler(cls._app, log_file)
            textual_handler.setFormatter(logging.Formatter('%(message)s'))
            textual_handler.setLevel(logging.INFO)  # 设置适当级别
            root_logger.addHandler(textual_handler)
            
            # 注册处理器
            cls._app.register_handler(textual_handler)
            
            # 异步运行应用
            async def run_app():
                await cls._app.run_async()
            
            # 在新线程中运行应用
            app_thread = threading.Thread(target=lambda: asyncio.run(run_app()))
            app_thread.daemon = True
            app_thread.start()
            
            # 等待应用初始化完成
            time.sleep(0.5)
            
        return cls._app

    @classmethod
    def close(cls):
        """关闭日志管理器，清理资源"""
        if cls._app is not None:
            # 移除所有日志处理器
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                if isinstance(handler, TextualLogHandler):
                    # 停止文件检查定时器
                    if hasattr(handler, '_file_check_timer') and handler._file_check_timer:
                        try:
                            handler._file_check_timer.stop()
                            handler._file_check_timer = None
                        except Exception:
                            pass
                    root_logger.removeHandler(handler)
            
            # 退出应用
            try:
                if hasattr(cls._app, "_running") and cls._app._running:
                    # 仅在应用运行时才尝试调用退出
                    asyncio.run_coroutine_threadsafe(cls._app.action_quit(), asyncio.get_event_loop())
            except Exception:
                pass
                
            # 清空引用
            cls._app = None