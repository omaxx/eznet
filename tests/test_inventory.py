from eznet import Inventory


def test_load():
    inventory = Inventory()
    inventory.load("inventory/devices/")
