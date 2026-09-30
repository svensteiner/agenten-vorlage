"""Bounded, read-only extraction of text from common office documents."""
from __future__ import annotations

import base64
import binascii
import io
import json
import sys
import zipfile
from pathlib import PurePosixPath

try:
    from agentkit.contracts import ContractError
except ImportError:  # CLI can run directly from an isolated working directory.
    class ContractError(ValueError):
        pass

try:
    from pypdf import PdfReader, Configuration
except ImportError:  # pragma: no cover
    PdfReader = None
from defusedxml import ElementTree as ET

_MAX_TEXT = 48_000
_MAX_MEMBER = 4 * 1024 * 1024
_MAX_ZIP = 8 * 1024 * 1024
_MAX_MEMBERS = 256
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def _finish(parts: list[str]) -> str:
    text = "\n".join(part.strip() for part in parts if part and part.strip())
    if len(text) > _MAX_TEXT:
        raise ContractError("Extracted document text exceeds the 48,000 character limit.")
    return text


def _safe_zip(data: bytes) -> zipfile.ZipFile:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        infos = archive.infolist()
        if len({i.filename for i in infos}) != len(infos):
            archive.close()
            raise ContractError("Document archive contains duplicate members.")
        if len(infos) > _MAX_MEMBERS or any(i.file_size > _MAX_MEMBER for i in infos) or sum(i.file_size for i in infos) > _MAX_ZIP:
            archive.close()
            raise ContractError("Document archive exceeds extraction limits.")
        for info in infos:
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in info.filename:
                archive.close()
                raise ContractError("Document archive contains an unsafe path.")
            if info.flag_bits & 0x1:
                archive.close()
                raise ContractError("Encrypted document members are not supported.")
            if "vbaproject" in info.filename.lower():
                archive.close()
                raise ContractError("Macros are not supported.")
        return archive
    except ContractError:
        raise
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        raise ContractError("Malformed document archive.") from exc


def _xml(archive: zipfile.ZipFile, name: str):
    try:
        with archive.open(name) as member:
            raw = member.read(_MAX_MEMBER + 1)
        if len(raw) > _MAX_MEMBER:
            raise ContractError("Document member exceeds extraction limits.")
        if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
            raise ContractError("Document XML contains forbidden entities.")
        return ET.fromstring(raw, forbid_dtd=True, forbid_entities=True)
    except ContractError:
        raise
    except Exception as exc:
        raise ContractError("Malformed document XML.") from exc


def _external_relationships(archive: zipfile.ZipFile, name: str) -> bool:
    root = _xml(archive, name)
    for rel in root:
        if rel.attrib.get("TargetMode", "").casefold() == "external":
            return True
    return False


def _docx(archive: zipfile.ZipFile) -> str:
    if "word/document.xml" not in archive.namelist():
        raise ContractError("DOCX main document is missing.")
    for name in archive.namelist():
        if name.endswith(".rels") and _external_relationships(archive, name):
            raise ContractError("Macros and external relationships are not supported.")
    root = _xml(archive, "word/document.xml")
    parts = []
    for node in root.findall(".//" + _W + "body/*"):
        if node.tag == _W + "p":
            parts.append("".join(t.text or "" for t in node.findall(".//" + _W + "t")))
        elif node.tag == _W + "tbl":
            for row in node.findall(".//" + _W + "tr"):
                parts.append(" | ".join("".join(t.text or "" for t in cell.findall(".//" + _W + "t")) for cell in row.findall("./" + _W + "tc")))
    return _finish(parts)


