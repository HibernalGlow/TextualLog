"""
使用说明:
1. 导入和初始化:
   ```python
   from nodes.tui.textual_logger import TextualLoggerManager
   注意插入时机，不要干扰输入
   # 定义布局配置 颜色强烈建议使用淡色系light
   TEXTUAL_LAYOUT = {
       "current_stats": {  # 面板名称，用于日志定位
           "ratio": 2,     # 面板高度比例
           "title": "📊 总体进度",  # 面板标题
           "style": "lightyellow"  # 面板样式颜色
       },
       "current_progress": {
           "ratio": 2,
           "title": "🔄 当前进度",
           "style": "lightcyan"
       },
       # ... 更多面板
   }
   
   # 初始化布局
   TextualLoggerManager.set_layout(TEXTUAL_LAYOUT)
   ```

2. 日志输出格式:
   - 普通日志: logging.info("消息内容")
   - 定向面板: logging.info("[#面板名]消息内容")
尽可能在一行输出完所有信息

3. 常用面板设置:
   - current_stats: 总体统计信息
   - current_progress: 当前处理进度
   - process_log: 处理过程日志
   - update_log: 更新状态日志

4. 样式颜色选项:
   - 基础色系:
     * yellow: 黄色
     * cyan: 青色
     * magenta: 品红
     * blue: 蓝色
     * green: 绿色
     * red: 红色
   - 浅色系扩展:
     * lightblue: 浅蓝
     * lightgreen: 浅绿
     * lightcyan: 浅青
     * lightmagenta: 浅品红
     * lightyellow: 浅黄
   - 灰色系:
     * white: 白
     * light_gray: 浅灰
     * dark_gray: 深灰
   - 自定义颜色: 可以直接使用CSS颜色名称或十六进制值，如 "#a8c8ff"

5. 新标签页显示（仅 Windows）:
   - 使用 newtab=True 参数可以在 Windows Terminal 中打开新标签页显示 TUI 界面
   - 与 log_file 参数结合使用时，会创建一个独立的日志监控界面，不需要运行原始脚本
   - 示例: TextualLoggerManager.set_layout(TEXTUAL_LAYOUT, log_file="logs/app.log", newtab=True)
   - 注意: 这需要系统安装了 Windows Terminal，并且 wt 命令可用
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Label, Footer, TabbedContent, TabPane, Collapsible, Header
from textual.reactive import reactive
from textual import log, work
from typing import Dict, Optional, List
import threading
import time
from datetime import datetime
import logging
import asyncio
import os
import sys
import signal
import psutil
import re
from dataclasses import dataclass, field
import argparse

@dataclass
class CPUInfo:
    usage: float = 0.0  # 仅保留CPU使用率

@dataclass
class DiskIOInfo:
    read_speed: float = 0.0  # 读取速度 (MB/s)
    write_speed: float = 0.0  # 写入速度 (MB/s)
    read_bytes: int = 0  # 总读取字节数
    write_bytes: int = 0  # 总写入字节数

@dataclass
class SystemStatus:
    cpu: CPUInfo = field(default_factory=CPUInfo)
    memory_usage: float = 0.0
    disk_io: DiskIOInfo = field(default_factory=DiskIOInfo)
    last_update: datetime = field(default_factory=datetime.now)

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
                    import json
                    import tempfile
                    
                    # 创建临时配置文件
                    temp_dir = tempfile.gettempdir()
                    config_file = os.path.join(temp_dir, f"textual_logger_config_{int(time.time())}.json")
                    with open(config_file, 'w', encoding='utf-8') as f:
                        json.dump(final_layout, f)
                        
                    # 获取当前脚本路径
                    current_script = os.path.abspath(__file__)
                    
                    # 构建命令行
                    cmd = f'wt new-tab -p "Windows PowerShell" {os.getenv("PYTHON_PATH")} "{current_script}" --config "{config_file}" --log-file "{log_file}"'
                    
                    # 执行命令
                    import subprocess
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
                    if handler._file_check_timer:
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

class TextualLogHandler(logging.Handler):
    """Textual日志处理器，支持日志文件读取"""
    
    def __init__(self, app, log_file=None):
        super().__init__()
        self.app = app
        self.path_regex = re.compile(r'([A-Za-z]:\\[^\s]+|/([^\s/]+/){2,}[^\s/]+|\S+\.[a-zA-Z0-9]+)')
        self.max_msg_length = 80
        self.max_filename_length = 40
        self.enable_truncate = False
        self.log_file = log_file
        self.last_position = 0
        self._file_check_timer = None

    def _check_log_file(self):
        """检查日志文件更新"""
        if not self.log_file or not os.path.exists(self.log_file):
            return

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                f.seek(self.last_position)
                new_lines = f.readlines()
                if new_lines:
                    for line in new_lines:
                        line = line.strip()
                        if line:
                            # 查找第一个面板标识符 [# 或 [@
                            start_idx = -1
                            for i in range(len(line)):
                                if line[i:i+2] in ['[#', '[@']:
                                    start_idx = i
                                    break
                            
                            if start_idx >= 0:
                                # 找到面板标识符的结束位置 ]
                                end_idx = line.find(']', start_idx)
                                if end_idx > start_idx:
                                    # 提取消息内容（去掉面板标识符）
                                    msg = line[end_idx + 1:].strip()
                                else:
                                    msg = line
                            else:
                                msg = line
                                
                            self.emit(logging.makeLogRecord({
                                'msg': msg,
                                'levelno': logging.INFO,
                                'created': time.time()
                            }))
                self.last_position = f.tell()
        except Exception as e:
            print(f"Error reading log file: {e}")

    def _setup_file_watching(self):
        """设置日志文件监控"""
        if self.log_file and not self._file_check_timer and self.app and hasattr(self.app, "set_interval"):
            try:
                # 创建文件监控定时器前先确认应用还在运行中
                if hasattr(self.app, "_running") and self.app._running:
                    # 当前是0.1秒检查一次，改为0.05秒
                    self._file_check_timer = self.app.set_interval(0.05, self._check_log_file)
            except Exception:
                # 忽略定时器创建时的异常
                pass
                
    def close(self):
        """关闭处理器，停止所有定时器"""
        try:
            if self._file_check_timer:
                self._file_check_timer.stop()
                self._file_check_timer = None
        except Exception:
            pass
        super().close()
        
    def __del__(self):
        """析构函数，确保资源被释放"""
        self.close()

    def set_truncate(self, enable: bool = False):
        """设置是否启用截断功能"""
        self.enable_truncate = enable

    def _truncate_path(self, path: str, max_length: int = None) -> str:
        """智能路径截断处理
        
        Args:
            path: 需要截断的路径或文件名
            max_length: 最大允许长度，如果不指定则使用 max_filename_length
            
        Returns:
            截断后的字符串
        """
        if not self.enable_truncate:  # 如果未启用截断，直接返回原始路径
            return path
            
        if max_length is None:
            max_length = self.max_filename_length
            
        if len(path) <= max_length:
            return path
            
        # 检查是否是带扩展名的文件
        base, ext = os.path.splitext(path)
        if ext:
            # 确保扩展名完整保留
            ext_len = len(ext)
            if ext_len + 4 >= max_length:  # 如果扩展名太长
                return f"...{ext[-max_length+3:]}"
            
            # 计算基础名称可用长度
            base_length = max_length - ext_len - 3  # 3是...的长度
            if base_length > 0:
                # 如果基础名称包含方括号，尝试保留方括号内的内容
                bracket_match = re.match(r'(.*?)(\[.*?\])(.*?)$', base)
                if bracket_match:
                    prefix, brackets, suffix = bracket_match.groups()
                    if len(brackets) + ext_len + 6 <= max_length:  # 包括...和可能的连接符
                        available_space = max_length - (len(brackets) + ext_len + 6)
                        if available_space > 0:
                            prefix_len = min(len(prefix), available_space // 2)
                            suffix_len = min(len(suffix), available_space - prefix_len)
                            return f"{prefix[:prefix_len]}...{brackets}...{ext}"
                
                # 常规截断
                return f"{base[:base_length]}...{ext}"
            return f"...{ext}"
        
        # 不是文件名的情况
        return f"{path[:max_length-3]}..."

    def emit(self, record):
        """处理日志记录"""
        try:
            msg = self.format(record)
            
            # 检查是否包含面板标识符
            if not (msg.startswith('[#') or msg.startswith('[@')):
                return  # 如果没有面板标识符，直接返回不处理
            
            # 检查是否是真正的进度条（同时包含@和%）
            is_real_progress = '@' in msg and '%' in msg
            
            # 提取面板标签
            progress_match = re.match(r'^\[@(\w{2,})\](.*)$', msg)
            normal_match = re.match(r'^\[#(\w{2,})\](.*)$', msg)
            
            # 获取标签和内容
            panel_name = None
            content = msg
            tag = ""
            
            if progress_match:
                panel_name = progress_match.group(1)
                content = progress_match.group(2).strip()
                tag = f"[@{panel_name}]"
            elif normal_match:
                panel_name = normal_match.group(1)
                content = normal_match.group(2).strip()
                tag = f"[#{panel_name}]"
            else:
                return  # 如果无法匹配面板标识符，直接返回不处理
            
            # 只在启用截断时进行处理
            if self.enable_truncate:
                # 获取终端宽度
                try:
                    terminal_width = self.app.console.width if self.app and self.app.console else 80
                except:
                    terminal_width = 80
                    
                # 调整最大消息长度为终端宽度
                self.max_msg_length = max(terminal_width - 2, 40)  # 预留2个字符的边距
                
                # 处理消息截断
                if len(content) > self.max_msg_length - len(tag):
                    # 查找所有需要截断的路径
                    matches = list(self.path_regex.finditer(content))
                    if not matches:
                        # 如果没有找到文件名或路径，保留开头和结尾的重要信息
                        available_length = self.max_msg_length - len(tag) - 5  # 5是...和空格的长度
                        if available_length > 20:  # 确保有足够空间显示
                            # 分配60%给前部分，40%给后部分
                            front_length = int(available_length * 0.6)
                            back_length = available_length - front_length
                            content = f"{content[:front_length]}...{content[-back_length:]}"
                        else:
                            # 空间不足时只显示开头部分
                            content = f"{content[:self.max_msg_length-len(tag)-3]}..."
                    else:
                        truncated_content = content
                        offset = 0
                        
                        # 处理所有匹配项
                        for match in matches:
                            start = match.start() - offset
                            end = match.end() - offset
                            original = match.group()
                            
                            # 计算当前位置的可用长度
                            remaining_space = self.max_msg_length - len(tag)
                            if remaining_space < 10:  # 空间不足
                                remaining_space = self.max_msg_length  # 忽略标签长度以确保显示内容
                                
                            # 为文件名保留合理空间
                            file_space = min(remaining_space // 2, self.max_filename_length)
                            truncated = self._truncate_path(original, file_space)
                            
                            # 确保截断后的内容不会完全消失
                            if not truncated or len(truncated) < 5:  # 如果截断后太短
                                truncated = f"...{original[-10:]}"  # 至少保留最后10个字符
                                
                            if truncated != original:
                                truncated_content = truncated_content[:start] + truncated + truncated_content[end:]
                                offset += len(original) - len(truncated)
                        
                        content = truncated_content
                        
                        # 如果内容仍然太长，保留重要信息
                        if len(content) > self.max_msg_length - len(tag):
                            # 查找最后的数字信息（如：89.5）
                            number_match = re.search(r'(\d+\.?\d*%?|\(\d+/\d+\))[^\d]*$', content)
                            if number_match:
                                # 保留开头部分和结尾的数字信息
                                end_part = content[number_match.start():]
                                available_length = self.max_msg_length - len(tag) - len(end_part) - 3
                                if available_length > 10:
                                    content = f"{content[:available_length]}...{end_part}"
                                else:
                                    # 空间实在不足时
                                    content = f"{content[:self.max_msg_length-len(tag)-10]}...{end_part[-7:]}"
                            else:
                                # 如果没有数字信息，保留开头部分
                                content = f"{content[:self.max_msg_length-len(tag)-3]}..."
            
            # 重新组合消息
            final_msg = f"{tag}{content}" if tag else content
            
            # 根据消息类型更新面板
            if progress_match and is_real_progress:
                # 真正的进度条
                self.app.update_panel(panel_name, content)
            elif progress_match and not is_real_progress:
                # 错误使用@的面板，转为普通面板处理
                if record.levelno >= logging.ERROR:
                    content = f"❌ {content}"
                elif record.levelno >= logging.WARNING:
                    content = f"⚠️ {content}"
                self.app.update_panel(panel_name, content)
            elif normal_match:
                if record.levelno >= logging.ERROR:
                    content = f"❌ {content}"
                elif record.levelno >= logging.WARNING:
                    content = f"⚠️ {content}"
                self.app.update_panel(panel_name, content)
            else:
                if record.levelno >= logging.ERROR:
                    self.app.update_panel("update", f"❌ {final_msg}")
                elif record.levelno >= logging.WARNING:
                    self.app.update_panel("update", f"⚠️ {final_msg}")
                else:
                    self.app.update_panel("update", final_msg)
                
        except Exception as e:
            self.handleError(record)

    def _handle_progress_message(self, panel_name: str, content: str):
        """专用进度条处理（无图标添加）"""
        self.app.update_panel(panel_name, content)

    def _handle_normal_message(self, panel_name: str, content: str, record: logging.LogRecord):
        """普通消息处理（添加状态图标）"""
        if record.levelno >= logging.ERROR:
            content = f"❌ {content}"
        elif record.levelno >= logging.WARNING:
            content = f"⚠️ {content}"
        self.app.update_panel(panel_name, content)

    def _handle_default_message(self, msg: str, record: logging.LogRecord):
        """处理未指定面板的消息"""
        if record.levelno >= logging.ERROR:
            self.app.update_panel("update", f"❌ {msg}")
        elif record.levelno >= logging.WARNING:
            self.app.update_panel("update", f"⚠️ {msg}")
        else:
            self.app.update_panel("update", msg)

class LogPanel(Static):
    """自定义日志面板组件，支持固定行数显示和进度条"""
    
    content = reactive(list)
    
    def __init__(self, name: str, title: str, style: str = "white", ratio: int = 1, **kwargs):
        super().__init__(**kwargs)
        self.panel_name = name
        self.title = title
        self.base_style = style
        self.ratio = ratio
        self.content = []
        self.max_lines = 100  # 设置最大缓存行数
        self._cached_size = None
        self._cached_visible_lines = None
        self._cached_panel_height = None
        self.progress_bars = {}  # 存储进度条信息 {msg: (percentage, position, is_completed)}
        self.progress_positions = {}  # 存储进度条位置 {position: msg}
        self.next_progress_position = 0  # 下一个进度条位置

    def _escape_markup(self, text: str) -> str:
        """转义可能导致标记解析错误的字符"""
        # 替换方括号为转义字符
        text = text.replace('[', '\\[').replace(']', '\\]')
        # 替换其他可能导致问题的字符
        text = text.replace('{', '\\{').replace('}', '\\}')
        return text

    def _create_progress_bar(self, width: int, percentage: float, fraction: str = None, fraction_format: str = None) -> str:
        """创建带简单ASCII进度条的文本显示"""
        bar_width = max(10, width - 20)
        filled = int(round(bar_width * percentage / 100))
        
        # 根据完成状态使用不同字符
        if percentage >= 100:
            progress_bar = "█" * bar_width + " ✅"  # 完成时显示对勾
        else:
            progress_bar = "█" * filled + "░" * (bar_width - filled)
        
        # 组合内容
        if fraction_format:
            return self._escape_markup(f"{progress_bar} {fraction_format} {percentage:.1f}%")
        return self._escape_markup(f"{progress_bar} {percentage:.1f}%")

    def append(self, text: str) -> None:
        """追加内容并保持在最大行数限制内"""
        # 检查是否是进度条更新
        if self._is_progress_message(text):
            self._handle_progress_message(text)
        else:
            self._handle_normal_message(text)
            
        # 更新显示
        self._update_display()
        
        # 无论是否有进度条，都确保面板定期刷新
        if not hasattr(self, '_refresh_timer'):
            self._refresh_timer = self.set_interval(0.1, self._periodic_refresh)
            
        self.scroll_end()

    def _periodic_refresh(self) -> None:
        """定期刷新面板内容"""
        self._update_display()
        self.refresh()

    def on_unmount(self) -> None:
        """组件卸载时清理定时器"""
        if hasattr(self, '_refresh_timer'):
            self._refresh_timer.stop()

    def _is_progress_message(self, text: str) -> bool:
        """检查是否为进度条消息"""
        # 定义正则表达式组件
        PREFIX_PATTERN = r'([^%]*?(?=\s*(?:\[|\(|\d+(?:\.\d+)?%|\s*$)))'
        BRACKETED_FRACTION = r'(?:(\(|\[)(\d+/\d+)[\)\]])'
        PLAIN_FRACTION = r'(\d+/\d+)'
        FRACTION_PART = fr'\s*(?:{BRACKETED_FRACTION}|\s*{PLAIN_FRACTION})?'
        PERCENTAGE = r'(\d+(?:\.\d+)?)%'
        FRACTION_PERCENTAGE = r'\((\d+)/(\d+)\)'
        PERCENTAGE_PART = fr'\s*(?:{PERCENTAGE}|{FRACTION_PERCENTAGE})$'
        
        PROGRESS_PATTERN = fr'{PREFIX_PATTERN}{FRACTION_PART}{PERCENTAGE_PART}'
        return bool(re.match(PROGRESS_PATTERN, text))

    def _handle_progress_message(self, text: str) -> None:
        """处理进度条消息"""
        progress_info = self._parse_progress_info(text)
        if not progress_info:
            return
            
        msg_prefix, percentage, fraction, fraction_format = progress_info
        self._update_progress_bars(msg_prefix, percentage, fraction, fraction_format)

    def _parse_progress_info(self, text: str) -> Optional[tuple]:
        """解析进度条信息"""
        # 使用与_is_progress_message相同的正则表达式
        PREFIX_PATTERN = r'([^%]*?(?=\s*(?:\[|\(|\d+(?:\.\d+)?%|\s*$)))'
        BRACKETED_FRACTION = r'(?:(\(|\[)(\d+/\d+)[\)\]])'
        PLAIN_FRACTION = r'(\d+/\d+)'
        FRACTION_PART = fr'\s*(?:{BRACKETED_FRACTION}|\s*{PLAIN_FRACTION})?'
        PERCENTAGE = r'(\d+(?:\.\d+)?)%'
        FRACTION_PERCENTAGE = r'\((\d+)/(\d+)\)'
        PERCENTAGE_PART = fr'\s*(?:{PERCENTAGE}|{FRACTION_PERCENTAGE})$'
        
        PROGRESS_PATTERN = fr'{PREFIX_PATTERN}{FRACTION_PART}{PERCENTAGE_PART}'
        
        match = re.match(PROGRESS_PATTERN, text)
        if not match:
            return None
            
        msg_prefix = match.group(1).strip()
        percentage = None
        fraction = None
        fraction_format = None
        
        if match.group(2):  # 有括号
            bracket = match.group(2)
            fraction_display = match.group(3)
            fraction_format = f"{bracket}{fraction_display}{')'if bracket=='('else']'}"
        elif match.group(4):  # 无括号的分数
            fraction_display = match.group(4)
            fraction_format = fraction_display
        
        if match.group(5):  # 百分比格式
            percentage = float(match.group(5))
        else:  # 分数格式
            current = int(match.group(6))
            total = int(match.group(7))
            percentage = current * 100.0 / total
            fraction = f"{current}/{total}"
            
        return msg_prefix, percentage, fraction, fraction_format

    def _update_progress_bars(self, msg_prefix: str, percentage: float, 
                            fraction: Optional[str], fraction_format: Optional[str]) -> None:
        """更新进度条信息"""
        if msg_prefix in self.progress_bars:
            position = self.progress_bars[msg_prefix][1]
        else:
            position = self._get_available_position()
            
        is_completed = percentage >= 100
        self.progress_bars[msg_prefix] = (percentage, position, is_completed, fraction, fraction_format)
        self.progress_positions[position] = msg_prefix

    def _get_available_position(self) -> int:
        """获取可用的进度条位置"""
        # 首先检查是否有已完成的进度条位置
        for pos, msg in list(self.progress_positions.items()):
            if msg in self.progress_bars and self.progress_bars[msg][2]:
                del self.progress_bars[msg]
                del self.progress_positions[pos]
                return pos
                
        # 如果没有已完成的位置，检查是否需要替换最旧的位置
        if self.progress_positions:
            oldest_position = min(self.progress_positions.keys())
            oldest_msg = self.progress_positions[oldest_position]
            del self.progress_bars[oldest_msg]
            del self.progress_positions[oldest_position]
            return oldest_position
            
        # 如果没有任何位置，创建新位置
        position = self.next_progress_position
        self.next_progress_position += 1
        return position

    def _handle_normal_message(self, text: str) -> None:
        """处理普通消息"""
        cleaned_msg = re.sub(r'^(\S+\s+)', '', text)
        start_part = cleaned_msg[:4]

        if self.content and len(start_part) >= 4:
            last_msg = self.content[-1]
            last_cleaned = re.sub(r'^(\S+\s+)', '', last_msg)
            last_start = last_cleaned[:4]

            if start_part == last_start:
                self.content[-1] = text  # 合并相似消息
            else:
                self.content.append(text)
        else:
            self.content.append(text)

        # 保持内容在最大行数限制内
        if len(self.content) > self.max_lines:
            self.content = self.content[-self.max_lines:]

    def _update_display(self) -> None:
        """更新显示内容"""
        # 更新面板尺寸缓存
        self._update_size_cache()
        
        # 准备显示内容
        display_content = []
        
        # 添加进度条
        display_content.extend(self._get_progress_bar_content())
        
        # 添加普通消息
        display_content.extend(self._get_normal_message_content())
        
        # 更新渲染
        self.update_render("\n".join(display_content))

    def _update_size_cache(self) -> None:
        """更新尺寸缓存"""
        current_size = self.app.console.size if self.app else None
        if current_size != self._cached_size:
            self._cached_size = current_size
            self._cached_panel_height = self._calculate_panel_height()
            self._cached_visible_lines = self._cached_panel_height - 2 if self._cached_panel_height > 2 else 1

    def _get_progress_bar_content(self) -> List[str]:
        """获取进度条显示内容"""
        content = []
        console_width = self.app.console.width if self.app else 80
        
        for pos in sorted(self.progress_positions.keys()):
            msg_prefix = self.progress_positions[pos]
            if msg_prefix in self.progress_bars:
                percentage, _, _, fraction, fraction_format = self.progress_bars[msg_prefix]
                progress_bar = self._create_progress_bar(
                    console_width - len(msg_prefix) - 4,
                    percentage,
                    fraction,
                    fraction_format
                )
                content.append(self._escape_markup(f"{msg_prefix}{progress_bar}"))
        return content

    def _get_normal_message_content(self) -> List[str]:
        """获取普通消息显示内容"""
        content = []
        remaining_lines = max(0, (self._cached_visible_lines or 1) - len(self.progress_positions))
        
        if remaining_lines > 0:
            messages = list(reversed(self.content[-remaining_lines:]))
            for msg in messages:
                if self.app and self.app.console.width > 4:
                    content.append(f"- {self._escape_markup(msg)}")
                else:
                    content.append(f"- {self._escape_markup(msg)}")
                    
        return list(reversed(content))  # 恢复正确顺序

    def _calculate_panel_height(self) -> int:
        """计算面板应占用的高度"""
        if not self.app:
            return 3
            
        # 获取终端高度和面板数量（使用console的尺寸）
        terminal_height = self.app.console.size.height  # 修改为使用console的尺寸
        panels = list(self.app.query(LogPanel))
        
        # 计算可用高度（考虑标题栏和底部栏）
        available_height = terminal_height - 2  # 只减去Header和Footer
        
        # 计算所有面板的ratio总和
        total_ratio = sum(panel.ratio for panel in panels)
        
        # 计算每个ratio单位对应的高度（保留小数）
        unit_height = available_height / total_ratio
        
        # 对于除最后一个面板外的所有面板，向下取整
        is_last_panel = panels[-1] == self
        if not is_last_panel:
            base_lines = 3 # 最小显示行数
            panel_height = max(base_lines, int(unit_height * self.ratio))
            self._cached_visible_lines = panel_height - 2  # 增加可见行数
        else:
            # 最后一个面板获取剩余所有空间
            used_height = sum(max(3, int(unit_height * p.ratio)) for p in panels[:-1])
            panel_height = max(3, available_height - used_height)
        
        return panel_height
        
    def update_render(self, content: str) -> None:
        """普通文本渲染"""
        self.styles.border = ("heavy", self.base_style)
        self.styles.color = self.base_style  # 设置面板文本颜色
        self.border_title = f"{self.title}"
        self.border_subtitle = f"{self.panel_name}"
        super().update(content)

    def on_mount(self) -> None:
        """当组件被挂载时调用"""
        # 设置定时刷新，用于进度条动画
        self.set_interval(0.1, self.refresh)

class SystemStatusFooter(Footer):
    """自定义底部状态栏"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status = SystemStatus()
        self._last_io_time = time.time()
        
    def on_mount(self) -> None:
        self.set_interval(2, self.update_status)
        
    def update_status(self) -> None:
        """更新系统状态信息"""
        try:
            
            
            # 仅更新CPU使用率和内存
            self.status.cpu.usage = psutil.cpu_percent()
            self.status.memory_usage = psutil.virtual_memory().percent
            
            # 磁盘IO
            current_time = time.time()
            disk_io = psutil.disk_io_counters()
            if disk_io:
                time_diff = current_time - self._last_io_time
                if time_diff > 0:
                    read_speed = (disk_io.read_bytes - self.status.disk_io.read_bytes) / time_diff / 1024 / 1024
                    write_speed = (disk_io.write_bytes - self.status.disk_io.write_bytes) / time_diff / 1024 / 1024
                    
                    self.status.disk_io = DiskIOInfo(
                        read_speed=read_speed,
                        write_speed=write_speed,
                        read_bytes=disk_io.read_bytes,
                        write_bytes=disk_io.write_bytes
                    )
                
                self._last_io_time = current_time
                
        except ImportError:
            self.status = SystemStatus()
            
        self.status.last_update = datetime.now()
        self.refresh()
        
    def render(self) -> str:
        """简化后的状态显示"""
        status = (
            f"CPU: {self.status.cpu.usage:.1f}% | "
            f"内存: {self.status.memory_usage:.1f}% | "
            f"IO: R:{self.status.disk_io.read_speed:.1f}MB/s W:{self.status.disk_io.write_speed:.1f}MB/s"
        )
        return status

