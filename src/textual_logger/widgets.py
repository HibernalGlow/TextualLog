"""
UI组件模块，包含日志面板和状态栏组件
"""

from textual.widgets import Static, Footer
from textual.reactive import reactive
from textual import work
import psutil
import time
from datetime import datetime
import re
import os
from typing import Dict, Optional, List, Any, Tuple

# 导入数据模型
from .models import SystemStatus, DiskIOInfo

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

    def _parse_progress_info(self, text: str) -> Optional[Tuple[str, float, Optional[str], Optional[str]]]:
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