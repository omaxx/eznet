import re

from lxml import etree

from ..drivers import SSH


class GetException(Exception):
    pass


def get_xml(ssh: SSH, cmd: str, xpath: str) -> etree:
    output = ssh.run_cmd(f"{cmd} | display xml")
    output = search_rpc_reply(output)
    output = output.replace(' xmlns=', ' xmlnamespace=')
    xml = etree.fromstring(output)

    e = xml.xpath(xpath)
    if len(e):
        return e[0]
    else:
        if len(xml.xpath("//message")):
            error = xml.xpath("//message")[0].text.strip()
            raise GetException(error)
        elif len(xml.xpath("//output")):
            error = xml.xpath("//output")[0].text.strip()
            raise GetException(error)
        elif len(xml.xpath("//rpc-reply/*")):
            error = f"top tag is {xml.xpath('//rpc-reply/*')[0].tag}, expected: {xpath}"
            raise GetException(error)
        else:
            error = "Unknown error"
            raise GetException(error)


def search_rpc_reply(output: str) -> str:
    output = re.search("<rpc-reply.*/rpc-reply>", output, re.MULTILINE + re.DOTALL)
    if output is not None:
        return output[0]
    else:
        error = "<rpc-reply> not found in output"
        raise GetException(error)


def text(xml, xpath, separator="\n"):
    return separator.join([e.text for e in xml.xpath(xpath)])


def number(xml, xpath):
    txt = text(xml, xpath)
    if txt.isnumeric():
        return int(txt)
    else:
        return None
