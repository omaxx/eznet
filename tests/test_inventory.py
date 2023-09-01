from eznet.inventory import Inventory


def test_load():
    inventory = Inventory()
    inventory.load("inventory/")
    assert inventory.devices[0].id == "vlab.vmx-1"
