# GeoSuite PVT Parser

Standalone parser package for GeoSuite `.pvt` files.

## Usage

```python
from geosuitepvt_parser import parse

result = parse("path/to/file.pvt")
for parsed in result:
    print(parsed.metadata.investigation_point, len(parsed.readings))
```

## Notes

- This package depends on the GeoSuite binary parser `libgeosuitepvt`.
- The parser extracts the investigation point from the file header.
- Coordinates (x/y/z) are not included in the standalone metadata.
