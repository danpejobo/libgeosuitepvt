from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import math

from .models import ParsedPiezometer, PiezometerMetadata, PiezometerReading


class PVTParser:
    """Parser wrapper for .pvt piezometer files."""

    _HEADER_PREFIX = "date"

    def parse(self, file_path: str) -> list[ParsedPiezometer]:
        # Kaller tekst-parseren direkte for å unngå avhengighet til libgeosuitepvt
        return [self._parse_text_file(file_path)]

    def _normalize_lib_output(
        self, parsed: Any, file_path: str
    ) -> list[ParsedPiezometer]:
        items = parsed if isinstance(parsed, list) else [parsed]
        normalized: list[ParsedPiezometer] = []
        for item in items:
            if isinstance(item, ParsedPiezometer):
                normalized.append(item)
                continue
            if isinstance(item, dict):
                meta = item.get("metadata") or item.get("meta") or {}
                rows = item.get("rows") or item.get("data") or []
                parsed_item = self._from_mapping(meta, rows, file_path)
                if parsed_item:
                    normalized.append(parsed_item)
        return normalized

    def _from_mapping(
        self, meta: Any, rows: Any, file_path: str
    ) -> ParsedPiezometer | None:
        investigation_point = self._first_value(
            meta, ["measure_point", "measurepoint", "investigation_point"]
        )
        if not investigation_point:
            return None

        series_number = self._first_value(
            meta, ["series_number", "serie_number", "serial", "serial_number"]
        )
        reading_time = self._coerce_datetime(
            self._first_value(meta, ["reading_time", "readingtime"])
        )
        installation_depth = self._coerce_float(
            self._first_value(
                meta, ["installation_depth", "installation_depth_m", "installation_depth(m)"]
            )
        )

        metadata = PiezometerMetadata(
            investigation_point=str(investigation_point),
            series_number=str(series_number) if series_number is not None else None,
            reading_time=reading_time,
            installation_depth=installation_depth,
            input_filename=Path(file_path).name,
        )

        readings: list[PiezometerReading] = []
        for row in self._rows_from_raw_data(rows):
            date_value = self._row_value(row, ["date"])
            time_value = self._row_value(row, ["time"])
            reading_time_value = self._parse_datetime_parts(date_value, time_value)
            if reading_time_value is None:
                continue
            readings.append(
                PiezometerReading(
                    reading_time=reading_time_value,
                    pressure_mh2o=self._coerce_float(
                        self._row_value(row, ["absolute_pressure", "pressure", "pressure_mh2o"])
                    ),
                    temperature_c=self._coerce_float(
                        self._row_value(row, ["temperature", "temperature_c"])
                    ),
                    battery_pct=self._coerce_float(
                        self._row_value(row, ["battery", "battery_pct"])
                    ),
                )
            )

        return ParsedPiezometer(metadata=metadata, readings=readings)

    def _parse_text_file(self, file_path: str) -> ParsedPiezometer:
        text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        lines = [line.rstrip("\n") for line in text.splitlines()]
        meta_line = ""
        for line in lines:
            if line.strip():
                meta_line = line.strip()
                break

        metadata = self._parse_metadata_line(meta_line, file_path)

        header_index = None
        for idx, line in enumerate(lines):
            if line.strip().lower().startswith(self._HEADER_PREFIX):
                header_index = idx
                break

        readings: list[PiezometerReading] = []
        if header_index is not None:
            data_start = header_index + 1
            if data_start < len(lines):
                unit_line = lines[data_start].strip()
                if unit_line and ("(" in unit_line or unit_line.startswith("\t")):
                    data_start += 1

            for line in lines[data_start:]:
                if not line.strip():
                    continue
                parts = line.split("\t")
                if len(parts) < 2:
                    continue
                reading_time = self._parse_datetime_parts(parts[0], parts[1])
                if reading_time is None:
                    continue
                pressure = self._coerce_float(parts[2]) if len(parts) > 2 else None
                temperature = self._coerce_float(parts[3]) if len(parts) > 3 else None
                battery = self._coerce_float(parts[4]) if len(parts) > 4 else None
                readings.append(
                    PiezometerReading(
                        reading_time=reading_time,
                        pressure_mh2o=pressure,
                        temperature_c=temperature,
                        battery_pct=battery,
                    )
                )

        return ParsedPiezometer(metadata=metadata, readings=readings)

    def _parse_metadata_line(self, line: str, file_path: str) -> PiezometerMetadata:
        parts = [part.strip() for part in line.split(",") if part.strip()]
        values: dict[str, str] = {}
        for part in parts:
            if ":" not in part:
                continue
            key, value = part.split(":", 1)
            values[self._normalize_key(key)] = value.strip()

        series_number = values.get("serienumber")
        reading_time = self._parse_datetime_value(values.get("readingtime"))
        measure_point = values.get("measurepoint") or Path(file_path).stem
        installation_depth = self._coerce_float(
            values.get("installationdepthm") or values.get("installationdepth")
        )

        return PiezometerMetadata(
            investigation_point=str(measure_point),
            series_number=series_number,
            reading_time=reading_time,
            installation_depth=installation_depth,
            input_filename=Path(file_path).name,
        )

    def _parse_datetime_value(self, value: str | None) -> Optional[datetime]:
        if not value:
            return None
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value.strip(), fmt)
            except ValueError:
                continue
        return self._coerce_datetime(value)

    def _parse_datetime_parts(self, date_value: Any, time_value: Any) -> Optional[datetime]:
        if not date_value or not time_value:
            return None
        if isinstance(date_value, str) and isinstance(time_value, str):
            combined = f"{date_value.strip()} {time_value.strip()}"
            return self._parse_datetime_value(combined)
        return None

    def _coerce_datetime(self, value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

    def _coerce_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            if "," in cleaned and "." in cleaned:
                if cleaned.rfind(",") > cleaned.rfind("."):
                    cleaned = cleaned.replace(".", "").replace(",", ".")
                else:
                    cleaned = cleaned.replace(",", "")
            elif "," in cleaned and "." not in cleaned:
                cleaned = cleaned.replace(",", ".")
            value = cleaned
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(number):
            return None
        return number

    def _normalize_key(self, value: str) -> str:
        return "".join(ch for ch in value.lower() if ch.isalnum())

    def _first_value(self, source: Any, keys: list[str]) -> Any:
        if source is None:
            return None
        if isinstance(source, dict):
            for key in keys:
                if key in source:
                    return source[key]
            normalized = {
                self._normalize_key(key): value
                for key, value in source.items()
                if isinstance(key, str)
            }
            for key in keys:
                match = normalized.get(self._normalize_key(key))
                if match is not None:
                    return match
        for key in keys:
            if hasattr(source, key):
                return getattr(source, key)
        return None

    def _row_value(self, row: Any, keys: list[str]) -> Any:
        return self._first_value(row, keys)

    def _rows_from_raw_data(self, raw_data: Any) -> list[Any]:
        if raw_data is None:
            return []
        if isinstance(raw_data, list):
            if not raw_data:
                return []
            if isinstance(raw_data[0], dict):
                return raw_data
            rows: list[Any] = []
            for item in raw_data:
                if isinstance(item, dict):
                    rows.append(item)
                elif hasattr(item, "__dict__"):
                    rows.append(vars(item))
            return rows
        if isinstance(raw_data, dict):
            for key in ("rows", "data", "values"):
                inner = raw_data.get(key)
                if isinstance(inner, list):
                    return inner
            if raw_data and all(isinstance(value, list) for value in raw_data.values()):
                keys = list(raw_data.keys())
                length = min(len(value) for value in raw_data.values())
                return [{key: raw_data[key][i] for key in keys} for i in range(length)]
        return []


def parse(file_path: str) -> list[ParsedPiezometer]:
    """Parse a PVT file and return metadata + readings."""
    return PVTParser().parse(file_path)