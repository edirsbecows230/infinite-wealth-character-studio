#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Y8 Ichiban Character Replacer - offline SRMM mod generator (READ-ONLY on originals).

Replaces Ichiban's 3D Character Identity (model/voice) with any target
Character Row by re-pointing three verified context lookup keys in
character_character_data.bin's row-mapping array:

    12514  -> party detail + battle
    22804  -> free roam + main menu overview
    15286  -> title screen

Two output modes:

  --mode mapping  (default, v1)
    Only the mapping entries are patched (4 bytes each). No table structure
    changes. Covers the three verified default-costume contexts.

  --mode forced   (v2, Forced Identity)
    v1 mapping PLUS character_costume.bin identity override: every costume
    row of Ichiban's player slot (kasuga, player=4) has its character /
    character_hawaii columns re-pointed to the target character, so EVERY
    outfit context (job, swimwear, t-shirts, DLC, default) resolves to the
    target without unlocking the in-game costume UI. Costume rows of other
    party members are untouched. This mirrors the native Skin mechanism
    (character_costume -> *character key) at the base-table level.

    Variant alignment (model-name based):
      swim / tshirt -> target's own swim / tshirt rows, ordinal by costume id;
      job -> target's own job outfits, paired by job-number groups (kasuga
      group k -> target group k, variant order preserved); groups without a
      target counterpart use --job-outfit-char (default: base identity keys);
      special (DLC/story) -> exact row-name token match first (michio /
      robomichio / casino), then cyclic fill from the target's special pool;
      everything else -> target's base identity keys.

The generated mod only patches the mapping entries (4 bytes each). It does
NOT insert/delete rows, does NOT touch the wrapper/sorted-key table, and does
NOT modify skills/moveset/job/weapon/battle params/UI portraits. Costume
stays under the game's own job/costume system.

Usage:
  python y8_character_replacer.py --list-targets
  python y8_character_replacer.py --target-row 9989 --name Play_as_Chitose
  python y8_character_replacer.py --target-char 23404
  python y8_character_replacer.py --target-model chitose
  python y8_character_replacer.py --presets --outdir <dir>
  python y8_character_replacer.py --target-row 9989 --update-ml
  python y8_character_replacer.py --target-char 23404 --mode forced --name Play_as_Chitose_v2
  python y8_character_replacer.py --target-char 23404 --mode forced --keys all

Options:
  --target-row N      original absolute character_character_data row
  --target-char N     *character id (looked up in the original table)
  --target-model S    model name substring (matched via adv_model_id)
  --keys A,B,C|all    identity keys to redirect (default 12514,22804,15286;
                      'all' = every face_target=ichiban main_chara=1 key)
  --mode MODE         mapping (v1, default) or forced (v2 Forced Identity)
  --job-outfit-char N special *character key used for ALL job costume rows in
                      forced mode (default: target base identity keys)
  --portraits         also swap Ichiban's 2D portraits (battle/result/darts/
                      bond/profile/sujimon) with the target's, copied from
                      ui.elvis.common.par (language-neutral, no text)
  --name NAME         SRMM mod directory name
  --outdir DIR        output mod root (default: game runtime/media/mods)
  --update-ml         also append/update ModList.ml (enables this mod)
  --list-targets      print playable-character database and exit
  --presets           generate Chitose/Yamai/Saeko/Seonhee presets
