from __future__ import annotations

from datetime import datetime
from typing import Optional, TypeVar, Union
from xml.etree.ElementTree import Element
from lxml.etree import _Element

K = TypeVar("K")
V = TypeVar("V")

# RecursiveDict = Union[dict[K, 'RecursiveDict[K, V]'], V]
RecursiveDict = Union[dict[K, Union[V, "RecursiveDict[K, V]"]]]


class XMLParseError(Exception):
    pass


class XMLParser:
    def __init__(self, indices: Optional[dict[str, str]] = None):
        self.indices = indices or {}

    def __call__(
        self, xml: Element
    ) -> Union[RecursiveDict[str, Optional[str]], Optional[str]]:
        return self.parse(xml)

    def parse(
        self,
        xml: Element,
        tag: Optional[str] = None,
        index_tag: str = "name",
    ) -> Union[RecursiveDict[str, Optional[str]], Optional[str]]:
        if tag is None:
            tag = xml.tag
        elements = [element for element in xml.findall("*") if element.tag != index_tag]
        if len(elements) == 0:
            return xml.text
        else:
            value: RecursiveDict[str, Optional[str]] = {}
            for element in elements:
                full_element_tag = tag + "/" + element.tag
                index_tag = self.indices.get(full_element_tag) or "name"
                index = element.find(index_tag)
                if index is None:
                    if element.tag in value:
                        raise XMLParseError(
                            f"Duplicated value for tag: {full_element_tag}"
                        )
                    value[element.tag] = self.parse(
                        element, full_element_tag, index_tag
                    )
                else:
                    if element.tag not in value:
                        value[element.tag] = {}
                    e = value[element.tag]
                    if not isinstance(e, dict):
                        raise XMLParseError()
                    if index.text in e:
                        raise XMLParseError(
                            f"Duplicated value for tag: {full_element_tag} index: {index.text}"
                        )
                    if index.text is None:
                        raise XMLParseError(
                            f"Wrong value for tag: {full_element_tag} index: {index.text}"
                        )
                    e[index.text] = self.parse(element, full_element_tag, index_tag)

            return value


def text(xml: Union[Element, _Element], xpath: str, strip: bool = False) -> Optional[str]:
    e = xml.find(xpath)
    if e is not None and e.text is not None:
        if not strip:
            return e.text
        else:
            return e.text.strip()
    return None


def number(xml: Union[Element, _Element], xpath: str) -> Optional[int]:
    e = xml.find(xpath)
    if e is not None and e.text is not None and e.text.isdigit():
        return int(e.text)
    return None


def timestamp(xml: Union[Element, _Element], xpath: str) -> Optional[datetime]:
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


# class XMLParser:
#     def __init__(self, indices: Optional[dict[str, str]] = None):
#         self.indices = indices or {}
#
#     def __call__(self, xml: Element) -> RecursiveDict[str, str] | str:
#         return self._xml_to_dict(xml)
#
#     def _xml_to_dict(
#         self,
#         xml: Element,
#         tag: Optional[str] = None,
#         index_tag: str = "name",
#     ) -> RecursiveDict[str, str] | str:
#         if tag is None:
#             tag = xml.tag
#         # elements = xml.xpath(f"*[not(self::{index_tag})]")
#         elements = [element for element in xml.findall("*") if element.tag != index_tag]
#         if len(elements) == 0:
#             return xml.text
#         else:
#             value: RecursiveDict[str, str] = {}
#             for element in elements:
#                 element_tag: str = element.tag
#                 full_element_tag = tag + "/" + element.tag
#                 index_tag = self.indices.get(full_element_tag) or "name"
#                 index = element.xpath(f"*[self::{index_tag}]")
#                 if len(index) == 0:
#                     if element_tag in value:
#                         raise XMLParseError(f"Duplicated value for tag: {full_element_tag}")
#                     value[element_tag] = self._xml_to_dict(element, full_element_tag, index_tag)
#                 else:
#                     if element_tag not in value:
#                         value[element_tag] = {}
#                     if index[0].text in value[element_tag]:
#                         raise XMLParseError(f"Duplicated value for tag: {full_element_tag} index: {index[0].text}")
#                     value[element_tag][index[0].text] = self._xml_to_dict(element, full_element_tag, index_tag)
#             return value
