# TextualLog

基于 Textual 的终端日志可视化工具，让您在终端中以美观的界面查看和监控日志。

## 功能特点

- 多面板布局，可自定义显示不同类型的日志
- 实时监控日志文件变化
- 支持进度条显示
- 支持系统资源监控
- 支持在 Windows Terminal 中开启新标签页显示

## 安装方法

### 通过 pip 从 PyPI 安装（推荐）

```bash
pip install textuallog
```

### 通过 pip 从 GitHub 安装

```bash
pip install git https://github.com/HibernalGlow/TextualLog.git
```

### 通过下载源码安装

1. 克隆或下载仓库
```bash
git clone https://github.com/您的用户名/TextualLog.git
cd TextualLog
```

2. 安装到本地环境
```bash
pip install -e .
```

## 基本使用

### 作为命令行工具使用

直接监控日志文件：

```bash
textual_logger --log-file your_log_file.log
```

或者使用短命令：

```bash
tlog --log-file your_log_file.log
```

### 作为库在代码中使用

```python
import logging
from textual_logger import set_layout

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
set_layout(TEXTUAL_LAYOUT)

# 发送日志到特定面板
logging.info("[#current_stats]总进度: 45%")
logging.info("[#current_progress]当前任务进度: 30%")
```

更多详细用法请参考 demo 示例。