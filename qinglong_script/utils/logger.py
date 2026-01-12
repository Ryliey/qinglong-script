import logging


def setup_logger():
    """
    配置并返回一个标准格式的日志记录器

    :return: 配置好的日志记录器实例
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger()


logger = setup_logger()

# Disable httpx logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