"""

import argparse
import io
import os
import re
import shutil
import struct
import sys

try:
    from y8_par_extract import sllz2_decompress
except Exception:
    sllz2_decompress = None


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG_DIR = os.path.join(PROJECT_ROOT, "local", "game_data", "extracted_full")
CHAR_BIN = os.path.join(ORIG_DIR, "character_character_data.bin")
MODEL_BIN = os.path.join(ORIG_DIR, "character_model_model_data.bin")
COSTUME_BIN = os.path.join(ORIG_DIR, "character_costume.bin")
RPG_COSTUME_BIN = os.path.join(ORIG_DIR, "rpg_costume.bin")
DEFAULT_MODS = os.path.join(PROJECT_ROOT, "local", "generated_mods")
ML_PATH = os.path.join(DEFAULT_MODS, "..", "ModList.ml")
UI_PAR = os.path.join(PROJECT_ROOT, "local", "ui.elvis.common.par")

# Per-character portrait texture families (ui.elvis.common.par). The source
# files are Ichiban's; for each family the target's files are mapped by
# ordinal (cyclic when the target has fewer variants).
PORTRAIT_FAMILIES = (
    "btl_main_chara_", "btl_result_chara_elv_", "btl_result_chara_",
    "mg_darts_chara_", "kizuna_cutin_", "profile_", "p_talk_exp_cutin_",
    "sujimon_name_", "sujimon_katagaki_",
)
CHAR_TOKENS = {
    "ichiban": ("ichiban", "kasuga"),
    "chitose": ("chitose", "chito"),
    "saeko": ("saeko",),
    "sonhi": ("sonhi",),
    "nanba": ("nanba",),
    "adachi": ("adachi",),
    "chou": ("chou", "cho"),
    "jyungi": ("jyungi", "jyun"),
    "kiryu": ("kiryu",),
    "tomizawa": ("tomizawa", "tomi"),
}

# Verified row-mapping array in the ORIGINAL character_character_data.bin:
# one u32 per sorted-key slot -> first-occurrence table row.
MAPPING_OFF = 0x50DE8

# Verified v1 identity keys (context -> key).
DEFAULT_KEYS = (12514, 22804, 15286)

# party.bin: kasuga -> player_id 4. All Forced-Identity costume overrides
# apply to this slot only; other party members keep their own rows.
KASUGA_SLOT = 4

# Native-skin reference pairs (character, character_hawaii) taken from the
# Playable Character Skins analysis. Forced Identity uses these as the
# target's base identity keys wherever no matching variant costume exists.
SKIN_BASE_KEYS = {
    "kiryu": (23350, 23350),
    "ichiban": (15286, 22804),
    "nanba": (15637, 22815),
    "adachi": (16291, 25154),
    "chou": (15583, 25880),
    "jyungi": (54, 25840),
    "tomizawa": (26422, 23393),
    "saeko": (6192, 26295),
    "sonhi": (16402, 25841),
    "chitose": (18935, 23404),
}

JOB_NUM_RE = re.compile(r"job_(\d+)")

# Row-name tokens used for semantic "special outfit" alignment. Exact token
# matches (kasuga row -> target row with the same token) win first; the
# remaining kasuga special rows cycle through the target's special pool.
SPECIAL_TOKENS = ("robomichio", "michio", "casino", "spy", "sonhi", "haruka")


def special_token(row_name):
    n = (row_name or "").lower()
    for tok in SPECIAL_TOKENS:
        if tok in n:
            return tok
    return None


def read_cstr(buf, off, limit=0x1000):
    end = buf.find(b"\x00", off)
    if end < 0 or end - off > limit:
        return None
    s = buf[off:end]
    try:
        return s.decode("ascii")
    except UnicodeDecodeError:
        return None


def parse_armp(buf):
    """Parse ARMP v2 table; returns row/col info + decoded columns."""
    if buf[0:4] != b"armp":
        raise ValueError("not an armp file")
    version = int.from_bytes(buf[0x0A:0x0C], "little")
    if version != 2:
        raise ValueError("not ARMP v2 (version=%d)" % version)
    hdr_size = int.from_bytes(buf[0x10:0x14], "little")
    if hdr_size == 0x20:
        inner = 0
        row_count = int.from_bytes(buf[0x20:0x24], "little")
        col_count = int.from_bytes(buf[0x24:0x28], "little")
        text_count = int.from_bytes(buf[0x28:0x2C], "little")
        types_off = int.from_bytes(buf[0x38:0x3C], "little")
        offset_table_off = int.from_bytes(buf[0x3C:0x40], "little")
        col_name_ptrs_off = int.from_bytes(buf[0x48:0x4C], "little")
    else:
        inner = hdr_size
        row_count = int.from_bytes(buf[inner + 0x00:inner + 0x04], "little")
        col_count = int.from_bytes(buf[inner + 0x04:inner + 0x08], "little")
        text_count = int.from_bytes(buf[inner + 0x08:inner + 0x0C], "little")
        types_off = int.from_bytes(buf[inner + 0x18:inner + 0x1C], "little")
        offset_table_off = int.from_bytes(buf[inner + 0x1C:inner + 0x20], "little")
        col_name_ptrs_off = int.from_bytes(buf[inner + 0x28:inner + 0x2C], "little")

    col_names = []
    if col_name_ptrs_off:
        for i in range(col_count):
            p = int.from_bytes(buf[col_name_ptrs_off + 4 * i:col_name_ptrs_off + 4 * i + 4], "little")
            col_names.append(read_cstr(buf, p) or "")
    else:
        col_names = [""] * col_count

    col_types = [buf[types_off + i] if types_off + i < len(buf) else -1 for i in range(col_count)]

    offsets = []
    if offset_table_off:
        for i in range(col_count):
            offsets.append(int.from_bytes(buf[offset_table_off + 4 * i:offset_table_off + 4 * i + 4], "little"))
    else:
        offsets = [0] * col_count

    pool = _extract_pool(buf, col_name_ptrs_off, types_off, col_count, text_count, offsets)
    columns = {}
    for ci, name in enumerate(col_names):
        off = offsets[ci]
        t = col_types[ci]
        if off == 0 or off >= len(buf):
            columns[name] = None
        elif t == 6:
            columns[name] = ("bitmask", off, (row_count + 7) // 8)
        elif t == 13:
            columns[name] = ("u32idx", off, row_count * 4)
        elif t == 1:
            columns[name] = ("u16", off, row_count * 2)
        else:
            columns[name] = ("u16", off, row_count * 2)

    return {
        "row_count": row_count,
        "col_count": col_count,
        "col_names": col_names,
        "col_types": col_types,
        "offsets": offsets,
        "columns": columns,
        "pool": pool,
    }


def _extract_pool(buf, col_ptrs_off, types_off, col_count, text_count, offsets):
    if text_count <= 0:
        return {}
    lo = col_ptrs_off + 4 * col_count if col_ptrs_off else types_off
    hi = 0
    for off in offsets:
        if off and off > lo:
            hi = min(hi, off) if hi else off
    if hi <= lo or hi - lo > 0x8000:
        hi = min(len(buf), lo + 0x8000)
    region = buf[lo:hi]
    best = None
    best_len = 0
    i = 0
    n = len(region)
    while i < n:
        while i < n and region[i] == 0:
            i += 1
        if i >= n:
            break
        strings = []
        k = i
        while k < n and len(strings) < text_count + 1:
            end = region.find(b"\x00", k)
            if end < 0 or end >= n:
                break
            s = region[k:end]
            if not s or not all(0x20 <= c < 0x7F for c in s):
                break
            strings.append(s.decode("ascii"))
            k = end + 1
        if len(strings) > best_len:
            best = strings
            best_len = len(strings)
        if best_len >= text_count:
            break
        i = k if k > i + 1 else i + 1
    pool = {}
    if best:
        for n, s in enumerate(best, start=1):
            pool[n] = s
    return pool


class Table:
    def __init__(self, path):
        with io.open(path, "rb") as f:
            self.buf = f.read()
        self.info = parse_armp(self.buf)

    def val(self, row, colname):
        col = self.info["columns"].get(colname)
        if col is None:
            return None
        kind, off, size = col
        buf = self.buf
        if kind == "bitmask":
            return (buf[off + row // 8] >> (row % 8)) & 1
        if kind == "u16":
            return int.from_bytes(buf[off + row * 2:off + row * 2 + 2], "little")
        if kind == "u32idx":
            idx = int.from_bytes(buf[off + row * 4:off + row * 4 + 4], "little")
            return self.info["pool"].get(idx, "") if idx else ""
        return None

    @property
    def row_count(self):
        return self.info["row_count"]


def load_char():
    return Table(CHAR_BIN)


def load_model():
    return Table(MODEL_BIN)


def build_key_pos_map(char):
    """Rebuild sorted-key slot -> key value from the mapping array + table rows."""
    buf = char.buf
    n = char.row_count
    key_pos = {}
    for pos in range(n):
        off = MAPPING_OFF + pos * 4
        if off + 4 > len(buf):
            break
        row = struct.unpack_from("<I", buf, off)[0]
        if row >= n:
            continue
        key = char.val(row, "*character")
        if key is not None and key not in key_pos:
            key_pos[key] = pos
    return key_pos


def model_name_for_adv(adv):
    """Return (model_row, face, hair, tops) for an adv_model_id, or None."""
    m = load_model()
    for r in range(m.row_count):
        if m.val(r, "*model") == adv:
            return (r, m.val(r, "face_model"), m.val(r, "hair_model"), m.val(r, "tops_model"))
    return None


def describe_row(char, row):
    ch = char.val(row, "*character")
    adv = char.val(row, "adv_model_id")
    ft = char.val(row, "face_target")
    vc = char.val(row, "voicer")
    mc = char.val(row, "main_chara")
    mm = model_name_for_adv(adv) if adv else None
    return {
        "row": row,
        "character": ch,
        "adv_model_id": adv,
        "model_row": mm[0] if mm else None,
        "model": mm[3] if mm else None,
        "face_target": ft,
        "main_chara": mc,
        "voicer": vc,
    }


def parse_row_names(buf):
    """ARMP v2 row names: offset table at table_base+0x10, entries are
    absolute file offsets of NUL-terminated strings."""
    if buf[0:4] != b"armp":
        return {}
    version = int.from_bytes(buf[0x0A:0x0C], "little")
    if version != 2:
        return {}
    hdr_size = int.from_bytes(buf[0x10:0x14], "little")
    base = 0x20 if hdr_size == 0x20 else hdr_size
    row_count = int.from_bytes(buf[base:base + 4], "little")
    ptr = int.from_bytes(buf[base + 0x10:base + 0x14], "little")
    names = []
    if ptr and ptr + 4 * row_count <= len(buf):
        for i in range(row_count):
            off = int.from_bytes(buf[ptr + 4 * i:ptr + 4 * i + 4], "little")
            names.append(read_cstr(buf, off) or "")
    else:
        names = [""] * row_count
    return dict(enumerate(names))


class RowTable:
    """Reader for ARMP v2 STORAGE_MODE=1 (row-major) tables.

    Layout is byte-verified against reARMP output for
    character_costume.bin (539 rows, row stride 16, 0/539 mismatches):
      +0 u16 *player | +2 u16 **costume | +4 u16 character | +6 u16 character_hawaii
    """
    def __init__(self, path, fields):
        with io.open(path, "rb") as f:
            self.buf = f.read()
        buf = self.buf
        hdr_size = struct.unpack_from("<I", buf, 0x10)[0]
        base = 0x20 if hdr_size == 0x20 else hdr_size
        self.row_count = struct.unpack_from("<I", buf, base)[0]
        storage = buf[base + 0x23]
        if storage != 1:
            raise ValueError("RowTable: not STORAGE_MODE=1 (storage=%d)" % storage)
        offtab = struct.unpack_from("<I", buf, base + 0x1C)[0]
        self.row_offsets = [
            struct.unpack_from("<I", buf, offtab + 4 * i)[0]
            for i in range(self.row_count)
        ]
        diffs = [b - a for a, b in zip(self.row_offsets, self.row_offsets[1:]) if b > a]
        self.stride = min(diffs) if diffs else 0
        self.fields = fields

    def val(self, row, colname):
        off, fmt = self.fields[colname]
        return struct.unpack_from("<" + fmt, self.buf, self.row_offsets[row] + off)[0]


# Byte-verified row-major layout of character_costume.bin.
CC_FIELDS = {
    "*player": (0, "H"),
    "**costume": (2, "H"),
    "character": (4, "H"),
    "character_hawaii": (6, "H"),
}


def build_key_model(char):
    """Precompute character key -> tops model name (first occurrence)."""
    m = load_model()
    adv2model = {}
    for r in range(m.row_count):
        adv = m.val(r, "*model")
        if adv is not None and adv not in adv2model:
            adv2model[adv] = m.val(r, "tops_model")
    key_model = {}
    for r in range(char.row_count):
        k = char.val(r, "*character")
        if k is not None and k not in key_model:
            key_model[k] = adv2model.get(char.val(r, "adv_model_id"))
    return key_model


def classify_model(row, cc, key_model):
    """(category, job_num) for a costume row, from the resolved model name.
    swim/tshirt ordinal-match the target's own rows; job rows use a single
    fixed special outfit (not job-bound); everything else falls back to the
    target's base identity keys."""
    for col in ("character", "character_hawaii"):
        ch = cc.val(row, col)
        if not ch:
            continue
        mod = key_model.get(ch)
        if not mod:
            continue
        ml = mod.lower()
        if "swim" in ml:
            return ("swim", None)
        if "tshirts" in ml:
            return ("tshirt", None)
        mm = JOB_NUM_RE.search(ml)
        if mm:
            return ("job", int(mm.group(1)))
        return ("other", None)
    return ("other", None)


