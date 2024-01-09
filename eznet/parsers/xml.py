from datetime import datetime
from typing import Optional

from lxml.etree import _Element  # noqa


def text(xml: _Element, xpath: str, strip: bool = False) -> Optional[str]:
    e = xml.find(xpath)
    if e is not None and e.text is not None:
        if not strip:
            return e.text
        else:
            return e.text.strip()
    return None


def number(xml: _Element, xpath: str) -> Optional[int]:
    e = xml.find(xpath)
    if e is not None and e.text is not None and e.text.isdigit():
        return int(e.text)
    return None


def timestamp(xml: _Element, xpath: str) -> Optional[datetime]:
    e = xml.find(xpath)
    if e is not None:
        if e.text is not None and e.text.isdigit():
            return datetime.fromtimestamp(float(e.text))
        e_attrib_seconds = e.attrib.get("seconds")
        if isinstance(e_attrib_seconds, str) and e_attrib_seconds.isdigit():
            try:
                return datetime.fromtimestamp(int(e_attrib_seconds))
            except ValueError:
                pass
        e_attrib_format = e.attrib.get("format")
        if isinstance(e_attrib_format, str):
            try:
                return datetime.strptime(e_attrib_format, "%b %d %Y")
            except ValueError:
                pass
    return None
