from dataclasses import dataclass, asdict

from ..drivers import SSH
from ..data import Data
from .get import get_xml, text, number


@dataclass
class Module:
    model: str
    sn: str
    pn: str
    description: str
    clei_code: str
    version: str

    @staticmethod
    def parse(chassis_hw, xpath):
        return dict(
            model=text(chassis_hw, f"{xpath}/model-number"),
            sn=text(chassis_hw, f"{xpath}/serial-number"),
            pn=text(chassis_hw, f"{xpath}/part-number"),
            description=text(chassis_hw, f"{xpath}/description"),
            clei_code=text(chassis_hw, f"{xpath}/clei-code"),
            version=text(chassis_hw, f"{xpath}/version"),
        )


@dataclass
class RE(Module):
    @classmethod
    def from_xml(cls, chassis_hw, module_name):
        xpath = f"//chassis-module[name='{module_name}']"
        return cls(
            **Module.parse(chassis_hw, xpath),
        )


@dataclass
class XCVR(Module):
    @classmethod
    def from_xml(cls, chassis_hw, module_name, sub_module_name, sub_sub_module_name):
        xpath = f"//chassis-module[name='{module_name}']" \
                f"/chassis-sub-module[name='{sub_module_name}']" \
                f"/chassis-sub-sub-module[name='{sub_sub_module_name}']"
        return cls(
            **Module.parse(chassis_hw, xpath),
        )


@dataclass
class PIC(Module):
    xcvr: dict[int, XCVR]

    @classmethod
    def from_xml(cls, chassis_hw, module_name, sub_module_name):
        xpath = f"//chassis-module[name='{module_name}']/chassis-sub-module[name='{sub_module_name}']"
        return cls(
            **Module.parse(chassis_hw, xpath),
            xcvr={
                int(text(xml, "name")[5:]): XCVR.from_xml(chassis_hw, module_name, sub_module_name, text(xml, "name"))
                for xml in chassis_hw.xpath(f"{xpath}/chassis-sub-sub-module")
                if text(xml, "name")[0:4] == "Xcvr"
            },
        )


def get_firmware(chassis_fw, fpc):
    xpath = f"//chassis-module[name='FPC {fpc}']"
    firmware = {
        text(xml, "type"): text(xml, "firmware-version").strip()
        for xml in chassis_fw.xpath(f"{xpath}/firmware")
    }
    if "ONIE/DIAG" in firmware:
        firmware["ONIE"], firmware["DIAG"] = firmware.pop("ONIE/DIAG").split("/")
    return firmware


@dataclass
class FPC(Module):
    pic: dict[int, PIC]
    firmware: dict[str, str]

    @classmethod
    def from_xml(cls, chassis_hw, module_name, chassis_fw=None):
        xpath = f"//chassis-module[name='{module_name}']"
        return cls(
            **Module.parse(chassis_hw, xpath),
            pic={
                int(text(xml, "name")[4:]): PIC.from_xml(chassis_hw, module_name, text(xml, "name"))
                for xml in chassis_hw.xpath(f"{xpath}/chassis-sub-module")
                if text(xml, "name")[0:3] == "PIC"
            },
            firmware=get_firmware(chassis_fw, 0) if chassis_fw is not None else None,

        )


@dataclass
class Chassis:
    sn: str
    description: str
    re: dict[int, RE]
    fpc: dict[int, FPC]

    @classmethod
    def from_xml(cls, chassis_hw, chassis_fw=None):
        return cls(
            sn=text(chassis_hw, "//chassis/serial-number"),
            description=text(chassis_hw, "//chassis/description"),
            re={
                int(text(xml, "name")[15:]): RE.from_xml(chassis_hw, text(xml, "name"))
                for xml in chassis_hw.xpath("//chassis-module")
                if text(xml, "name")[0:14] == "Routing Engine"
            },
            fpc={
                int(text(xml, "name")[4:]): FPC.from_xml(chassis_hw, text(xml, "name"), chassis_fw)
                for xml in chassis_hw.xpath("//chassis-module")
                if text(xml, "name")[0:3] == "FPC"
            },
        )


def get_chassis_info(ssh: SSH):
    chassis_hw = get_xml(ssh, "show chassis hardware", "//chassis-inventory/chassis")
    chassis_fw = get_xml(ssh, "show chassis firmware", "//firmware-information/chassis")

    return Chassis.from_xml(chassis_hw, chassis_fw)