def target_costume_profile(char, cc, key_model, target):
    """Resolve the target's player slot, base identity keys and variant
    costume sets. Returns (slot, base_keys, variants).
    variants['swim'/'tshirt'] = [(cst, character, character_hawaii), ...]
    sorted by costume id; variants['job'] = [(job_num, [(cst, ch, hh), ...]),
    ...] sorted by job number with each group sorted by costume id."""
    ft = target["face_target"]
    base = SKIN_BASE_KEYS.get(ft)
    if base is None:
        key = target["character"] or 0
        base = (key, key)
    slot = None
    if ft:
        ft_by_key = {}
        for r in range(char.row_count):
            k = char.val(r, "*character")
            if k is not None and k not in ft_by_key:
                ft_by_key[k] = char.val(r, "face_target")
        votes = {}
        for i in range(cc.row_count):
            pl = cc.val(i, "*player")
            f = ft_by_key.get(cc.val(i, "character"))
            if f:
                votes.setdefault(pl, {})
                votes[pl][f] = votes[pl].get(f, 0) + 1
        best, bestn = None, 0
        for pl, cnt in votes.items():
            n = cnt.get(ft, 0)
            if n > bestn:
                best, bestn = pl, n
        slot = best
    variants = {}
    if slot is not None:
        swim, tshirt, jobs = [], [], {}
        for i in range(cc.row_count):
            if cc.val(i, "*player") != slot:
                continue
            cst = cc.val(i, "**costume")
            cat, num = classify_model(i, cc, key_model)
            ent = (cst, cc.val(i, "character"), cc.val(i, "character_hawaii"))
            if cat == "swim":
                swim.append(ent)
            elif cat == "tshirt":
                tshirt.append(ent)
            elif cat == "job":
                jobs.setdefault(num, []).append(ent)
        swim.sort()
        tshirt.sort()
        variants["swim"] = swim
        variants["tshirt"] = tshirt
        variants["job"] = [(n, sorted(jobs[n])) for n in sorted(jobs)]
    return slot, base, variants


