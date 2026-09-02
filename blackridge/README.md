# Blackridge Enterprise Data Foundation v0.1.0

This package deterministically builds the public Blackridge 2015 enterprise database and
SQL-derived master workbook. It preserves the public/private boundary: no oracle truth is
stored in the public schema or generated workbook.

```bash
cd blackridge
python -m pip install -e '.[dev]'
python -m blackridge doctor
python -m blackridge generate --profile smoke --seed 20150112
python -m blackridge generate --profile m00 --seed 20150112
python -m blackridge generate --profile full_2015 --seed 20150112
python -m blackridge validate --profile full_2015
python -m blackridge export all --profile full_2015
pytest
```

The canonical source is SQLite. Excel is a generated human interface. Generated databases,
workbooks, reports, and manifests record hashes and validation state.

