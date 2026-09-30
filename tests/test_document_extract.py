import io
import json
import unittest
import zipfile
from unittest.mock import patch

from agentkit.contracts import ContractError
from cockpit.document_extract import extract_document, main
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def archive(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as zf:
        for name, value in files.items():
            zf.writestr(name, value)
    return output.getvalue()


def pdf_bytes(pages=1, marker=None, encrypted=False):
    writer = PdfWriter()
    for index in range(pages):
        page = writer.add_blank_page(width=612, height=792)
        if marker is not None and index == 0:
            stream = DecodedStreamObject()
            stream.set_data(b"BT /F1 12 Tf 72 720 Td (" + marker.encode() + b") Tj ET")
            page[NameObject("/Contents")] = writer._add_object(stream)
            page[NameObject("/Resources")] = DictionaryObject({
                NameObject("/Font"): DictionaryObject({
                    NameObject("/F1"): DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
                })
            })
    if encrypted:
        writer.encrypt("fixture-password")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class DocumentExtractTests(unittest.TestCase):
    def test_pdf_text_blank_encrypted_page_and_page_limit(self):
        self.assertIn("fixture-marker", extract_document("x.pdf", pdf_bytes(marker="fixture-marker")))
        with self.assertRaises(ContractError):
            extract_document("x.pdf", pdf_bytes())
        with self.assertRaises(ContractError):
            extract_document("x.pdf", pdf_bytes(encrypted=True))
        with self.assertRaises(ContractError):
            extract_document("x.pdf", pdf_bytes(pages=101))

    def test_pdf_extracted_text_limit(self):
        marker = "x" * 48_001
        with self.assertRaises(ContractError):
            extract_document("x.pdf", pdf_bytes(marker=marker))

    def test_docx_body_and_table(self):
        data = archive({"word/document.xml": """<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body><w:p><w:r><w:t>Hello</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Cell</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>"""})
        self.assertIn("Hello", extract_document("x.docx", data))
        self.assertIn("Cell", extract_document("x.docx", data))

    def test_xlsx_cached_values_and_formula_literal(self):
        data = archive({
            "xl/workbook.xml": "<workbook xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main' xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'><sheets><sheet name='Data' r:id='rId1'/></sheets></workbook>",
            "xl/_rels/workbook.xml.rels": "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'><Relationship Id='rId1' Target='worksheets/sheet1.xml'/></Relationships>",
            "xl/worksheets/sheet1.xml": "<worksheet xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'><sheetData><row><c r='A1'><f>1+1</f><v>2</v></c></row></sheetData></worksheet>",
        })
        text = extract_document("x.xlsx", data)
        self.assertIn("Data!A1: 2 =1+1", text)

    def test_xlsx_inline_shared_index_and_absolute_target(self):
        inline = archive({
            "xl/workbook.xml": "<workbook xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main' xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'><sheets><sheet name='Data' r:id='rId1'/></sheets></workbook>",
            "xl/_rels/workbook.xml.rels": "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'><Relationship Id='rId1' Target='/xl/worksheets/sheet1.xml'/></Relationships>",
            "xl/worksheets/sheet1.xml": "<worksheet xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'><sheetData><row><c r='A1' t='inlineStr'><is><t>Inline</t></is></c></row></sheetData></worksheet>",
        })
        self.assertIn("Inline", extract_document("x.xlsx", inline))
        invalid = inline.replace(b"Inline", b"<v>99</v>")
        with self.assertRaises(ContractError):
            extract_document("x.xlsx", invalid)

    def test_pptx_order_and_rejections(self):
        data = archive({
            "ppt/presentation.xml": "<p:presentation xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main' xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'><p:sldIdLst><p:sldId r:id='rId1'/></p:sldIdLst></p:presentation>",
            "ppt/_rels/presentation.xml.rels": "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'><Relationship Id='rId1' Target='slides/slide1.xml'/></Relationships>",
            "ppt/slides/slide1.xml": "<p:sld xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main' xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main'><a:p><a:r><a:t>First</a:t></a:r></a:p><a:p><a:r><a:t> second</a:t></a:r></a:p></p:sld>",
        })
        self.assertIn("First\n second", extract_document("x.pptx", data))
        with self.assertRaises(ContractError):
            extract_document("x.exe", data)
        with self.assertRaises(ContractError):
            extract_document("x.docx", b"bad")

    def test_pptx_presentation_order_and_relationship_security(self):
        files = {
            "ppt/presentation.xml": "<p:presentation xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main' xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'><p:sldIdLst><p:sldId r:id='rId2'/><p:sldId r:id='rId1'/></p:sldIdLst></p:presentation>",
            "ppt/_rels/presentation.xml.rels": "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'><Relationship Id='rId1' Target='slides/slide1.xml'/><Relationship Id='rId2' Target='slides/slide2.xml'/></Relationships>",
            "ppt/slides/slide1.xml": "<p:sld xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main' xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main'><a:p><a:r><a:t>One</a:t></a:r></a:p></p:sld>",
            "ppt/slides/slide2.xml": "<p:sld xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main' xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main'><a:p><a:r><a:t>Two</a:t></a:r></a:p></p:sld>",
        }
        text = extract_document("x.pptx", archive(files))
        self.assertLess(text.index("Two"), text.index("One"))
        external = dict(files)
        external["ppt/_rels/presentation.xml.rels"] = external["ppt/_rels/presentation.xml.rels"].replace("</Relationships>", "<Relationship Id='x' TargetMode='external' Target='https://example.test'/></Relationships>")
        with self.assertRaises(ContractError):
            extract_document("x.pptx", archive(external))

    def test_zip_duplicate_macro_and_compressed_member_limits(self):
        duplicate = io.BytesIO()
        with zipfile.ZipFile(duplicate, "w") as zf:
            zf.writestr("word/document.xml", "a")
            zf.writestr("word/document.xml", "b")
        with self.assertRaises(ContractError):
            extract_document("x.docx", duplicate.getvalue())
        macro = archive({"word/vbaPROJECT.bin": b"macro", "word/document.xml": "<w:document/>"})
        with self.assertRaises(ContractError):
            extract_document("x.docx", macro)
        bomb = io.BytesIO()
        with zipfile.ZipFile(bomb, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("word/document.xml", b"x" * (4 * 1024 * 1024 + 1))
        with self.assertRaises(ContractError):
            extract_document("x.docx", bomb.getvalue())

    def test_limits_and_xml_security(self):
        bad = archive({"word/document.xml": "<!DOCTYPE w:document [<!ENTITY x SYSTEM 'x'>]><w:document/>"})
        with self.assertRaises(ContractError):
            extract_document("x.docx", bad)
        huge = archive({"word/document.xml": "x" * (4 * 1024 * 1024 + 1)})
        with self.assertRaises(ContractError):
            extract_document("x.docx", huge)

    def test_cli_does_not_echo_input(self):
        with patch("sys.stdin", io.TextIOWrapper(io.BytesIO(json.dumps({"name": "x.docx", "content_base64": "%%%"}).encode()))), patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(main(), 1)
            self.assertNotIn("%%%", output.getvalue())


if __name__ == "__main__":
    unittest.main()