def build_costume_overrides(char, cc, key_model, rpg_names, target, job_outfit=None,
                            source_slot=KASUGA_SLOT, source_name="kasuga"):
    """Compute (row, costume, category, new_char, new_hawaii) for every
    kasuga-slot character_costume row.

    - swim / tshirt rows ordinal-match the target's own rows (by costume id);
    - job rows pair by job-number groups: kasuga group k -> target group k,
      variant ordinal inside the group stays aligned; groups without a target
      counterpart use job_outfit (default: target's base identity keys);
    - special outfit rows (DLC/story) align by row-name token first (michio /
      robomichio / casino etc.), then cycle through the target's own special
      pool so every special context shows a special outfit;
    - everything else falls back to the target's base identity keys.
    """
    slot, base, variants = target_costume_profile(char, cc, key_model, target)
    if job_outfit is None:
        job_outfit = base
    swim_rows, tshirt_rows, job_groups, special_rows = [], [], {}, []
    source_base = SKIN_BASE_KEYS.get(source_name)
    for i in range(cc.row_count):
        if cc.val(i, "*player") != source_slot:
            continue
        cat, num = classify_model(i, cc, key_model)
        if cat == "swim":
            swim_rows.append(i)
        elif cat == "tshirt":
            tshirt_rows.append(i)
        elif cat == "job":
            job_groups.setdefault(num, []).append(i)
        else:
            current_pair = (cc.val(i, "character"), cc.val(i, "character_hawaii"))
            if rpg_names.get(cc.val(i, "**costume"), "") != source_name and \
               current_pair != source_base:
                special_rows.append(i)  # skip the default-outfit row
    swim_rows.sort(key=lambda r: cc.val(r, "**costume"))
    tshirt_rows.sort(key=lambda r: cc.val(r, "**costume"))
    for g in job_groups.values():
        g.sort(key=lambda r: cc.val(r, "**costume"))
    special_rows.sort(key=lambda r: cc.val(r, "**costume"))

    overrides = []
    for cat, rows in (("swim", swim_rows), ("tshirt", tshirt_rows)):
        tgt = variants.get(cat, [])
        for k, row in enumerate(rows):
            nch, nhh = base
            if k < len(tgt):
                _, vch, vhh = tgt[k]
                if vch:
                    nch = vch
                nhh = vhh  # mirror the target's own row (0 = fall back)
            overrides.append((row, cc.val(row, "**costume"), cat, nch, nhh))

    tgt_jobs = variants.get("job", [])
    for k, num in enumerate(sorted(job_groups)):
        nch, nhh = job_outfit
        if k < len(tgt_jobs):
            tg_rows = tgt_jobs[k][1]
            for j, row in enumerate(job_groups[num]):
                if j < len(tg_rows):
                    _, vch, vhh = tg_rows[j]
                    nch, nhh = (vch if vch else job_outfit[0]), vhh
                else:
                    nch, nhh = job_outfit
                overrides.append((row, cc.val(row, "**costume"), "job", nch, nhh))
        else:
            for row in job_groups[num]:
                overrides.append((row, cc.val(row, "**costume"), "job",
                                  nch, nhh))

    # special outfit alignment: exact token match first, then cyclic fill
    if slot is not None:
        tgt_special = []
        ft_name = target["face_target"] or ""
        for i in range(cc.row_count):
            if cc.val(i, "*player") != slot:
                continue
            cst = cc.val(i, "**costume")
            name = rpg_names.get(cst, "")
            base_name = name.replace("_short", "").replace("_amikomi", "")
            if name == ft_name or base_name == ft_name or "fudangi" in name:
                continue  # formal wear is not a special outfit
            cat, _num = classify_model(i, cc, key_model)
            if cat != "other":
                continue
            tgt_special.append((cst, cc.val(i, "character"),
                                cc.val(i, "character_hawaii"),
                                special_token(name)))
        tgt_special.sort()
        used = set()
        for row in special_rows:
            cst = cc.val(row, "**costume")
            tok = special_token(rpg_names.get(cst, ""))
            if tok and "fudangi" not in rpg_names.get(cst, ""):
                for k, (tc, vch, vhh, ttok) in enumerate(tgt_special):
                    if k not in used and ttok == tok:
                        used.add(k)
                        overrides.append((row, cst, "special", vch, vhh))
                        break
        pool = [e for k, e in enumerate(tgt_special) if k not in used]
        unmatched = []
        for row in special_rows:
            cst = cc.val(row, "**costume")
            if any(o[0] == row for o in overrides):
                continue
            if "fudangi" in rpg_names.get(cst, ""):
                continue
            unmatched.append(row)
        for k, row in enumerate(unmatched):
            if not pool:
                break
            _, vch, vhh, _tok = pool[k % len(pool)]
            overrides.append((row, cc.val(row, "**costume"), "special", vch, vhh))

    mapped = {o[0] for o in overrides}
    for i in range(cc.row_count):
        if cc.val(i, "*player") != source_slot or i in mapped:
            continue
        cst = cc.val(i, "**costume")
        nch, nhh = base
        overrides.append((i, cst, "other", nch, nhh))
    return slot, base, overrides


