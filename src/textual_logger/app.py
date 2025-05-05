"""
应用模块，包含Textual应用主类
"""

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header
from typing import Dict, List, Optional, Any
import os
import sys
import asyncio
from datetime import datetime
import logging

# 导入组件
from .widgets import LogPanel, SystemStatusFooter
from .handler import TextualLogHandler

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
        self._handlers: List[TextualLogHandler] = []  # 存储处理器列表
        
    def register_handler(self, handler: TextualLogHandler):
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
            if hasattr(handler, '_file_check_timer') and handler._file_check_timer:
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