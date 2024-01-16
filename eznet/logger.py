import logging
from pathlib import Path
from typing import Union, Optional

from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.logging import RichHandler
from rich.theme import Theme

from eznet import Device

MODULE = __name__.split(".")[0]


class LogHighlighter(RegexHighlighter):
    base_style = "eznet."
    highlights = [
        r"(?P<cmd>`.*?`)",
        r"(?P<source>^.*?:)",
        r"(?P<error>ERROR.*)",
    ]


theme = Theme(
    {
        "eznet.cmd": "green",
        "eznet.source": "magenta",
        "eznet.error": "red",
    }
)


def config_logger(
    level: int,
    file: Union[None, str, Path] = None,
    force_terminal: Optional[bool] = None,
    width: Optional[int] = None,
) -> None:
    logger = logging.getLogger(MODULE)
    logger.setLevel(level)

    console = Console(
        emoji=False,
        markup=False,
        theme=theme,
        force_terminal=force_terminal,
        width=width,
    )

    logger.addHandler(
        RichHandler(
            show_path=False,
            omit_repeated_times=False,
            highlighter=LogHighlighter(),
            console=console,
            level=level,
        )
    )

    if file is not None:
        if isinstance(file, str):
            file = Path(file)
        if not file.parent.exists():
            file.parent.mkdir(parents=True)

        handler = logging.FileHandler(file, mode="w")
        formatter = logging.Formatter(
            "{asctime} {levelname:8s} {message}",
            datefmt="[%x %X]",
            style="{",
        )
        handler.setFormatter(formatter)
        handler.setLevel(level)
        logger.addHandler(handler)


def config_device_logger(
    device: Device,
    level: int,
    file: Union[str, Path],
) -> None:
    if isinstance(file, str):
        file = Path(file)
    if not file.parent.exists():
        file.parent.mkdir(parents=True)

    logger = logging.getLogger(f"{MODULE}.device.{device.id}")
    logger.setLevel(level)

    handler = logging.FileHandler(file, mode="w")
    formatter = logging.Formatter(
        "{asctime} {levelname:8s} {message}",
        datefmt="[%x %X]",
        style="{",
    )
    handler.setFormatter(formatter)
    handler.setLevel(level)
    logger.addHandler(handler)