def patch_costume_bin(cc, overrides):
    """Apply the overrides in place and byte-verify that only the expected
    character / character_hawaii u16 cells changed."""
    buf = bytearray(cc.buf)
    off_ch = cc.fields["character"][0]
    off_hh = cc.fields["character_hawaii"][0]
    expected_ranges = []
    for row, cst, cat, nch, nhh in overrides:
        if nch != cc.val(row, "character"):
            struct.pack_into("<H", buf, cc.row_offsets[row] + off_ch, nch)
            expected_ranges.append((cc.row_offsets[row] + off_ch,
                                    cc.row_offsets[row] + off_ch + 1))
        if nhh != cc.val(row, "character_hawaii"):
            struct.pack_into("<H", buf, cc.row_offsets[row] + off_hh, nhh)
            expected_ranges.append((cc.row_offsets[row] + off_hh,
                                    cc.row_offsets[row] + off_hh + 1))
    changed = [o for o in range(len(buf)) if buf[o] != cc.buf[o]]
    covered = set()
    for lo, hi in expected_ranges:
        covered.update(range(lo, hi + 1))
    extra = [hex(o) for o in changed if o not in covered][:10]
    untouched = [hex(lo) for lo, hi in expected_ranges
                 if not any(o in changed for o in range(lo, hi + 1))][:10]
    if extra or untouched:
        missing_chg = untouched
        raise SystemExit("costume self-check failed: extra=%s missing=%s"
                         % (extra, missing_chg))
    return buf


