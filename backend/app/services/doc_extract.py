"""입찰 첨부파일(hwp / hwpx / pdf) 텍스트 추출.

외부 프로그램 없이 순수 Python. pyhwp는 유지보수 중단 + 무출력 문제로 쓰지 않고
HWP 5.0 공개 스펙대로 BodyText 문단 레코드를 직접 읽는다.
"""

from __future__ import annotations

import io
import re
import struct
import zipfile
import zlib
import xml.etree.ElementTree as ET

import olefile
from pypdf import PdfReader

SUPPORTED_EXTS = ("hwp", "hwpx", "pdf")


class UnsupportedDocument(Exception):
    """배포용(편집 제한)·암호 hwp 등 읽을 수 없는 문서."""


def ext_of(name: str | None) -> str:
    if not name or "." not in name:
        return ""
    return name.rsplit(".", 1)[1].strip().lower()


def extract_text(data: bytes, ext: str) -> str:
    if ext == "hwp":
        return extract_hwp(data)
    if ext == "hwpx":
        return extract_hwpx(data)
    if ext == "pdf":
        return extract_pdf(data)
    raise ValueError(f"unsupported ext: {ext}")


# ----- PDF -----

def extract_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return _clean("\n".join((pg.extract_text() or "") for pg in reader.pages))


# ----- HWPX (OWPML, zip + xml) -----

_HP = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"


def extract_hwpx(data: bytes) -> str:
    out: list[str] = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = sorted(
            n for n in z.namelist() if re.fullmatch(r"Contents/section\d+\.xml", n)
        )
        for n in names:
            root = ET.fromstring(z.read(n))
            # 표 셀 안 문단은 바깥 문단에 중첩됨 → 각 hp:t를 가장 가까운 hp:p에만 귀속시켜 중복 방지
            parent = {c: p for p in root.iter() for c in p}
            para_text: dict[ET.Element, list[str]] = {}
            order: list[ET.Element] = []
            for t in root.iter(f"{_HP}t"):
                p = parent.get(t)
                while p is not None and p.tag != f"{_HP}p":
                    p = parent.get(p)
                if p is None:
                    continue
                if p not in para_text:
                    para_text[p] = []
                    order.append(p)
                para_text[p].append(t.text or "")
            for p in order:
                s = "".join(para_text[p]).strip()
                if s:
                    out.append(s)
    return _clean("\n".join(out))


# ----- HWP 5.0 (OLE compound) -----

_HWPTAG_PARA_TEXT = 67  # HWPTAG_BEGIN(16) + 51
# 문단 텍스트 제어문자(코드 < 32) 중 1 wchar만 차지하는 문자형: 0, 줄바꿈(10), 문단끝(13), 24~31.
# 나머지(확장/인라인 컨트롤: 필드·표·탭 등)는 ch + 12바이트 + ch = 8 wchar 블록.
_CTRL_1WCHAR = {0, 10, 13, 24, 25, 26, 27, 28, 29, 30, 31}


def extract_hwp(data: bytes) -> str:
    ole = olefile.OleFileIO(io.BytesIO(data))
    fh = ole.openstream("FileHeader").read()
    if not fh.startswith(b"HWP Document File"):
        raise UnsupportedDocument("not an HWP 5.0 file")
    flags = struct.unpack("<I", fh[36:40])[0]
    if flags & 0x02:
        raise UnsupportedDocument("password protected")
    if flags & 0x04:
        raise UnsupportedDocument("distribution (배포용) document")
    compressed = bool(flags & 0x01)

    sections = sorted(
        (e for e in ole.listdir() if len(e) == 2 and e[0] == "BodyText"),
        key=lambda e: int(re.sub(r"\D", "", e[1]) or 0),
    )
    out: list[str] = []
    for entry in sections:
        body = ole.openstream(entry).read()
        if compressed:
            body = zlib.decompress(body, -15)
        for tag, payload in _iter_records(body):
            if tag != _HWPTAG_PARA_TEXT:
                continue
            s = _para_text(payload)
            if s:
                out.append(s)
    return _clean("\n".join(out))


def _iter_records(buf: bytes):
    i, n = 0, len(buf)
    while i + 4 <= n:
        hdr = struct.unpack_from("<I", buf, i)[0]
        i += 4
        tag = hdr & 0x3FF
        size = (hdr >> 20) & 0xFFF
        if size == 0xFFF:
            size = struct.unpack_from("<I", buf, i)[0]
            i += 4
        yield tag, buf[i : i + size]
        i += size


def _para_text(payload: bytes) -> str:
    s = payload.decode("utf-16le", "ignore")
    buf: list[str] = []
    j = 0
    while j < len(s):
        c = ord(s[j])
        if c < 32:
            if c in _CTRL_1WCHAR:
                if c in (10, 13):
                    buf.append("\n")
                elif c in (30, 31):
                    buf.append(" ")
                j += 1
            else:
                if c == 9:
                    buf.append("\t")
                j += 8
            continue
        buf.append(s[j])
        j += 1
    return "".join(buf).strip()


# ----- 공통 -----

def _clean(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[-]", "•", text)  # Wingdings/Symbol 글머리표(PUA) → 불릿
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in text.splitlines()]
    return "\n".join(l for l in lines if l)
