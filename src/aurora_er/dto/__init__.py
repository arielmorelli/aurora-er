"""Data transfer objects for the transport layer: immutable and validated on construction."""

from aurora_er.dto.battery import BatterySpecDTO
from aurora_er.dto.market import MarketDTO
from aurora_er.dto.validation import InvalidDTOError

__all__ = ["BatterySpecDTO", "InvalidDTOError", "MarketDTO"]
