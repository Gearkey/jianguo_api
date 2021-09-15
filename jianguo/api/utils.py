import logging

# 调试日志设置
logger = logging.getLogger("jianguo")
logger.setLevel(logging.ERROR)
formatter = logging.Formatter(
    fmt="%(asctime)s [line:%(lineno)d] %(funcName)s %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")
console = logging.StreamHandler()
console.setFormatter(formatter)
logger.addHandler(console)
