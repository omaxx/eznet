import pytest


TESTBED_DEVICES = [
    {"name": "omega", "ip": "172.31.0.8", "tags": ["linux"]},
    {"name": "vmx1", "ip": "172.31.0.32", "tags": ["junos", "vmx", "single_re_vmx"]},
    {"name": "vmx2", "ip": "172.31.0.33", "tags": ["junos", "vmx", "dual_re_vmx"]},
]


def pytest_addoption(parser):
    parser.addoption("--testbed", action="store_true", default=False, help="run testbed tests")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--testbed"):
        skip = pytest.mark.skip(reason="need --testbed option to run")
        for item in items:
            if "testbed" in item.keywords:
                item.add_marker(skip)


def devices_by_tags(*tags):
    required = set(tags)
    return [d for d in TESTBED_DEVICES if required.issubset(d["tags"])]
