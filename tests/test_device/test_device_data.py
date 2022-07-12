from eznet.device.data import Data


def test_device_data_load_1():
    device_data = Data.load(
        interfaces={
            "ae0": {
                "members": ["et-0/0/0", "et-0/0/1"]
            },
        }
    )
    assert device_data.interfaces["ae0"] is not None
    assert device_data.interfaces["et-0/0/0"] is not None
    assert device_data.interfaces["et-0/0/1"] is not None
    assert device_data.interfaces["ae0"].members == ["et-0/0/0", "et-0/0/1"]


def test_device_data_load_2():
    device_data = Data.load(
        interfaces={
            "ae0": {
                "members": {
                    "et-0/0/0": {"peer": {"interface": "et-0/0/4"}},
                    "et-0/0/1": {"peer": {"interface": "et-0/0/5"}},
                },
                "peer": {"device": "another", "interface": "ae1"}
            }
        }
    )
    assert device_data.interfaces["ae0"].peer.device == "another"
    assert device_data.interfaces["ae0"].peer.interface == "ae1"
    assert device_data.interfaces["et-0/0/0"].peer.interface == "et-0/0/4"
    assert device_data.interfaces["et-0/0/0"].peer.device == "another"
    assert device_data.interfaces["et-0/0/0"].ae == "ae0"
    assert device_data.interfaces["et-0/0/1"].peer.interface == "et-0/0/5"
    assert device_data.interfaces["et-0/0/1"].peer.device == "another"
    assert device_data.interfaces["et-0/0/1"].ae == "ae0"
    assert device_data.interfaces["ae0"].members == ["et-0/0/0", "et-0/0/1"]
