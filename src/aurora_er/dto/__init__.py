"""Data transfer objects for the transport layer: immutable and validated on construction."""

from aurora_er.dto.battery import BatteryDTO, BatterySpecDTO, BatteryStateDTO
from aurora_er.dto.horizon import HorizonDTO
from aurora_er.dto.market import MarketDTO
from aurora_er.dto.options import SolveOptionsDTO
from aurora_er.dto.result import (
    DispatchResultDTO,
    MarketDispatchDTO,
    RollingDispatchResultDTO,
    SolveStatus,
)
from aurora_er.dto.validation import InvalidDTOError

__all__ = [
    "BatteryDTO",
    "BatterySpecDTO",
    "BatteryStateDTO",
    "DispatchResultDTO",
    "HorizonDTO",
    "InvalidDTOError",
    "MarketDTO",
    "MarketDispatchDTO",
    "RollingDispatchResultDTO",
    "SolveOptionsDTO",
    "SolveStatus",
]
