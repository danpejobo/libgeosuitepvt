from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PiezometerMetadata:
    investigation_point: str
    series_number: Optional[str]
    reading_time: Optional[datetime]
    installation_depth: Optional[float]
    input_filename: Optional[str] = None


@dataclass
class PiezometerReading:
    reading_time: datetime
    pressure_mh2o: Optional[float]
    temperature_c: Optional[float]
    battery_pct: Optional[float]


@dataclass
class ParsedPiezometer:
    metadata: PiezometerMetadata
    readings: list[PiezometerReading]
