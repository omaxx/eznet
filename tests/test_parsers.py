from lxml import etree
from eznet.parsers.xml import XMLParser, XMLParseError


def test_parser():
    xml = etree.fromstring("""
    <top>
        <none></none>
        <string>String</string>
        <nested>
            <string>String</string>
        </nested>
        <super>
            <nested>
                <string>String</string>
            </nested>
        </super>
    </top>
    """)
    parser = XMLParser()

    assert parser(xml) == {
        "none": None,
        "string": "String",
        "nested": {
            "string": "String",
        },
        "super": {
            "nested": {
                "string": "String",
            },
        }
    }


def test_dict():
    xml = etree.fromstring("""
    <top>
        <element-dict>
            <element>
                <name>first</name>
                <value>one</value>
            </element>
            <element>
                <name>second</name>
                <value>two</value>
            </element>
        </element-dict>
    </top>
    """)
    parser = XMLParser()

    assert parser(xml) == {
        "element-dict": {
            "element": {
                "first": {"value": "one"},
                "second": {"value": "two"},
            }
        }
    }


def test_dict_indices():
    xml = etree.fromstring("""
    <top>
        <element-dict>
            <element>
                <element-name>first</element-name>
                <value>one</value>
            </element>
            <element>
                <element-name>second</element-name>
                <value>two</value>
            </element>
        </element-dict>
    </top>
    """)
    parser = XMLParser(indices={"top/element-dict/element": "element-name"})

    assert parser(xml) == {
        "element-dict": {
            "element": {
                "first": {"value": "one"},
                "second": {"value": "two"},
            }
        }
    }
