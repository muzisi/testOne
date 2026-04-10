"""
日志工具类 - 基于 loguru 封装
支持控制台输出和文件保存
"""
import sys
from pathlib import Path
from loguru import logger


class Logger:
    """日志工具类"""

    def __init__(
        self,
        name: str = "app",
        log_dir: str = "logs",
        log_file: str = None,
        level: str = "INFO",
        rotation: str = "10 MB",
        retention: str = "7 days",
        format: str = None
    ):
        """
        初始化日志器

        Args:
            name: logger 名称
            log_dir: 日志文件目录
            log_file: 日志文件名，默认 {name}.log
            level: 日志级别 INFO/DEBUG/WARNING/ERROR
            rotation: 日志轮转大小，如 "10 MB"
            retention: 日志保留时间，如 "7 days"
            format: 日志格式，默认包含时间、级别、源码位置、内容
        """
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_file = log_file or f"{name}.log"
        self.level = level.upper()
        self.rotation = rotation
        self.retention = retention
        self.format = format or (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )

        # 移除默认处理器
        logger.remove()

        # 添加控制台处理器
        logger.add(
            sys.stdout,
            format=self.format,
            level=self.level,
            colorize=True
        )

        # 确保日志目录存在
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 添加文件处理器
        log_path = self.log_dir / self.log_file
        logger.add(
            log_path,
            format=self.format,
            level=self.level,
            rotation=self.rotation,
            retention=self.retention,
            compression="zip",  # 压缩旧日志
            enqueue=True  # 线程安全
        )

    def info(self, message: str, *args, **kwargs):
        """Info 级别日志"""
        logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        """Warning 级别日志"""
        logger.warning(message, *args, **kwargs)

    def warn(self, message: str, *args, **kwargs):
        """Warn 级别日志（warning 的别名）"""
        logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        """Error 级别日志"""
        logger.error(message, *args, **kwargs)

    def debug(self, message: str, *args, **kwargs):
        """Debug 级别日志"""
        logger.debug(message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs):
        """Exception 级别日志（自动包含堆栈信息）"""
        logger.exception(message, *args, **kwargs)

    def success(self, message: str, *args, **kwargs):
        """Success 级别日志"""
        logger.success(message, *args, **kwargs)


# 创建默认全局日志实例
default_logger = Logger(name="app")


# 便捷函数
def get_logger(name: str = None) -> Logger:
    """获取日志实例"""
    if name:
        return Logger(name=name)
    return default_logger


# ============ 使用示例 ============
if __name__ == "__main__":
    # 方式1：使用默认日志
    log = get_logger()
    log.info("This is an info message")
    log.warning("This is a warning message")
    log.error("This is an error message")
    log.success("Operation completed successfully")

    # 方式2：创建自定义日志
    custom_log = Logger(
        name="my_agent",
        log_dir="logs/agent",
        log_file="agent.log",
        level="DEBUG"
    )
    custom_log.info("Custom logger test")
    custom_log.debug("Debug message")
