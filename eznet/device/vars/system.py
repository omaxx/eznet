from __future__ import annotations

from typing import Optional

from attrs import define


@define
class System:
    hostname: Optional[str] = None
