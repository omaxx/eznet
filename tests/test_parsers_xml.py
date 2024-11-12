from xml.etree import ElementTree
# from lxml import etree

from eznet.parsers.xml import XMLParser, text, number, timestamp


def test_parsers():
    xml = ElementTree.fromstring(
        """
        <system-information>
            <hardware-model>vmx</hardware-model>
            <version>1</version>
        </system-information>
        """
    )
    assert text(xml, "hardware-model") == "vmx"
    assert number(xml, "version") == 1


def test_xml_parse():
    xml = ElementTree.fromstring(
"""
<system-information>
    <hardware-model>vmx</hardware-model>
    <os-name>junos</os-name>
</system-information>
"""
    )
    assert XMLParser()(xml) == {
        "hardware-model": "vmx",
        "os-name": "junos"
    }


def test_xml_parse_dict():
    xml = ElementTree.fromstring(
"""
<interface-information>
    <physical-interface>
        <name>ge-0/0/0</name>
        <admin-status>up</admin-status>
        <oper-status>up</oper-status>
        <logical-interface>
            <name>ge-0/0/0.0</name>
            <address-family>
                <address-family-name>inet</address-family-name>
                <mtu>1500</mtu>
            </address-family>
        </logical-interface>
    </physical-interface>
</interface-information>
"""
    )
    assert XMLParser({
        "interface-information/physical-interface/logical-interface/address-family": "address-family-name",
    })(xml) == {
        "physical-interface": {
            "ge-0/0/0": {
                "admin-status": "up",
                "oper-status": "up",
                "logical-interface": {
                    "ge-0/0/0.0": {
                        "address-family": {
                            # "address-family-name": "inet",
                            # "mtu": "1500",
                            "inet": {
                                "mtu": "1500",
                            }
                        }
                    }
                }
            }
        },
    }
