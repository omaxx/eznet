import logging
import colorlog


def init(level="INFO"):
    logger = logging.getLogger(__name__.split(".")[0])

    logger.setLevel(level)
    logger.addHandler(create_stderr_handler(level=(level)))
    return logger


def create_stderr_handler(level="INFO"):
    stderr = colorlog.StreamHandler()
    stderr.setFormatter(colorlog.ColoredFormatter('%(log_color)s%(asctime)-32s%(levelname)-10s%(message)s'))
    stderr.setLevel(level)
    return stderr


def create_file_handler(filename, level="DEBUG"):
    log_file = logging.FileHandler(filename)
    log_file.setFormatter(logging.Formatter('%(asctime)-32s%(levelname)-10s%(message)s'))
    log_file.setLevel(level)
    return log_file
