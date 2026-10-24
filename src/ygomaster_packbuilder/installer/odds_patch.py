"""Reversible, comment-preserving insertion of custom odds into YgoMaster's main odds file."""

import hashlib
import json
import re

BEGIN_MARKER = "// YGOMASTER-PACKBUILDER ODDS BEGIN"
END_MARKER = "// YGOMASTER-PACKBUILDER ODDS END"
BLOCK_PATTERN = re.compile(
    r"\r?\n[ \t]*// YGOMASTER-PACKBUILDER ODDS BEGIN\r?\n"
    r".*?\r?\n[ \t]*// YGOMASTER-PACKBUILDER ODDS END\r?\n",
    re.DOTALL,
)

class YgoMasterOddsPatchError(ValueError):
    pass

def _strip_comments(text: str) -> str:
    """Mask JSON comments while preserving strings and character positions."""
    chars = list(text)
    i = 0
    quoted = False
    while i < len(chars):
        if quoted:
            if chars[i] == "\\":
                i += 2
                continue
            if chars[i] == '"':
                quoted = False
            i += 1
            continue
        if chars[i] == '"':
            quoted = True
            i += 1
            continue
        if chars[i:i + 2] == ["/", "/"]:
            end = text.find("\n", i + 2)
            if end < 0:
                end = len(chars)
            for j in range(i, end):
                chars[j] = " "
            i = end
            continue
        if chars[i:i + 2] == ["/", "*"]:
            end = text.find("*/", i + 2)
            if end < 0:
                raise YgoMasterOddsPatchError("Unterminated block comment in ShopPackOdds.json.")
            for j in range(i, end + 2):
                if chars[j] not in "\r\n":
                    chars[j] = " "
            i = end + 2
            continue
        i += 1
    return "".join(chars)

def _json_for_validation(text: str) -> str:
    """Accept YgoMaster's trailing commas only in the validation copy."""
    chars = list(_strip_comments(text))
    quoted = False
    escaped = False
    for index, char in enumerate(chars):
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == ",":
            next_index = index + 1
            while next_index < len(chars) and chars[next_index].isspace():
                next_index += 1
            previous_index = index - 1
            while previous_index >= 0 and chars[previous_index].isspace():
                previous_index -= 1
            if (next_index < len(chars) and chars[next_index] in "}]"
                    and previous_index >= 0 and chars[previous_index] not in "[{:,"):
                chars[index] = " "
    return "".join(chars)

def _read_odds_document(content: bytes) -> tuple[str, str, list]:
    encoding = "utf-8-sig" if content.startswith(b"\xef\xbb\xbf") else "utf-8"
    try:
        text = content.decode(encoding)
        data = json.loads(_json_for_validation(text))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise YgoMasterOddsPatchError(f"Invalid main ShopPackOdds.json: {exc}") from exc
    if not isinstance(data, list):
        raise YgoMasterOddsPatchError("ShopPackOdds.json root must be a JSON array.")
    return text, encoding, data

def _remove_managed_block(text: str, expected_sha256: str) -> str:
    blocks = list(BLOCK_PATTERN.finditer(text))
    if len(blocks) != 1 or text.count(BEGIN_MARKER) != 1 or text.count(END_MARKER) != 1:
        raise YgoMasterOddsPatchError("Cannot locate a unique PackBuilder odds block; refusing to alter ShopPackOdds.json.")
    block = blocks[0]
    if hashlib.sha256(block.group().encode("utf-8")).hexdigest() != expected_sha256:
        raise YgoMasterOddsPatchError("PackBuilder odds block was modified after installation; refusing to overwrite it.")
    return text[:block.start()] + text[block.end():]

def patch_main_odds_file(original: bytes, new_entries: list[dict], installed_sha256: str | None = None) -> tuple[bytes, str]:
    text, encoding, _ = _read_odds_document(original)
    if installed_sha256 is not None:
        text = _remove_managed_block(text, installed_sha256)
    elif BEGIN_MARKER in text or END_MARKER in text:
        raise YgoMasterOddsPatchError("Existing PackBuilder odds block without installation state; refusing to overwrite it.")
    _, _, base_entries = _read_odds_document(text.encode(encoding))
    if not new_entries or any(not isinstance(entry, dict) for entry in new_entries):
        raise YgoMasterOddsPatchError("Generated odds must be a nonempty list of objects.")
    original_ids = {int(shop_id) for entry in base_entries if isinstance(entry, dict)
                    for shop_id in entry.get("packShopIds", [])}
    new_ids = [int(shop_id) for entry in new_entries for shop_id in entry.get("packShopIds", [])]
    if len(new_ids) != len(set(new_ids)) or original_ids.intersection(new_ids):
        raise YgoMasterOddsPatchError("PackBuilder shop IDs conflict with existing ShopPackOdds entries.")
    mask = _strip_comments(text)
    open_index = next((i for i, char in enumerate(mask) if not char.isspace()), -1)
    if open_index < 0 or mask[open_index] != "[":
        raise YgoMasterOddsPatchError("Cannot locate ShopPackOdds root array.")
    newline = "\r\n" if "\r\n" in text else "\n"
    serialized = json.dumps(new_entries, indent=2, ensure_ascii=False)[1:-1].strip()
    serialized = serialized.replace("\n", newline)
    block = (
        f"{newline}  {BEGIN_MARKER}{newline}"
        f"{serialized}{',' if base_entries else ''}{newline}"
        f"  {END_MARKER}{newline}"
    )
    patched = text[:open_index + 1] + block + text[open_index + 1:]
    _read_odds_document(patched.encode(encoding))
    return patched.encode(encoding), hashlib.sha256(block.encode("utf-8")).hexdigest()

def restore_main_odds_file(installed: bytes, installed_sha256: str) -> bytes:
    text, encoding, _ = _read_odds_document(installed)
    restored = _remove_managed_block(text, installed_sha256)
    _read_odds_document(restored.encode(encoding))
    return restored.encode(encoding)
