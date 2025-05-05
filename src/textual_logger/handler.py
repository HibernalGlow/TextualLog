"""
日志处理模块，包含用于Textual日志处理的Handler
"""

import logging
import os
import re
import time
import sys

class TextualLogHandler(logging.Handler):
    """Textual日志处理器，支持日志文件读取"""
    
    def __init__(self, app, log_file=None):
        super().__init__()
        self.app = app # app实例
        self.path_regex = re.compile(r'([A-Za-z]:\\[^\s]+|/([^\s/]+/){2,}[^\s/]+|\S+\.[a-zA-Z0-9]+)')
        self.max_msg_length = 80
        self.max_filename_length = 40
        self.enable_truncate = False
        self.log_file = log_file
        self.last_position = 0
        self._file_check_timer = None
        # 面板标识符正则表达式
        self.panel_tag_regex = re.compile(r'(\[[@#](\w{2,})\])')

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
                            self.emit(logging.makeLogRecord({
                                'msg': line,
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
            
            # 直接从消息中查找面板标识符
            panel_match = self.panel_tag_regex.search(msg)
            if not panel_match:
                return  # 如果没有面板标识符，直接返回不处理
            
            tag = panel_match.group(1)  # 完整标签，如[#panel]或[@panel]
            panel_name = panel_match.group(2)  # 面板名称，如panel
            
            # 获取标签后的内容
            content_start = panel_match.end()
            content = msg[content_start:].strip()
            
            # 判断是否为进度条（@开头的标签）
            is_progress = tag.startswith('[@')
            
            # 根据消息类型更新面板
            if is_progress and '@' in msg and '%' in msg:
                # 真正的进度条
                self.app.update_panel(panel_name, content)
            else:
                # 普通消息
                if record.levelno >= logging.ERROR:
                    content = f"❌ {content}"
                elif record.levelno >= logging.WARNING:
                    content = f"⚠️ {content}"
                self.app.update_panel(panel_name, content)
                
        except Exception as e:
            self.handleError(record)