def ichiban_variant_keys(char):
    """All face_target=ichiban main_chara=1 variant keys (file-layer superset)."""
    keys = []
    for r in range(char.row_count):
        if char.val(r, "face_target") == "ichiban" and char.val(r, "main_chara") == 1:
            k = char.val(r, "*character")
            if k is not None:
                keys.append(k)
    return tuple(keys)


def load_par_entries(path):
    """Read only the PARC header + name table + entry table (no payload)."""
    with io.open(path, "rb") as f:
        head = f.read(0x20)
        if head[0:4] != b"PARC":
            raise ValueError("not a PARC file: %s" % path)
        count = int.from_bytes(head[0x18:0x1C], "big")
        ent_off = int.from_bytes(head[0x1C:0x20], "big")
        f.seek(0x60)
        name_blob = f.read(count * 0x40)
        f.seek(ent_off)
        ent_blob = f.read(count * 0x20)
    names = []
    for i in range(count):
        off = i * 0x40
        e = name_blob.find(b"\x00", off)
        names.append(name_blob[off:e].decode("ascii", "replace"))
    entries = {}
    for i in range(count):
        e = ent_blob[i * 0x20:(i + 1) * 0x20]
        flags = int.from_bytes(e[0:4], "big")
        dsize = int.from_bytes(e[4:8], "big")
        csize = int.from_bytes(e[8:12], "big")
        doff = int.from_bytes(e[12:16], "big")
        hsh = int.from_bytes(e[28:32], "big")
        entries[names[i]] = (flags, dsize, csize, doff, hsh)
    return entries


def extract_par_entry(path, entry):
    flags, dsize, csize, doff, hsh = entry
    with io.open(path, "rb") as f:
        f.seek(doff)
        blk = f.read(csize)
    if flags & 0x80000000:
        if sllz2_decompress is None:
            raise SystemExit("sllz2_decompress unavailable (y8_par_extract missing)")
        return sllz2_decompress(blk, dsize)
    return blk[:dsize]


def _suffix_key(name, fam, tokens):
    """Sort key for a portrait file: the variant suffix after the character
    token (numeric suffixes zero-padded), so 'elv_chitose' < 'elv_chito02'
    pairs by variant instead of ASCII name order."""
    for t in sorted(tokens, key=len, reverse=True):
        if name.startswith(fam + t):
            rest = name[len(fam) + len(t):]
            break
    else:
        return None
    if rest.endswith(".dds"):
        rest = rest[:-4]
    rest = rest.lstrip("_")
    if rest.isdigit():
        rest = rest.zfill(4)
    return (rest, name)


def build_portrait_map(entries, face_target):
    """Map each Ichiban portrait file to the target's same-family file.
    Returns [(src_name, tgt_name), ...] ordered by family + variant ordinal."""
    ichi_tokens = CHAR_TOKENS.get("ichiban", ())
    tgt_tokens = CHAR_TOKENS.get(face_target or "", ())
    if not tgt_tokens:
        return []
    mapping = []
    for fam in PORTRAIT_FAMILIES:
        src = [(k, n) for n in entries
               if n.endswith(".dds") and (k := _suffix_key(n, fam, ichi_tokens))]
        tgt = [(k, n) for n in entries
               if n.endswith(".dds") and (k := _suffix_key(n, fam, tgt_tokens))]
        src.sort()
        tgt.sort()
        if not src or not tgt:
            continue
        for k, (_, s) in enumerate(src):
            mapping.append((s, tgt[k % len(tgt)][1]))
    return mapping


def add_portraits(mod_dir, target):
    """Copy the target's portrait DDS files over Ichiban's file names into
    mod_dir/ui.elvis/common/texture/. Verifies DDS dimensions match."""
    entries = load_par_entries(UI_PAR)
    mapping = build_portrait_map(entries, target["face_target"])
    if not mapping:
        print("Portraits: no vanilla portraits for face_target=%s (skipped)"
              % target["face_target"])
        return 0
    tdir = os.path.join(mod_dir, "ui.elvis", "common", "texture")
    os.makedirs(tdir, exist_ok=True)
    done, skipped = 0, 0
    for src, tgt in mapping:
        s = extract_par_entry(UI_PAR, entries[src])
        t = extract_par_entry(UI_PAR, entries[tgt])
        if len(s) >= 20 and len(t) >= 20:
            sh, sw = int.from_bytes(s[12:16], "little"), int.from_bytes(s[16:20], "little")
            th, tw = int.from_bytes(t[12:16], "little"), int.from_bytes(t[16:20], "little")
            if (sh, sw) != (th, tw):
                print("  skip %s <- %s (dims %dx%d vs %dx%d)"
                      % (src, tgt, sw, sh, tw, th))
                skipped += 1
                continue
        with io.open(os.path.join(tdir, src), "wb") as f:
            f.write(t)
        done += 1
    print("Portraits: %d files swapped (ui.elvis/common/texture/), skipped=%d"
          % (done, skipped))
    return done


