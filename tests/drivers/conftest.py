import pytest

from eznet.drivers.ssh import SSH
from tests.conftest import devices_by_tags


LINUX_DEVICES = devices_by_tags("linux")


@pytest.fixture(params=LINUX_DEVICES, ids=lambda d: d["name"])
def device_info(request):
    return request.param


@pytest.fixture
async def ssh(device_info):
    s = SSH(name=device_info["name"], ip=device_info["ip"])
    await s.open()
    yield s
    await s.close()
