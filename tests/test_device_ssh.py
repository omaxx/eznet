import pytest
import asyncio
import os

from eznet import Device
from eznet.inventory.device.drivers.errors import ConnectError, AuthenticationError, ExecutionError, ProxyError

PROXY = "172.31.0.8"
R1_DIRECT_IP = "172.31.0.96"
R1_REMOTE_IP = "192.168.0.1"
R2_DIRECT_IP = "172.31.0.97"
R2_REMOTE_IP = "192.168.0.2"
WRONG_IP = "172.31.0.250"


async def process(device: Device):
    async with device.ssh:
        return await device.ssh.execute("show system info")


@pytest.mark.asyncio
async def test_unnamed():
    r1 = Device(R1_DIRECT_IP)
    r2 = Device(R2_DIRECT_IP)

    await asyncio.gather(process(r1), process(r2))


@pytest.mark.asyncio
async def test_single_ip():
    r1 = Device("R1", ip=R1_DIRECT_IP)
    r2 = Device("R2", ip=R2_DIRECT_IP)

    await asyncio.gather(process(r1), process(r2))


@pytest.mark.asyncio
async def test_list_ip():
    proxy = Device(PROXY)
    r1 = Device("R1", ip=[R1_DIRECT_IP, R1_REMOTE_IP])
    r2 = Device("R2", ip=[(R2_DIRECT_IP, None), R2_REMOTE_IP], proxy=proxy)

    await asyncio.gather(process(r1), process(r2))


@pytest.mark.asyncio
async def test_dict_ip():
    proxy = Device(PROXY)
    r1 = Device("R1", ip={"ge-0/0/0": R1_DIRECT_IP, "fxp0": R1_REMOTE_IP})
    r2 = Device("R2", ip={"ge-0/0/0": (R2_DIRECT_IP, None), "fxp0": R2_REMOTE_IP}, proxy=proxy)

    await asyncio.gather(process(r1), process(r2))


@pytest.mark.asyncio
async def test_proxy_unnamed():
    proxy = Device(PROXY)
    r1 = Device(R1_REMOTE_IP, proxy=proxy)
    r2 = Device(R2_REMOTE_IP, proxy=proxy)

    async with proxy.ssh:
        await asyncio.gather(process(r1), process(r2))


@pytest.mark.asyncio
async def test_proxy_single_ip():
    proxy = Device(PROXY)
    r1 = Device("R1", ip=R1_REMOTE_IP, proxy=proxy)
    r2 = Device("R2", ip=(R2_REMOTE_IP, proxy))

    async with proxy.ssh:
        await asyncio.gather(process(r1), process(r2))


@pytest.mark.asyncio
async def test_proxy_list_ip():
    proxy = Device(PROXY)
    r1 = Device("R1", ip=[(R1_REMOTE_IP, proxy), R1_DIRECT_IP])
    r2 = Device("R2", ip=[R2_REMOTE_IP, (R2_DIRECT_IP, None)], proxy=proxy)

    async with proxy.ssh:
        await asyncio.gather(process(r1), process(r2))


@pytest.mark.asyncio
async def test_proxy_dict_ip():
    proxy = Device(PROXY)
    r1 = Device("R1", ip={"fxp0": (R1_REMOTE_IP, proxy), "ge-0/0/0": R1_DIRECT_IP})
    r2 = Device("R2", ip={"fxp0": R2_REMOTE_IP, "ge-0/0/0": (R2_DIRECT_IP, None)}, proxy=proxy)

    async with proxy.ssh:
        await asyncio.gather(process(r1), process(r2))


@pytest.mark.asyncio
async def test_connect_error():
    device = Device(WRONG_IP)
    with pytest.raises(ConnectError):
        await device.ssh.connect()


@pytest.mark.asyncio
async def test_proxy_error():
    proxy = Device(PROXY)
    device = Device(R1_DIRECT_IP, proxy=proxy)
    with pytest.raises(ConnectError):
        await device.ssh.connect()


# @pytest.mark.asyncio
# async def test_no_ip_error():
#     device = Device(R1_DIRECT_IP, ip=None)
#     with pytest.raises(ConnectError):
#         await device.ssh.connect()
#
#
@pytest.mark.asyncio
async def test_authentication_error():
    device = Device(R1_DIRECT_IP, user_name="boo")
    with pytest.raises(AuthenticationError):
        await device.ssh.connect()


@pytest.mark.asyncio
async def test_execution_error():
    device = Device(R1_DIRECT_IP)
    with pytest.raises(ExecutionError):
        await device.ssh.execute("show system info")


@pytest.mark.asyncio
async def test_reconnect():
    device = Device(R1_DIRECT_IP)
    async with device.ssh:
        await device.ssh.execute(f"request system logout user {os.environ['USER']}")
        for i in range(30):
            try:
                await device.ssh.execute("show system info")
                return
            except ExecutionError:
                await asyncio.sleep(1)


@pytest.mark.asyncio
async def test_long_command():
    device = Device(R1_DIRECT_IP)
    async with device.ssh:
        with pytest.raises(ExecutionError):
            await device.ssh.execute(f'start shell command "csh run.sh 1 10"', timeout=5)

# run.sh :
# if ( $#argv != 2 ) then
#     echo "usage: csh run.sh <timeout> <runs>"
#     exit 1
# endif
#
# set i = 0
# while ( $i < $2 )
#     echo "Running..."
#     sleep $1
#     @ i++
# end