def find_target(char, args):
    if args.target_row is not None:
        row = args.target_row
        if not 0 <= row < char.row_count:
            raise SystemExit("target row %d out of range (0..%d)" % (row, char.row_count - 1))
        return describe_row(char, row)
    if args.target_char is not None:
        for r in range(char.row_count):
            if char.val(r, "*character") == args.target_char:
                return describe_row(char, r)
        raise SystemExit("no row with *character=%d" % args.target_char)
    if args.target_model:
        hits = []
        m = load_model()
        for mr in range(m.row_count):
            for col in ("tops_model", "face_model", "hair_model"):
                name = m.val(mr, col)
                if name and args.target_model.lower() in name.lower():
                    adv = m.val(mr, "*model")
                    for r in range(char.row_count):
                        if char.val(r, "adv_model_id") == adv:
                            hits.append(describe_row(char, r))
        if not hits:
            raise SystemExit("no character row matches model %r" % args.target_model)
        # prefer main_chara=1
        for h in hits:
            if h["main_chara"] == 1:
                return h
        return hits[0]
    raise SystemExit("one of --target-row / --target-char / --target-model is required")


def build_mod(char, target, keys, name, outdir, update_ml=False, mode="mapping",
              job_outfit=None, portraits=False):
    key_pos = build_key_pos_map(char)
    missing = [k for k in keys if k not in key_pos]
    if missing:
        raise SystemExit("keys not found in mapping: %s" % missing)

    buf = bytearray(char.buf)
    summary = []
    for key in keys:
        pos = key_pos[key]
        off = MAPPING_OFF + pos * 4
        old_row = struct.unpack_from("<I", buf, off)[0]
        struct.pack_into("<I", buf, off, target["row"])
        summary.append((key, pos, old_row, target["row"]))

    # byte-level self check: only the expected u32s changed
    expected = {MAPPING_OFF + key_pos[k] * 4 for k in keys}
    changed = [off for off in range(0, len(buf), 4) if buf[off:off + 4] != char.buf[off:off + 4]]
    if set(changed) != expected:
        extra = [hex(o) for o in changed if o not in expected][:10]
        missing_chg = [hex(o) for o in expected if o not in changed][:10]
        raise SystemExit("self-check failed: extra=%s missing=%s" % (extra, missing_chg))

    mod_dir = os.path.join(outdir, name)
    lang_dir = os.path.join(mod_dir, "db.elvis.zhs")
    os.makedirs(lang_dir, exist_ok=True)
    out_bin = os.path.join(lang_dir, "character_character_data.bin")
    with io.open(out_bin, "wb") as f:
        f.write(buf)

    print("Mod: %s" % name)
    print("Mode: %s" % mode)
    print("Target: row=%d character=%s adv_model_id=%s model=%s face_target=%s main_chara=%s voicer=%s"
          % (target["row"], target["character"], target["adv_model_id"], target["model"],
             target["face_target"], target["main_chara"], target["voicer"]))
    for key, pos, old, new in summary:
        print("  key %-6d slot %-5d mapping %-5d -> %-5d" % (key, pos, old, new))
    print("Changed u32s: %d (exactly expected), rows/wrapper untouched" % len(summary))
    print("Output: %s" % out_bin)

    if mode == "forced":
        cc = RowTable(COSTUME_BIN, CC_FIELDS)
        key_model = build_key_model(char)
        rpg_names = parse_row_names(io.open(RPG_COSTUME_BIN, "rb").read())
        if job_outfit is not None:
            found = any(char.val(r, "*character") == job_outfit
                        for r in range(char.row_count))
            if not found:
                raise SystemExit("--job-outfit-char %d: no such character key"
                                 % job_outfit)
            job_outfit = (job_outfit, job_outfit)
        slot, base, overrides = build_costume_overrides(
            char, cc, key_model, rpg_names, target, job_outfit=job_outfit)
        cbuf = patch_costume_bin(cc, overrides)
        out_cb = os.path.join(lang_dir, "character_costume.bin")
        with io.open(out_cb, "wb") as f:
            f.write(cbuf)
        print("Costume override: player slot %s -> base keys %s" % (slot, base))
        changed_rows = sum(1 for o in overrides
                           if o[3] != cc.val(o[0], "character")
                           or o[4] != cc.val(o[0], "character_hawaii"))
        print("  costume rows overridden: %d / %d kasuga-slot rows (byte-verified)"
              % (changed_rows, len(overrides)))
        for row, cst, cat, nch, nhh in overrides:
            if nch != cc.val(row, "character") or nhh != cc.val(row, "character_hawaii"):
                print("    row %3d costume %3d %-16s char %6d/%6d -> %6d/%6d"
                      % (row, cst, cat, cc.val(row, "character"),
                         cc.val(row, "character_hawaii"), nch, nhh))
        print("Output: %s" % out_cb)

    if portraits:
        print("WARNING: --portraits is currently DISABLED for this game build: "
              "any ui.elvis overlay breaks the character avatar list "
              "(index/directory-enumeration based). See CURRENT_STATE.md.")
        add_portraits(mod_dir, target)

    if update_ml:
        update_mod_list(name, enable=True)
        print("ModList.ml updated (enabled): %s" % name)
    return out_bin