def _xlsx(archive: zipfile.ZipFile) -> str:
    names = set(archive.namelist())
    if "xl/workbook.xml" not in names:
        raise ContractError("XLSX workbook is missing.")
    if any(n.endswith(".rels") and _external_relationships(archive, n) for n in names):
        raise ContractError("Macros and external relationships are not supported.")
    shared = []
    if "xl/sharedStrings.xml" in names:
        root = _xml(archive, "xl/sharedStrings.xml")
        shared = ["".join(t.text or "" for t in si.findall(".//" + _S + "t")) for si in root.findall("./" + _S + "si")]
    workbook = _xml(archive, "xl/workbook.xml")
    relroot = _xml(archive, "xl/_rels/workbook.xml.rels") if "xl/_rels/workbook.xml.rels" in names else None
    rels = {r.attrib.get("Id"): r.attrib.get("Target", "") for r in relroot} if relroot is not None else {}
    parts = []
    for sheet in workbook.findall(".//" + _S + "sheet"):
        title = sheet.attrib.get("name", "")
        target = rels.get(sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"), "")
        path = target.lstrip("/")
        if not path.startswith("xl/"):
            path = "xl/" + path
        if path not in names:
            raise ContractError("XLSX worksheet is missing.")
        parts.append(title)
        root = _xml(archive, path)
        for cell in root.findall(".//" + _S + "c"):
            value = cell.find("./" + _S + "v")
            formula = cell.find("./" + _S + "f")
            text = ""
            if value is not None and value.text is not None:
                if cell.attrib.get("t") == "s":
                    index = int(value.text)
                    if index < 0 or index >= len(shared):
                        raise ContractError("XLSX shared string index is invalid.")
                    text = shared[index]
                else:
                    text = value.text
            elif cell.attrib.get("t") == "inlineStr":
                text = "".join(t.text or "" for t in cell.findall(".//" + _S + "t"))
            if formula is not None and formula.text:
                text = (text + " " if text else "") + "=" + formula.text
            if text:
                parts.append(f"{title}!{cell.attrib.get('r', '')}: {text}")
    return _finish(parts)


def _pptx(archive: zipfile.ZipFile) -> str:
    names = set(archive.namelist())
    if "ppt/presentation.xml" not in names or "ppt/_rels/presentation.xml.rels" not in names:
        raise ContractError("PPTX contains no slides.")
    if any(n.endswith(".rels") and _external_relationships(archive, n) for n in names):
        raise ContractError("Macros and external relationships are not supported.")
    presentation = _xml(archive, "ppt/presentation.xml")
    relationships = _xml(archive, "ppt/_rels/presentation.xml.rels")
    targets = {rel.attrib.get("Id"): rel.attrib.get("Target", "") for rel in relationships}
    slides = []
    for slide_id in presentation.findall(".//{http://schemas.openxmlformats.org/presentationml/2006/main}sldId"):
        rel_id = slide_id.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        target = targets.get(rel_id, "")
        path = target.lstrip("/")
        if not path.startswith("ppt/"):
            path = "ppt/" + path
        if path not in names:
            raise ContractError("PPTX slide is missing.")
        slides.append(path)
    parts = []
    for number, name in enumerate(slides, 1):
        root = _xml(archive, name)
        text = "\n".join("".join(t.text or "" for t in paragraph.findall(".//" + _A + "t")) for paragraph in root.findall(".//" + _A + "p"))
        if text.strip():
            parts.append(f"Slide {number}\n{text}")
    return _finish(parts)


def extract_document(name: str, data: bytes) -> str:
    if not isinstance(name, str) or not isinstance(data, bytes):
        raise ContractError("Document name and bytes are required.")
    if len(data) > 2 * 1024 * 1024:
        raise ContractError("Document input exceeds the 2 MiB limit.")
    extension = name.lower().rsplit(".", 1)[-1] if "." in name else ""
    try:
        if extension == "pdf":
            if PdfReader is None:
                raise ContractError("PDF extraction is unavailable.")
            Configuration.zlib_maximum_output_length = 4 * 1024 * 1024
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise ContractError("Encrypted PDFs are not supported.")
            if len(reader.pages) > 100:
                raise ContractError("PDF exceeds the 100 page limit.")
            parts = []
            stream_size = 0
            actual_text = []
            for page_number, page in enumerate(reader.pages, 1):
                contents = page.get_contents()
                if contents is not None:
                    stream_size += sum(len(obj.get_data()) for obj in contents) if isinstance(contents, list) else len(contents.get_data())
                if stream_size > 4 * 1024 * 1024:
                    raise ContractError("PDF content streams exceed the limit.")
                page_text = page.extract_text() or ""
                actual_text.append(page_text)
                parts.append(page_text or (f"[Page {page_number} contains no extractable text]" if len(reader.pages) > 1 else ""))
            result = _finish(parts)
            if not any(text.strip() for text in actual_text):
                raise ContractError("PDF contains no extractable text.")
            return result
        archive = _safe_zip(data)
        try:
            if extension == "docx":
                return _docx(archive)
            if extension == "xlsx":
                return _xlsx(archive)
            if extension == "pptx":
                return _pptx(archive)
            raise ContractError("Unsupported document format.")
        finally:
            archive.close()
    except ContractError:
        raise
    except Exception as exc:
        raise ContractError("Malformed document.") from exc


def main() -> int:
    try:
        # 2 MiB decoded content expands to roughly 2.8 MiB of base64 JSON.
        raw = sys.stdin.buffer.read(3 * 1024 * 1024 + 1)
        if len(raw) > 3 * 1024 * 1024:
            raise ContractError("Input is too large.")
        request = json.loads(raw.decode("utf-8"))
        encoded = request.get("content_base64") if isinstance(request, dict) else None
        name = request.get("name") if isinstance(request, dict) else None
        if not isinstance(encoded, str) or not isinstance(name, str):
            raise ContractError("name and content_base64 are required.")
        data = base64.b64decode(encoded, validate=True)
        output = json.dumps({"text": extract_document(name, data)}, ensure_ascii=False).encode("utf-8") + b"\n"
        sys.stdout.buffer.write(output)
    except (ContractError, ValueError, TypeError, UnicodeError, binascii.Error):
        print(json.dumps({"error": "document extraction failed"}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
