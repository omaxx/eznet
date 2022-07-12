from collections.abc import MutableMapping, Sequence
from typing import Union, Dict, Any, Tuple, TypeVar, List


def string_to_dict(item, key="name") -> MutableMapping:
    if isinstance(item, MutableMapping):
        return item
    if isinstance(item, str):
        return {key: item}
    raise TypeError(f"could not convert {type(item)} to dict")


def list_to_dict(sequence: Union[Sequence, MutableMapping], key="name", remove_key=True) -> MutableMapping:
    if isinstance(sequence, MutableMapping):
        if remove_key:
            return sequence
        else:
            return {
                name: {**item, key: name}
                for name, item in sequence.items()
            }
    if isinstance(sequence, list):
        sequence = [string_to_dict(item, key) for item in sequence]
        if remove_key:
            return {
                item.pop(key): item for item in sequence
            }
        else:
            return {
                item.get(key): item for item in sequence
            }
    raise TypeError(f"counld not convert {type(sequence)} to dict")


def interface_name_to_port(interface_name: str) -> List[int]:
    if ":" in interface_name:
        return [
            *interface_name_to_port(interface_name.split(":")[0]),
            int(interface_name.split(":")[1])
        ]
    if "-" in interface_name:
        return [
            i for i in map(int, interface_name.split("-")[1].split("/"))
        ]
    if interface_name[:2] == 'ae':
        return [int(interface_name[2:])]
