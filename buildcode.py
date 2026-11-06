"""Tách code build súng Delta Force ra khỏi nội dung tin nhắn."""
import re
import unicodedata
from dataclasses import dataclass

# Định dạng khi share từ game: "<Tên súng>-<Chế độ>-<Code>"
# vd: "CI-19 Assault Rifle-Warfare-6HNEL2G0EIPHRNLI0J8JI"
#     "K437 Assault Rifle-Chiến Dịch (Thoát Hiểm)-6LFHT2C0AHP1JR9CHG3OI"
# Tên súng có thể chứa dấu "-" (CI-19, SR-25) nên tách từ phải sang.
SHARE_RE = re.compile(r"(?P<weapon>[^\n`]+?)-(?P<mode>[^\n`\-]+)-(?P<code>[0-9A-Z]{15,30})\b")

# Code đứng trơ trọi: chuỗi in hoa + số, có cả chữ lẫn số.
BARE_RE = re.compile(r"\b(?=[0-9A-Z]*\d)(?=[0-9A-Z]*[A-Z])[0-9A-Z]{18,26}\b")


@dataclass
class Build:
    code: str
    weapon: str | None
    mode: str | None
    note: str | None = None  # dòng ghi chú ngay trên code, vd "K437 full", "eco"
    context: str | None = None  # cả tin nhắn, chỉ dùng khi code không có tên súng lẫn ghi chú

    def search_text(self) -> str:
        # Nối bằng "|" để "...Thoát Hiểm" + "K416" không thành "...mk416"
        return "|".join(normalize(x) for x in (self.weapon, self.mode, self.note, self.context) if x)


def normalize(text: str) -> str:
    """'K437 Assault Rifle' -> 'k437assaultrifle', bỏ dấu tiếng Việt."""
    text = unicodedata.normalize("NFKD", text.casefold()).replace("đ", "d")
    return "".join(c for c in text if c.isalnum())


def _clean(text: str) -> str:
    return text.strip(" \t*_`>:-|")


def extract_builds(content: str) -> list[Build]:
    builds: list[Build] = []
    seen: set[str] = set()
    note = None  # dòng gần nhất không chứa code
    for line in content.splitlines():
        found: list[Build] = []
        for m in SHARE_RE.finditer(line):
            # Phần chữ dẫn trước tên súng, vd "build ngon nè: K437 ..."
            *lead, weapon = re.split(r"[:：>|]\s*", m["weapon"].strip())
            found.append(Build(m["code"], weapon.strip() or None, m["mode"].strip(), _clean(" ".join(lead)) or None))
        share_codes = {b.code for b in found}
        for m in BARE_RE.finditer(line):
            if m[0] not in share_codes:
                found.append(Build(m[0], None, None, _clean(line.replace(m[0], "")) or None))
        if not found:
            note = _clean(line) or note
            continue
        for b in found:
            if b.code in seen:
                continue
            seen.add(b.code)
            b.note = b.note or note
            builds.append(b)
        note = None
    # Code trơ trọi không có ghi chú gì -> đành tìm theo cả tin nhắn
    for b in builds:
        if not b.weapon and not b.note:
            b.context = content.replace(b.code, " ")
    return builds
