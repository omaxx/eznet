from typing import Dict, List, Union


class XMLParseError(Exception):
    pass


class XMLParser:
    def __init__(self,
                 mappings: Dict[str, dict] = None,
                 sequences: List[str] = None,
                 keep_mapping_key: bool = False,
                 default_index_tag: Union[bool, str] = "name",
                 dash_to_underscore: bool = True,

                 ):
        self.mappings = mappings or {}
        self.sequences = sequences or []
        self.keep_mapping_key = keep_mapping_key
        self.default_index_tag = default_index_tag
        self.dash_to_underscore = dash_to_underscore

    def parse(self, xml, xpath=None, ignore_tag=None):
        if xpath is None:
            xpath = xml.tag
        if ignore_tag is not None and not self.keep_mapping_key:
            elements = xml.xpath(f"*[not(self::{ignore_tag})]")
        else:
            elements = xml.xpath("*")
        if len(elements) == 0:
            return xml.text
        else:
            value = {}
            for element in elements:
                element_xpath = xpath + "/" + element.tag
                if not self.dash_to_underscore:
                    key = element.tag
                else:
                    key = element.tag.replace("-", "_")
                if element_xpath in self.sequences:
                    if key not in value:
                        value[key] = []
                    value[key].append(self.parse(element, element_xpath))
                    continue
                if element_xpath in self.mappings:
                    index_tag = self.mappings.get(element_xpath)
                    if key  not in value:
                        value[key] = {}
                    index = element.xpath(f"*[self::{index_tag}]")
                    if len(index) == 0:
                        raise XMLParseError(f"Cound not find index {index_tag} for xpath: {element_xpath}")
                    if index[0].text in value[key]:
                        raise XMLParseError(f"Duplicated value for xpath: {element_xpath} index: {index[0].text}")
                    value[key][index[0].text] = self.parse(element, element_xpath, index_tag)
                    continue
                if self.default_index_tag is not False:
                    index_tag = self.default_index_tag
                    index = element.xpath(f"*[self::{index_tag}]")
                    if len(index) == 0:
                        if key in value:
                            raise XMLParseError(f"Duplicated value for tag: {element_xpath}")
                    else:
                        if key not in value:
                            value[key] = {}
                        if index[0].text in value[key]:
                            raise XMLParseError(f"Duplicated value for tag: {element_xpath} index: {index[0].text}")
                        value[key][index[0].text] = self.parse(element, element_xpath, index_tag)
                        continue

                if key in value:
                    raise XMLParseError(f"Duplicated value for xpath: {element_xpath}")
                value[key] = self.parse(element, element_xpath)

            return value