def update_mod_list(name, enable=True):
    """Append/refresh an entry in media/ModList.ml (FF=on, FE=off)."""
    path = os.path.normpath(ML_PATH)
    names = []
    enabled = set()
    if os.path.exists(path):
        data = open(path, "rb").read()
        if data[:8] == b"SRMM_ML" and len(data) >= 12:
            count = struct.unpack_from("<H", data, 10)[0]
            off = 12
            for _ in range(count):
                if off + 3 > len(data):
                    break
                flag = data[off]
                ln = struct.unpack_from("<H", data, off + 1)[0]
                nm = data[off + 3:off + 3 + ln].decode("utf-8", "replace")
                names.append(nm)
                if flag == 0xFF:
                    enabled.add(nm)
                off += 3 + ln
    if name not in names:
        names.append(name)
    if enable:
        enabled.add(name)
    else:
        enabled.discard(name)
    out = bytearray(b"SRMM_ML")
    out += struct.pack("<H", 2)
    out += struct.pack("<H", len(names))
    for nm in names:
        b = nm.encode("utf-8")
        out += bytes([0xFF if nm in enabled else 0xFE])
        out += struct.pack("<H", len(b))
        out += b
    with open(path, "wb") as f:
        f.write(out)


def list_targets():
    char = load_char()
    rows = []
    for r in range(char.row_count):
        ft = char.val(r, "face_target")
        mc = char.val(r, "main_chara")
        if not ft and mc != 1:
            continue
        rows.append(describe_row(char, r))
    rows.sort(key=lambda d: (d["character"] or 0))
    print("%-6s %-8s %-9s %-7s %-26s %-12s %-5s %s"
          % ("row", "char", "adv", "mrow", "model(tops)", "face_target", "main", "voicer"))
    for d in rows:
        print("%-6d %-8s %-9s %-7s %-26s %-12s %-5s %s"
              % (d["row"], d["character"], d["adv_model_id"], d["model_row"], d["model"],
                 d["face_target"], d["main_chara"], d["voicer"]))


def presets(outdir):
    char = load_char()
    known = {
        "Play_as_Chitose": 23404,
        "Play_as_Yamai": 25107,
        "Play_as_Saeko": 12479,
        "Play_as_Seonhee": 16402,
    }
    for name, chid in known.items():
        target = None
        for r in range(char.row_count):
            if char.val(r, "*character") == chid:
                target = describe_row(char, r)
                break
        if target is None:
            print("SKIP %s: character %d not found" % (name, chid))
            continue
        build_mod(char, target, DEFAULT_KEYS, name, outdir)
        print()


def main():
    ap = argparse.ArgumentParser(description="Y8 Ichiban Character Replacer generator")
    ap.add_argument("--list-targets", action="store_true")
    ap.add_argument("--presets", action="store_true")
    ap.add_argument("--target-row", type=int)
    ap.add_argument("--target-char", type=int)
    ap.add_argument("--target-model")
    ap.add_argument("--keys", default=",".join(map(str, DEFAULT_KEYS)))
    ap.add_argument("--mode", default="mapping", choices=("mapping", "forced"))
    ap.add_argument("--job-outfit-char", type=int)
    ap.add_argument("--portraits", action="store_true")
    ap.add_argument("--name")
    ap.add_argument("--outdir", default=DEFAULT_MODS)
    ap.add_argument("--update-ml", action="store_true")
    args = ap.parse_args()

    if args.list_targets:
        list_targets()
        return
    if args.presets:
        presets(args.outdir)
        return

    char = load_char()
    target = find_target(char, args)
    if args.keys.strip().lower() in ("all", "all133"):
        keys = ichiban_variant_keys(char)
        print("Redirecting all %d ichiban variant keys -> target row" % len(keys))
    else:
        keys = tuple(int(k) for k in args.keys.split(",") if k.strip())
    name = args.name or ("Ichiban_Replacer_%s" % (target["model"] or target["character"]))
    build_mod(char, target, keys, name, args.outdir, update_ml=args.update_ml,
              mode=args.mode, job_outfit=args.job_outfit_char,
              portraits=args.portraits)


if __name__ == "__main__":
    main()
