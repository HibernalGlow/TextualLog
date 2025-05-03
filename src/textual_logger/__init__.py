from .core import *
from .core import TextualLoggerManager

# 显式导出set_layout函数，使其可以直接导入
set_layout = TextualLoggerManager.set_layout

# 添加命令行入口点
def main():
    """命令行入口点，用于监控日志文件或启动演示模式"""
    import argparse
    import os
    import json
    import asyncio
    import time

    parser = argparse.ArgumentParser(description="Textual日志查看器")
    parser.add_argument("--config", help="布局配置文件路径")
    parser.add_argument("--log-file", help="要监控的日志文件路径")
    args = parser.parse_args()
    
    layout_config = None
    
    # 从配置文件加载布局配置
    if args.config and os.path.exists(args.config):
        try:
            with open(args.config, 'r', encoding='utf-8') as f:
                layout_config = json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            layout_config = None
    
    # 如果指定了日志文件，直接启动监控
    if args.log_file:
        # 如果没有布局配置，使用默认的简单布局
        if not layout_config:
            layout_config = {
                "current_stats": {"ratio": 2, "title": "📊 总体进度", "style": "yellow"},
                "current_progress": {"ratio": 2, "title": "🔄 当前进度", "style": "cyan"},
                "process": {"ratio": 4, "title": "📝 处理日志", "style": "magenta"},
                "update": {"ratio": 2, "title": "ℹ️ 更新日志", "style": "blue"}
            }
        
        # 启动监控
        app = TextualLoggerManager.set_layout(layout_config, log_file=args.log_file)
        
        # 直接启动应用（不在后台线程运行）
        if app:
            asyncio.run(app.run_async())
    else:
        print("使用方法: textual_logger --log-file 日志文件路径 [--config 配置文件路径]")
        print("未指定日志文件，请使用 --log-file 参数")
        print("例如: textual_logger --log-file app.log")