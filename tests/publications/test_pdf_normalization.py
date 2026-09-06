"""Check the publication compatibility backend's actual PDF output contract."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "publication_builder", ROOT / "tools/documents/build_controlled_publications.py"
)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)
try:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import DecodedStreamObject, NameObject
except ImportError:
    PdfReader = None


@unittest.skipIf(
    PdfReader is None, "publication environment needs tools/documents/requirements.txt"
)
class PdfNormalizationTests(unittest.TestCase):
    def test_volatile_metadata_does_not_change_normalized_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            outputs = []
            for index in (1, 2):
                writer = PdfWriter()
                writer.add_blank_page(width=612, height=792)
                page = writer.add_blank_page(width=400, height=600)
                page.rotate(90)
                writer.add_metadata(
                    {"/CreationDate": f"D:2026010{index}120000Z", "/Title": f"volatile-{index}"}
                )
                metadata = DecodedStreamObject()
                metadata.set_data(f"<xmp>volatile-{index}</xmp>".encode())
                metadata[NameObject("/Type")] = NameObject("/Metadata")
                metadata[NameObject("/Subtype")] = NameObject("/XML")
                writer._root_object[NameObject("/Metadata")] = writer._add_object(metadata)
                writer.generate_file_identifiers()
                source = tmp / f"source-{index}.pdf"
                writer.write(source)
                output = tmp / f"output-{index}.pdf"
                BUILDER.normalize_with_pypdf(source, output)
                outputs.append(output.read_bytes())
                reader = PdfReader(output)
                self.assertIsNone(reader.metadata)
                self.assertNotIn("/Metadata", reader.trailer["/Root"])
                self.assertEqual(len(reader.pages), 2)
                self.assertEqual(tuple(reader.pages[0].mediabox), (0, 0, 612, 792))
                self.assertEqual(tuple(reader.pages[1].mediabox), (0, 0, 400, 600))
                self.assertEqual(reader.pages[1].rotation, 90)
                self.assertEqual(reader.trailer["/ID"][0], reader.trailer["/ID"][1])
            self.assertEqual(outputs[0], outputs[1])

    def test_encrypted_input_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)
            writer.encrypt("publication-test-password")
            writer.write(tmp / "encrypted.pdf")
            with self.assertRaises(ValueError):
                BUILDER.normalize_with_pypdf(tmp / "encrypted.pdf", tmp / "output.pdf")
            self.assertFalse((tmp / "output.pdf").exists())
