#!/usr/bin/env python3
"""
extract_and_seed.py
-------------------
Reads all .pdf files (which are actually ZIP archives) from the dataset folder,
extracts structured scheme data, and inserts directly into MongoDB.

No giant JSON file needed!

REQUIREMENTS — run this once before starting:
    pip install pymongo python-dotenv ftfy huggingface_hub

HOW TO RUN:
    python extract_and_seed.py

WHERE TO PUT THIS FILE:
    Backend/scripts/extract_and_seed.py
    (same folder as seedSchemes.js)
"""

import json
import os
import re
import zipfile
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
from pathlib import Path

# ──────────────────────────────────────────────────────────
# ⚠️  CHANGE #1 — MongoDB connection string
#     Option A: paste your connection string directly below
#     Option B: leave as None and it will read from your .env file
#               (looks for MONGODB_URL in Backend/.env)
# ──────────────────────────────────────────────────────────
MONGODB_URL = None   # e.g. "mongodb://localhost:27017/mydb"  OR  None to use .env

# ──────────────────────────────────────────────────────────
# ⚠️  CHANGE #2 — MongoDB database and collection name
#     Open your Mongoose model file:
#       Backend/models/schemev2.model.js
#     Look for the collection name at the bottom, e.g.:
#       mongoose.model('Schemev2', ...)   → collection = "schemev2s"
#     MongoDB auto-pluralises + lowercases the model name.
# ──────────────────────────────────────────────────────────
DB_NAME         = "scheme-seva"       # ← your database name
COLLECTION_NAME = "schemesv2"      # ← your collection name (usually modelName + 's')

# ──────────────────────────────────────────────────────────
# ⚠️  CHANGE #3 — Folder containing the .pdf (ZIP) files
#     This is wherever you downloaded the Hugging Face files.
#     Use an absolute path or relative to where you run the script.
# ──────────────────────────────────────────────────────────
PDF_FOLDER = "../data/pdfs/text_data"        # ← relative path from Backend/scripts/

# ──────────────────────────────────────────────────────────
# ⚠️  CHANGE #4 — Should it clear old data first?
#     True  = deletes ALL existing schemes before inserting
#     False = adds on top of existing data (skips duplicates)
# ──────────────────────────────────────────────────────────
CLEAR_EXISTING = True

# ──────────────────────────────────────────────────────────
# ⚠️  CHANGE #5 — Batch size
#     How many schemes to insert at once.
#     50-100 is fine for most machines.
# ──────────────────────────────────────────────────────────
BATCH_SIZE = 50

# ══════════════════════════════════════════════════════════
#   DO NOT CHANGE ANYTHING BELOW THIS LINE
#   (unless you know what you're doing!)
# ══════════════════════════════════════════════════════════

# ── Load .env if MONGODB_URL not set directly ─────────────
if MONGODB_URL is None:
    try:
        from dotenv import load_dotenv
        # Walk up to find .env
        script_dir = Path(__file__).parent
        for candidate in [script_dir / ".env",
                          script_dir.parent / ".env",
                          script_dir.parent.parent / ".env"]:
            if candidate.exists():
                load_dotenv(candidate)
                break
        MONGODB_URL = os.environ.get("MONGODB_URL") or os.environ.get("MONGO_URI")
        if not MONGODB_URL:
            raise ValueError("MONGODB_URL not found in .env file")
    except ImportError:
        raise SystemExit("❌  python-dotenv not installed. Run: pip install python-dotenv")

# ── Imports ───────────────────────────────────────────────
try:
    from pymongo import MongoClient, UpdateOne
    from pymongo.errors import BulkWriteError
except ImportError:
    raise SystemExit("❌  pymongo not installed. Run: pip install pymongo")

try:
    import ftfy
    HAS_FTFY = True
except ImportError:
    HAS_FTFY = False
    print("⚠️  ftfy not installed — encoding fixes will be partial.")
    print("    Install with: pip install ftfy\n")


