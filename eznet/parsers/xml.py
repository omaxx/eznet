from datetime import datetime
from typing import Optional, Dict, Any

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


class XMLParseError(Exception):
    pass


class XMLParser:
    def __init__(self, indices=None) -> None:
        self.indices = indices or {}

    def __call__(self, xml) -> Dict[str, Any]:
        return self._xml_to_dict(xml)

    def _xml_to_dict(self, xml, tag=None, index_tag="name") -> Dict[str, Any]:
        if tag is None:
            tag = xml.tag
        elements = xml.xpath(f"*[not(self::{index_tag})]")
        if len(elements) == 0:
            return xml.text
        else:
            value = {}
            for element in elements:
                element_tag = tag + "/" + element.tag
                index_tag = self.indices.get(element_tag) or "name"
                index = element.xpath(f"*[self::{index_tag}]")
                if len(index) == 0:
                    if element.tag in value:
                        raise XMLParseError(f"Duplicated value for tag: {element_tag}")
                    value[element.tag] = self._xml_to_dict(element, element_tag, index_tag)
                else:
                    if element.tag not in value:
                        value[element.tag] = {}
                    if index[0].text in value[element.tag]:
                        raise XMLParseError(f"Duplicated value for tag: {element_tag} index: {index[0].text}")
                    value[element.tag][index[0].text] = self._xml_to_dict(element, element_tag, index_tag)
            return value
