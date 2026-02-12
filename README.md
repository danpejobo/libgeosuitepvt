# GeoSuite PVT Parser

Standalone parser package for GeoSuite `.pvt` files.

## Usage

```python
import libgeosuitepvt

# Parse a file
result = libgeosuitepvt.parse("path/to/file.pvt")

for parsed in result:
    print(f"Point: {parsed.metadata.investigation_point}")
    print(f"Readings: {len(parsed.readings)}")
```

## Notes

- The parser extracts the investigation point from the file header.
- Coordinates (x/y/z) are not included in the standalone metadata.