class TextualLogger(App):
    """Textual日志应用"""
    
    CSS = """
    #main-container {
        layout: vertical;
        width: 100%;
        height: 100%;
        background: $surface;
        padding: 0;
    }
    
    LogPanel {
        width: 100%;
        min-height: 3;
        height: auto;
        background: $surface;
        padding: 0 1;
        margin: 0;
        overflow: hidden;
    }
    
    LogPanel:focus {
        border: double $accent;
    }
    
    Static {
        width: 100%;
        height: auto;
        overflow: hidden;
    }
    
    Header {
        height: 1;
        padding: 0;
        margin: 0;
        background: $surface;
        color: $text;
    }
    
    Footer {
        height: 1;
        padding: 0;
        margin: 0;
        background: $surface;
        color: $text;
    }
    
    /* 调整底部栏样式 */
    SystemStatusFooter {
        width: 100%;
        content-align: center middle;
        padding: 0 1;
        background: $surface;
        color: $text;
    }
    """
    
    BINDINGS = [
        ("d", "toggle_dark", "主题"),  # 简化快捷键提示
        ("q", "quit", "退出")
    ]
    
    def __init__(self, layout_config: Dict):
        super().__init__()
        self.layout_config = layout_config
        self.panels: Dict[str, LogPanel] = {}
        self._pending_updates = []
        self.theme = "tokyo-night"
        self.script_name = os.path.basename(sys.argv[0])
        self.start_time = datetime.now()
        self._handlers = []  # 存储处理器列表
        
    def register_handler(self, handler):
        """注册日志处理器"""
        self._handlers.append(handler)
        
    def compose(self) -> ComposeResult:
        """初始化界面布局"""
        yield Header(show_clock=True)
        with Container(id="main-container"):
            for name, config in self.layout_config.items():
                panel = LogPanel(
                    name=name,
                    title=config.get("title", name),
                    style=config.get("style", "white"),
                    ratio=config.get("ratio", 1),
                    id=f"panel-{name}"
                )
                self.panels[name] = panel
                yield panel
        yield SystemStatusFooter()  # 使用自定义底部栏
    
    def action_focus_next(self) -> None:
        """焦点移到下一个面板"""
        current = self.focused
        panels = list(self.query(LogPanel))
        if current in panels:
            idx = panels.index(current)
            next_idx = (idx + 1) % len(panels)
            panels[next_idx].focus()
    
    def action_focus_previous(self) -> None:
        """焦点移到上一个面板"""
        current = self.focused
        panels = list(self.query(LogPanel))
        if current in panels:
            idx = panels.index(current)
            prev_idx = (idx - 1) % len(panels)
            panels[prev_idx].focus()
    
    def action_toggle_dark(self) -> None:
        """切换暗色/亮色主题"""
        if self.theme == "textual-light":
            self.theme = "textual-dark"
        else:
            self.theme = "textual-light"
    
    def on_mount(self) -> None:
        """初始化"""
        self.title = self.script_name
        self.set_interval(1, self.update_timer)
        
        # 处理待处理的更新
        for name, content in self._pending_updates:
            self._do_update(name, content)
        self._pending_updates.clear()
        
        # 初始化所有处理器的文件监控
        for handler in self._handlers:
            if isinstance(handler, TextualLogHandler):
                handler._setup_file_watching()
        
        # 默认聚焦第一个面板
        first_panel = next(iter(self.panels.values()), None)
        if first_panel:
            first_panel.focus()
    
    def create_panel(self, name: str, config: Dict) -> None:
        """动态创建新面板"""
        if name not in self.panels:
            panel = LogPanel(
                name=name,
                title=config.get("title", name),
                style=config.get("style", "white"),
                ratio=config.get("ratio", 1),  # 使用ratio代替size
                id=f"panel-{name}"
            )
            self.panels[name] = panel
            # 获取主容器并添加新面板
            main_container = self.query_one("#main-container")
            main_container.mount(panel)
            # 通知用户
            self.notify(f"已创建新面板: {name}")
            return panel
        return self.panels[name]

    def update_panel(self, name: str, content: str) -> None:
        """更新或创建面板内容"""
        if not self.is_mounted:
            self._pending_updates.append((name, content))
            return
            
        # 如果面板不存在，创建新面板
        if name not in self.panels:
            self.create_panel(name, {
                "title": name,
                "style": "cyan",  # 新面板默认使用青色
                "ratio": 1  # 默认ratio为1
            })
        
        self._do_update(name, content)
    
    def _do_update(self, name: str, content: str) -> None:
        """执行实际的更新操作"""
        try:
            if name in self.panels:
                self.panels[name].append(content)
                self.panels[name].scroll_end()
        except Exception as e:
            print(f"Error updating panel: {e}")

    def update_timer(self) -> None:
        """更新运行时间显示"""
        elapsed = datetime.now() - self.start_time
        hours, remainder = divmod(elapsed.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        time_str = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
        self.title = f"{self.script_name} [{time_str}]"  # 在标题中添加计时器

    def on_unmount(self) -> None:
        """组件卸载时处理"""
        # 停止所有面板的定时器
        for panel in self.panels.values():
            if hasattr(panel, '_refresh_timer'):
                try:
                    panel._refresh_timer.stop()
                except Exception:
                    pass
        
        # 停止处理器的文件监控定时器
        for handler in self._handlers:
            if isinstance(handler, TextualLogHandler) and handler._file_check_timer:
                try:
                    handler._file_check_timer.stop()
                except Exception:
                    pass
    
    def action_quit(self) -> None:
        """退出应用前清理资源"""
        # 停止所有面板的定时器
        for panel in self.panels.values():
            if hasattr(panel, '_refresh_timer'):
                try:
                    panel._refresh_timer.stop()
                except Exception:
                    pass
                    
        # 调用父类的退出方法
        super().action_quit()

if __name__ == "__main__":
    # 在作为独立脚本运行时处理命令行参数
    parser = argparse.ArgumentParser(description="Textual日志查看器")
    parser.add_argument("--config", help="布局配置文件路径")
    parser.add_argument("--log-file", help="要监控的日志文件路径")
    args = parser.parse_args()
    
    layout_config = None
    
    # 从配置文件加载布局配置
    if args.config and os.path.exists(args.config):
        try:
            import json
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
        # 演示使用
        print("未指定日志文件，启动演示模式")
        TextualLoggerManager.set_layout()
        
        # 保持程序运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            # 优雅关闭应用
            TextualLoggerManager.close()