"""
数据模型模块，包含系统状态监控的数据类
"""

from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class CPUInfo:
    usage: float = 0.0  # CPU使用率

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