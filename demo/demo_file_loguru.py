from loguru import logger
import os
import sys
from pathlib import Path
from datetime import datetime
import time
import random

# 添加父级目录到sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入TextualLog相关模块
from src.textual_logger import TextualLoggerManager

def setup_logger(app_name="app", project_root=None, console_output=True):
    """配置 Loguru 日志系统
    
    Args:
        app_name: 应用名称，用于日志目录
        project_root: 项目根目录，默认为当前文件所在目录
        console_output: 是否输出到控制台，默认为True
        
    Returns:
        tuple: (logger, config_info)
            - logger: 配置好的 logger 实例
            - config_info: 包含日志配置信息的字典
    """
    # 获取项目根目录
    if project_root is None:
        project_root = Path(__file__).parent.resolve()
    
    # 清除默认处理器
    logger.remove()
    
    # 有条件地添加控制台处理器（简洁版格式）
    if console_output:
        logger.add(
            sys.stdout,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <blue>{elapsed}</blue> | <level>{level.icon} {level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
        )
    
    # 使用 datetime 构建日志路径
    current_time = datetime.now()
    date_str = current_time.strftime("%Y-%m-%d")
    hour_str = current_time.strftime("%H")
    minute_str = current_time.strftime("%M%S")
    
    # 构建日志目录和文件路径
    log_dir = os.path.join(project_root, "logs", app_name, date_str, hour_str)
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{minute_str}.log")
    
    # 添加文件处理器
    logger.add(
        log_file,
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {elapsed} | {level.icon} {level: <8} | {name}:{function}:{line} - {message}",
    )
    
    # 创建配置信息字典
    config_info = {
        'log_file': log_file,
    }
    
    logger.info(f"日志系统已初始化，应用名称: {app_name}")
    return logger, config_info

def simulate_file_conversion(total_files=20):
    """模拟文件转换过程，生成各种类型的日志"""
    logger.info("[#stats]开始处理文件转换任务")
    
    # 模拟总体进度
    for i in range(1, total_files + 1):
        # 模拟进度信息
        progress_percent = (i / total_files) * 100
        logger.info(f"[@progress]处理进度: [{i}/{total_files}] {progress_percent:.1f}%")
        
        # 模拟文件处理
        file_size = random.randint(100, 500)
        compressed_size = int(file_size * random.uniform(0.2, 0.8))
        saved_size = file_size - compressed_size
        save_ratio = (saved_size / file_size) * 100
        
        file_path = f"E:\\模拟路径\\测试文件夹\\file_{i:04d}.jpg"
        output_path = f"E:\\模拟路径\\测试文件夹\\file_{i:04d}.jxl"
        
        # 随机模拟一些文件删除消息
        if random.random() > 0.7:
            logger.info(f"[#image]已删除原始文件: {file_path}")
        
        # 模拟转换结果信息
        logger.info(f"[#image]转换成功: {output_path}, {file_size}KB -> {compressed_size}KB, 节省: {saved_size}KB, 压缩率: {save_ratio:.1f}%")
        
        # 随机模拟一些警告或错误
        if random.random() > 0.9:
            logger.warning(f"[#warning]文件处理警告: {file_path} 图像质量较低")
        elif random.random() > 0.95:
            logger.error(f"[#error]处理失败: {file_path} 无法读取元数据")
        
        # 模拟处理延迟
        time.sleep(random.uniform(0.3, 1.0))
    
    # 完成信息
    logger.success("[#stats]所有文件处理完成！总共处理: {total_files}个文件")

def main():
    """主函数，演示TextualLog与loguru集成"""
    # 设置loguru
    logger, config = setup_logger(app_name="DEMO", console_output=False)
    
    # 设置TextualLog布局
    TEXTUAL_LAYOUT = {
        "stats": {
            "ratio": 1,
            "title": "📊 总体统计",
            "style": "lightyellow"
        },
        "progress": {
            "ratio": 1,
            "title": "🔄 处理进度",
            "style": "lightcyan"
        },
        "image": {
            "ratio": 3,
            "title": "🖼️ 图像处理",
            "style": "lightgreen"
        },
        "warning": {
            "ratio": 2,
            "title": "⚠️ 警告信息",
            "style": "yellow"
        },
        "error": {
            "ratio": 2,
            "title": "❌ 错误信息",
            "style": "red"
        }
    }
    
    # 初始化TextualLog，使用loguru的日志文件
    TextualLoggerManager.set_layout(TEXTUAL_LAYOUT, log_file=config['log_file'])
    
    # 打印一些起始信息
    logger.info("[#stats]启动loguru与TextualLog集成演示")
    time.sleep(1)
    
    # 模拟文件处理
    simulate_file_conversion()
    
    # 保持程序运行一段时间以便查看结果
    logger.info("[#stats]演示完成，程序将在10秒后退出")
    time.sleep(10)

if __name__ == "__main__":
    main()