# ══════════════════════════════════════════════════════════
#  STEP 1 — ENCODING FIX
# ══════════════════════════════════════════════════════════

# Characters that are always garbled in these files
CHAR_FIXES = {
    '\ufb01': 'fi',   # fi ligature  (shows as ï¬)
    '\ufb02': 'fl',   # fl ligature
    '\x02':   ' ',    # stray control character
    '\x00':   '',
    '\ufeff': '',     # BOM
}

def fix_encoding(text: str) -> str:
    if HAS_FTFY:
        text = ftfy.fix_text(text)
    for bad, good in CHAR_FIXES.items():
        text = text.replace(bad, good)
    return text


# ══════════════════════════════════════════════════════════
#  STEP 2 — READ TEXT FROM ZIP
# ══════════════════════════════════════════════════════════

def is_zip_file(path: str) -> bool:
    """Check if file is actually a ZIP by reading its magic bytes."""
    try:
        with open(path, 'rb') as f:
            return f.read(2) == b'PK'
    except:
        return False


def read_text_from_zip(zip_path: str) -> str:
    """Open the ZIP, read all .txt pages in order, return combined text."""
    pages = []
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            if "manifest.json" in names:
                manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
                txt_files = [p["text"]["path"]
                             for p in manifest.get("pages", [])
                             if "text" in p]
            else:
                txt_files = sorted(n for n in names if n.endswith(".txt"))
            for f in txt_files:
                if f in names:
                    raw = zf.read(f).decode("utf-8", errors="replace")
                    pages.append(raw)
    except Exception as e:
        print(f"    ⚠ ZIP read error in {zip_path}: {e}")
        return ""
    return "\n".join(pages)


