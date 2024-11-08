import logging
from pathlib import Path
from typing import Optional, Union

from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.logging import RichHandler
from rich.theme import Theme

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


def create_rich_handler(
    level: int = logging.INFO,
    width: Optional[int] = None,
    force_terminal: Optional[bool] = None,
) -> logging.Handler:
    console = Console(
        emoji=False,
        markup=False,
        theme=theme,
        width=width,
        force_terminal=force_terminal,
        stderr=True,
    )

    handler = RichHandler(
        show_path=False,
        omit_repeated_times=False,
        highlighter=LogHighlighter(),
        console=console,
        level=level,
    )
    return handler


def create_file_handler(file: Union[str, Path], level: int = logging.INFO) -> logging.Handler:
    if not isinstance(file, Path):
        file = Path(file)
    file.expanduser()
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
    return handler
