from eznet.device import SSH, Data, Info


def test_device_driver_ssh():
    ssh = SSH(
        ip="1.1.1.1",
        user_name="test",
        user_password="test"
    )
