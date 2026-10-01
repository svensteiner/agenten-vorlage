import json
import os
import subprocess
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

from agentkit.contracts import ContractError
from cockpit.image_extract import extract_image


def png(width=10, height=10, color=True):
    signature = b"\x89PNG\r\n\x1a\n"
    fmt = b"\x08\x06\x00\x00\x00" if color else b"\x08\x02\x00\x00\x00"
    return signature + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, height) + fmt + b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00IEND\xaeB`\x82"


class ImageExtractTests(unittest.TestCase):
    @unittest.skipUnless(
        sys.platform == "win32" and os.environ.get("AGENTKIT_RUN_REAL_OCR", "1") == "1",
        "real Windows OCR requires AGENTKIT_RUN_REAL_OCR=1 on a Windows host",
    )
    def test_real_local_windows_ocr_fixture(self):
        for filename in ("reference.png", "reference.jpg"):
            fixture = Path(__file__).parent / "fixtures" / "ocr" / filename
            result = extract_image(fixture.name, fixture.read_bytes())
            self.assertEqual("windows-ocr", result["extraction_method"])
            self.assertTrue(result["language"] in {"de-DE", "en-US"})
            self.assertIn("OCR REFERENCE 930", result["text"])
        fixture = Path(__file__).parent / "fixtures" / "ocr" / "unicode.png"
        result = extract_image(fixture.name, fixture.read_bytes())
        if result["language"] == "de-DE":
            self.assertIn("Grüße für Österreich", result["text"])
        self.assertNotIn("\ufffd", result["text"])

    def test_non_windows_fails_closed_before_process(self):
        with patch("cockpit.image_extract.sys.platform", "linux"), patch("cockpit.image_extract.subprocess.run") as run:
            with self.assertRaises(ContractError):
                extract_image("x.png", png())
            run.assert_not_called()

    def test_signature_format_and_dimension_limits(self):
        with patch("cockpit.image_extract.sys.platform", "win32"):
            for name, data in (("x.jpg", png()), ("x.png", b"bad"), ("x.gif", png()), ("x.png", png(4097, 1)), ("x.png", png(3000, 3000))):
                with self.assertRaises(ContractError):
                    extract_image(name, data)
            with self.assertRaises(ContractError):
                extract_image("x.png", b"x" * (2 * 1024 * 1024 + 1))

    def test_success_contract_and_sanitized_process(self):
        result = {"text": "Hallo", "extraction_method": "windows-ocr", "language": "de-DE"}
        with patch("cockpit.image_extract.sys.platform", "win32"), patch("cockpit.image_extract.subprocess.run", return_value=type("R", (), {"returncode": 0, "stdout": json.dumps(result)})()) as run:
            value = extract_image("scan.png", png())
        self.assertEqual(result, value)
        command = run.call_args.args[0]
        self.assertEqual(command[0].lower(), r"c:\windows\system32\windowspowershell\v1.0\powershell.exe")
        self.assertIn("-NoProfile", command)
        self.assertIn("-NonInteractive", command)
        self.assertNotIn("-ExecutionPolicy", command)

    def test_bad_process_output_timeout_and_text_limits(self):
        for result in ({"text": "", "extraction_method": "windows-ocr", "language": "de-DE"}, {"text": "x", "extraction_method": "wrong", "language": "de-DE"}, [], {"text": "x", "extraction_method": "windows-ocr", "language": "not valid"}):
            with patch("cockpit.image_extract.sys.platform", "win32"), patch("cockpit.image_extract.subprocess.run", return_value=type("R", (), {"returncode": 0, "stdout": json.dumps(result)})()):
                with self.assertRaises(ContractError):
                    extract_image("scan.png", png())
        with patch("cockpit.image_extract.sys.platform", "win32"), patch("cockpit.image_extract.subprocess.run", side_effect=subprocess.TimeoutExpired("ocr", 15)):
            with self.assertRaises(ContractError):
                extract_image("scan.png", png())


if __name__ == "__main__":
    unittest.main()
