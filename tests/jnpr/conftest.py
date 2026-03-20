import pytest

from eznet.jnpr import Device
from tests.conftest import devices_by_tags


JUNOS_DEVICES = devices_by_tags("junos")
SINGLE_RE_DEVICES = devices_by_tags("single_re_vmx")
DUAL_RE_DEVICES = devices_by_tags("dual_re_vmx")


@pytest.fixture(params=JUNOS_DEVICES, ids=lambda d: d["name"])
def device_info(request):
    return request.param


@pytest.fixture(params=SINGLE_RE_DEVICES, ids=lambda d: d["name"])
def single_re_device_info(request):
    return request.param


@pytest.fixture(params=DUAL_RE_DEVICES, ids=lambda d: d["name"])
def dual_re_device_info(request):
    return request.param


@pytest.fixture
async def device(device_info):
    dev = Device(name=device_info["name"], ip=device_info["ip"])
    await dev.ssh.open()
    yield dev
    await dev.ssh.close()


@pytest.fixture
async def single_re_device(single_re_device_info):
    dev = Device(name=single_re_device_info["name"], ip=single_re_device_info["ip"])
    await dev.ssh.open()
    yield dev
    await dev.ssh.close()


@pytest.fixture
async def dual_re_device(dual_re_device_info):
    dev = Device(name=dual_re_device_info["name"], ip=dual_re_device_info["ip"])
    await dev.ssh.open()
    yield dev
    await dev.ssh.close()