def read_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a real PDF using pdfplumber."""
    if not HAS_PDFPLUMBER:
        print("    ⚠ pdfplumber not installed. Run: pip install pdfplumber")
        return ""
    try:
        pages = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
        return "\n".join(pages)
    except Exception as e:
        print(f"    ⚠ PDF read error in {pdf_path}: {e}")
        return ""


def read_file(path: str) -> str:
    """Auto-detect file type and extract text accordingly."""
    if is_zip_file(path):
        return read_text_from_zip(path)
    else:
        return read_text_from_pdf(path)


# ══════════════════════════════════════════════════════════
#  STEP 3 — CLEAN UP TEXT
# ══════════════════════════════════════════════════════════

# Cut off everything from the website footer onwards
FOOTER_PATTERN = re.compile(
    r"(Ok\s*Was this helpful\?|ShareNews and Updates|"
    r"©\d{4}|Powered by|Digital India Corporation|Quick\s*Links)",
    re.IGNORECASE,
)

def strip_footer(text: str) -> str:
    m = FOOTER_PATTERN.search(text)
    return text[:m.start()].strip() if m else text.strip()

def find_content_start(text: str) -> str:
    """
    Skip the navigation bar at the top.
    The nav bar is: SchemeName + UI junk + all section names listed
    Real content starts at the SECOND occurrence of 'Details'.
    """
    first = text.find("Details")
    if first == -1:
        return text
    second = text.find("Details", first + 1)
    return text[second:] if second != -1 else text[first:]


# ══════════════════════════════════════════════════════════
#  STEP 4 — SPLIT INTO SECTIONS
# ══════════════════════════════════════════════════════════

SECTION_NAMES = [
    "Details",
    "Benefits",
    "Eligibility",
    "Application Process",
    "Documents Required",
    "Frequently Asked Questions",
    "Sources And References",
]

def split_sections(text: str) -> dict:
    """Split the content blob into named sections."""
    result = {}
    remaining = text

    for i, section in enumerate(SECTION_NAMES):
        idx = remaining.find(section)
        if idx == -1:
            continue

        content_start = idx + len(section)
        next_idx = len(remaining)

        for next_section in SECTION_NAMES[i + 1:]:
            ni = remaining.find(next_section, content_start)
            if ni != -1 and ni < next_idx:
                next_idx = ni

        result[section] = remaining[content_start:next_idx].strip()
        remaining = remaining[next_idx:]

    return result


# ══════════════════════════════════════════════════════════
#  STEP 5 — EXTRACT INDIVIDUAL FIELDS
# ══════════════════════════════════════════════════════════

def extract_scheme_name(raw_text: str) -> str:
    """Scheme name is always the very first thing before 'Are you sure'."""
    first_part = raw_text.split("Are you sure")[0].strip()
    # Sometimes tags get concatenated: "Scheme NameTagOneTagTwo"
    # Split at camelCase boundary to isolate the name
    split = re.sub(r"([a-z])([A-Z])", r"\1|\2", first_part).split("|")
    return split[0].strip()


def make_short_title(name: str, index: int) -> str:
    words = re.findall(r"\b[A-Za-z]\w*", name)
    if len(words) >= 2:
        abbr = "".join(w[0].upper() for w in words[:6])
        if len(abbr) >= 2:
            return abbr
    return f"SCH{index:05d}"


# Document splitting — splits run-together document list
DOCUMENT_SPLIT = re.compile(
    r"(?<=[a-z0-9\)])\s*(?="
    r"(?:Aadhaar|PAN|Pan|Voter|Passport|Ration|Birth|Income|"
    r"Residence|Caste|Address|Bank|Photo|Self|Attested|Recent|"
    r"Domicile|Class|Mark|Degree|Disability|Medical|Application|"
    r"NOC|BPL|Community|Age|Land|Property|Certificate|Card|"
    r"Proof|Statement|Copy|Letter|Declaration|Affidavit|ID\s|Identity))",
    re.IGNORECASE,
)

def parse_documents(text: str) -> list:
    if not text:
        return []
    parts = DOCUMENT_SPLIT.split(text)
    docs = []
    for part in parts:
        part = part.strip()
        if len(part) < 5:
            continue
        if any(x in part.lower() for x in ["sources and", "guidelines", "official website"]):
            break
        docs.append({"document": part, "description": ""})
    if not docs and len(text) > 10:
        docs = [{"document": text[:200], "description": ""}]
    return docs


def parse_benefits(text: str) -> list:
    if not text:
        return []
    items = re.split(r"\n?\d+\.\s+|\n[•\-\*]\s*", text)
    benefits = []
    for item in items:
        item = item.strip()
        if len(item) < 15:
            continue
        benefits.append({"title": item[:80].rstrip(".,"), "description": item})
    if not benefits and len(text) > 10:
        benefits = [{"title": text[:80], "description": text}]
    return benefits


def parse_application_process(text: str) -> list:
    if not text:
        return []
    tl = text.lower()
    if "offline" in tl and "online" not in tl:
        mode = "Offline"
    elif "online" in tl and "offline" not in tl:
        mode = "Online"
    else:
        mode = "Online/Offline"

    steps = re.split(r"Step\s*(?:0?\d+|[A-Z]+)\s*[:.]?\s*", text, flags=re.IGNORECASE)
    steps = [s.strip() for s in steps if len(s.strip()) > 10]
    if len(steps) <= 1:
        steps = re.split(r"\n\d+\.\s+", text)
        steps = [s.strip() for s in steps if len(s.strip()) > 10]
    if not steps:
        steps = [text.strip()]
    return [{"mode": mode, "process": steps}]


def parse_faqs(text: str) -> list:
    if not text:
        return []
    parts = re.split(r"(?<=[?])\s*", text)
    faqs = []
    for i in range(0, len(parts) - 1, 2):
        q = parts[i].strip()
        a = parts[i + 1].strip() if i + 1 < len(parts) else ""
        qm = re.search(r"[A-Z][^?]+\?$", a)
        if qm:
            a = a[:qm.start()].strip()
        if len(q) > 10 and len(a) > 5:
            faqs.append({"question": q, "answer": a})
    return faqs[:20]


# ── State / Level detection ───────────────────────────────
STATES = [
    "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh",
    "Goa","Gujarat","Haryana","Himachal Pradesh","Jharkhand","Karnataka",
    "Kerala","Madhya Pradesh","Maharashtra","Manipur","Meghalaya","Mizoram",
    "Nagaland","Odisha","Punjab","Rajasthan","Sikkim","Tamil Nadu",
    "Telangana","Tripura","Uttar Pradesh","Uttarakhand","West Bengal",
    "Andaman and Nicobar","Chandigarh","Dadra and Nagar Haveli",
    "Daman and Diu","Delhi","Jammu and Kashmir","Ladakh",
    "Lakshadweep","Puducherry",
]
UTS = {"Andaman and Nicobar","Chandigarh","Dadra and Nagar Haveli",
       "Daman and Diu","Delhi","Jammu and Kashmir","Ladakh","Lakshadweep","Puducherry"}

def detect_state_level(text: str):
    for state in STATES:
        if state.lower() in text.lower():
            return state, ("State/ UT" if state in UTS else "State")
    if any(k in text.lower() for k in ["government of india","all india"]):
        return "All India", "Central"
    if re.search(r"ministry\s+of", text, re.IGNORECASE):
        return "All India", "Central"
    return "", ""


def detect_ministry(text: str) -> str:
    # Ministry appears in the breadcrumb: "Check Eligibility<Ministry>Scheme Name"
    m = re.search(r"Check Eligibility(Ministry\s+(?:Of|of)\s+[^\n\r]+?)(?=[A-Z][a-z].*(?:Scheme|Yojana|Programme|Program|Initiative))",
                  text)
    if m:
        ministry = m.group(1).strip()
        if len(ministry) < 100:
            return ministry

    # Fallback: find "Ministry of/Of X" anywhere
    m2 = re.search(r"Ministry\s+(?:of|Of)\s+[A-Z&][^\n\r©®]{5,70}", text)
    if m2:
        result = re.split(r"[©®]|\bPowered\b|\bDigital India\b|\bQuick\b|Government of India", m2.group(0))[0]
        return result.strip()
    return ""


TAG_MAP = {
    "subsidy":     ["subsidy"],
    "grant":       ["grant"],
    "loan":        ["loan"],
    "scholarship": ["scholarship","stipend","fellowship"],
    "pension":     ["pension"],
    "housing":     ["housing","house","shelter"],
    "education":   ["education","school","college","university","student"],
    "health":      ["health","hospital","medical","treatment","disease"],
    "employment":  ["employment","job","livelihood"],
    "agriculture": ["agriculture","farmer","crop","kisan"],
    "business":    ["business","enterprise","entrepreneur","startup"],
    "women":       ["women","woman","girl","female","maternity"],
    "youth":       ["youth","young"],
    "senior":      ["senior citizen","elderly","old age"],
    "disability":  ["disability","disabled","divyang"],
    "sc/st":       ["scheduled caste","scheduled tribe","sc/st","tribal"],
}

def detect_tags(text: str) -> list:
    tl = text.lower()
    return [tag for tag, kws in TAG_MAP.items() if any(k in tl for k in kws)]


# ══════════════════════════════════════════════════════════
#  STEP 6 — FULL PARSE PIPELINE
# ══════════════════════════════════════════════════════════

def parse_scheme(raw_text: str, filename: str, index: int):
    if not raw_text or len(raw_text) < 100:
        return None

    text      = fix_encoding(raw_text)
    name      = extract_scheme_name(text)
    if not name or len(name) < 5:
        name  = Path(filename).stem.replace("_", " ").title()

    clean     = strip_footer(text)
    content   = find_content_start(clean)
    sections  = split_sections(content)

    state, level = detect_state_level(text)
    ministry     = detect_ministry(text)
    tags         = detect_tags(text)

    scheme = {
        "schemeName":               name,
        "schemeShortTitle":         make_short_title(name, index),
        "state":                    state,
        "level":                    level,
        "nodalMinistryName":        ministry,
        "tags":                     tags,
        "schemeCategory":           [],
        "detailedDescription_md":   sections.get("Details", "").strip(),
        "eligibilityDescription_md":sections.get("Eligibility", "").strip(),
        "benefits":                 parse_benefits(sections.get("Benefits", "")),
        "documents_required":       parse_documents(sections.get("Documents Required", "")),
        "applicationProcess":       parse_application_process(sections.get("Application Process", "")),
        "faqs":                     parse_faqs(sections.get("Frequently Asked Questions", "")),
        "references":               [],
        "openDate":                 None,
        "closeDate":                None,
    }

    if not scheme["detailedDescription_md"] and not scheme["eligibilityDescription_md"]:
        return None

    return scheme


# ══════════════════════════════════════════════════════════
#  STEP 7 — SEED DIRECTLY INTO MONGODB
# ══════════════════════════════════════════════════════════

def seed_to_mongodb(pdf_folder: str):
    # Connect
    print(f"🔌 Connecting to MongoDB...")
    client     = MongoClient(MONGODB_URL)
    db         = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    print(f"✅ Connected!  Database: {DB_NAME}  Collection: {COLLECTION_NAME}\n")

    if CLEAR_EXISTING:
        deleted = collection.delete_many({})
        print(f"🗑️  Cleared {deleted.deleted_count} existing documents\n")

    # Find all .pdf files
    folder     = Path(pdf_folder)
    pdf_files  = sorted(folder.glob("**/*.pdf"))

    if not pdf_files:
        print(f"❌ No .pdf files found in: {pdf_folder}")
        print("   Check that PDF_FOLDER path is correct.")
        return

    print(f"📂 Found {len(pdf_files)} files\n")

    seen_names = set()
    batch      = []
    inserted   = 0
    skipped    = 0
    failed     = 0

    for i, pdf_path in enumerate(pdf_files, start=1):
        print(f"  [{i:5d}/{len(pdf_files)}] {pdf_path.name[:40]:<40}", end=" ", flush=True)

        try:
            raw  = read_file(str(pdf_path))
            if not raw or len(raw.strip()) < 100:
                print("⚠  empty")
                failed += 1
                continue

            scheme = parse_scheme(raw, pdf_path.name, i)
            if scheme is None:
                print("⚠  no content")
                failed += 1
                continue     

            # Deduplicate
            key = scheme["schemeName"].strip().lower()
            if key in seen_names:
                print("⏭  duplicate")
                skipped += 1
                continue
            seen_names.add(key)

            batch.append(scheme)
            print(f"✅ {scheme['schemeName'][:50]}")

            # Insert batch
            if len(batch) >= BATCH_SIZE:
                try:
                    collection.insert_many(batch, ordered=False)
                    inserted += len(batch)
                    print(f"\n  💾 Inserted batch — total so far: {inserted}\n")
                except BulkWriteError as e:
                    # Some duplicates slipped through — that's okay
                    inserted += e.details.get("nInserted", 0)
                batch = []

        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1

    # Insert remaining
    if batch:
        try:
            collection.insert_many(batch, ordered=False)
            inserted += len(batch)
        except BulkWriteError as e:
            inserted += e.details.get("nInserted", 0)

    client.close()

    print(f"\n{'═'*55}")
    print(f"✅  ALL DONE!")
    print(f"   Inserted  : {inserted}")
    print(f"   Duplicates: {skipped}")
    print(f"   Failed    : {failed}")
    print(f"   Total in DB: {inserted}")
    print(f"{'═'*55}")


# ══════════════════════════════════════════════════════════
#  RUN
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    seed_to_mongodb(PDF_FOLDER)