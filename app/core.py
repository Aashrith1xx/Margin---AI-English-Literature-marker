from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from pypdf import PdfReader

SUPPORTED_YEARS = {2026, 2027}
SOURCE_ROOT = Path(r"C:\Users\Aashr\OneDrive\Documents\Englit_marker_material")


def assess(question: str, response: str, year: int|None, component: str|None, work: str|None, question_type: str, passage: str|None, progress=None) -> dict[str, Any]:
    from .review import review
    if not question.strip(): raise ValueError('An exact question is required before assessment.')
    if year not in SUPPORTED_YEARS: raise ValueError('Select 2026 or 2027 before assessment.')
    if not response.strip(): raise ValueError('A candidate response is required before assessment.')
    from .limits import check_response_limit
    check_response_limit(response)
    evidence = review(question,response,work,component,passage)
    from .local_model import assess_local
    result = assess_local(question,response,year,component,work,question_type,passage,evidence,progress)
    return result


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    
    
    conn = sqlite3.connect(db_path, timeout=45)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
    PRAGMA journal_mode=WAL;
    PRAGMA busy_timeout=45000;
    PRAGMA foreign_keys=ON;
    CREATE TABLE IF NOT EXISTS resources (
      id INTEGER PRIMARY KEY, path TEXT UNIQUE NOT NULL, filename TEXT NOT NULL,
      kind TEXT NOT NULL, sha256 TEXT NOT NULL, pages INTEGER, text TEXT,
      extraction_status TEXT NOT NULL, verification_status TEXT NOT NULL,
      metadata_json TEXT NOT NULL DEFAULT '{}'
    );
    CREATE TABLE IF NOT EXISTS annotations (
      id INTEGER PRIMARY KEY, resource_id INTEGER NOT NULL REFERENCES resources(id),
      page INTEGER NOT NULL, subtype TEXT NOT NULL, rect_json TEXT, highlighted_text TEXT,
      surrounding_context TEXT, comment TEXT, author TEXT, colour TEXT,
      parent_ref TEXT, confidence TEXT NOT NULL, verification_status TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS rubrics (
      id INTEGER PRIMARY KEY, fingerprint TEXT UNIQUE NOT NULL, source_resource_id INTEGER,
      descriptor_text TEXT NOT NULL, applicability_json TEXT NOT NULL DEFAULT '[]'
    );
    CREATE TABLE IF NOT EXISTS submissions (
      id INTEGER PRIMARY KEY, created_at TEXT DEFAULT CURRENT_TIMESTAMP, year INTEGER,
      component TEXT, work TEXT, question TEXT NOT NULL, question_type TEXT NOT NULL,
      response TEXT NOT NULL, passage TEXT, result_json TEXT
    );
    """)
    return conn


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def classify(path: Path) -> str:
    p = str(path).lower().replace("_", " ")
    if "mark scheme" in p or "mark schemes" in p or " ms " in f" {p} ": return "assessment_criteria"
    if "question papers" in p or " qp " in f" {p} ": return "question_paper"
    if "examiner reports" in p or " examiner report" in p: return "examiner_report"
    if "example responses" in p: return "candidate_response"
    if "teaching packs" in p: return "cambridge_teaching_pack"
    if "texts and analysis" in p:
        primary_names = {"_oceanofpdf.com_blues_for_an_alabama_sky_-_pearl_cleage.pdf", "things-fall-apart.pdf", "the bus by arun.k.pdf", "the roadpoem.pdf", "children of wealth.md"}
        return "primary_literary_text" if path.name.lower() in primary_names else "literary_annotation"
    if path.suffix.lower() == ".md": return "primary_literary_text" if path.name.lower()=="children of wealth.md" else "literary_annotation"
    return "unknown"


def annotation_colour(a: Any) -> str | None:
    color = a.get("/C")
    return json.dumps([float(x) for x in color]) if color else None


def rects_from_quadpoints(a: Any) -> list[list[float]]:
    q = a.get("/QuadPoints")
    if not q: return []
    vals = [float(x) for x in q]
    return [[min(vals[i], vals[i+2], vals[i+4], vals[i+6]), min(vals[i+1], vals[i+3], vals[i+5], vals[i+7]), max(vals[i], vals[i+2], vals[i+4], vals[i+6]), max(vals[i+1], vals[i+3], vals[i+5], vals[i+7])] for i in range(0, len(vals), 8)]


def words_for_page(pdf_path: Path, page_no: int) -> list[dict[str, Any]]:
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            
            p = pdf.pages[page_no]
            height = float(p.height)
            return [{"text": w["text"], "x0": w["x0"], "x1": w["x1"], "y0": height-w["bottom"], "y1": height-w["top"]} for w in p.extract_words()]
    except Exception:
        return []


def text_for_rect(words: list[dict[str, Any]], rects: list[list[float]]) -> str:
    picked = []
    for w in words:
        cx, cy = (w["x0"] + w["x1"])/2, (w["y0"] + w["y1"])/2
        if any(r[0]-2 <= cx <= r[2]+2 and r[1]-2 <= cy <= r[3]+2 for r in rects): picked.append(w)
    return " ".join(w["text"] for w in picked)


def nearby_text(words: list[dict[str, Any]], rects: list[list[float]]) -> str:
    if not rects: return ""
    lo, hi = min(r[1] for r in rects)-35, max(r[3] for r in rects)+35
    return " ".join(w["text"] for w in words if lo <= (w["y0"]+w["y1"])/2 <= hi)[:1200]


def annotation_records(path: Path) -> list[dict[str, Any]]:
    reader = PdfReader(str(path)); out = []
    
    
    
    annotated_pages = [i for i, p in enumerate(reader.pages) if p.get("/Annots")]
    word_cache: dict[int, list[dict[str, Any]]] = {}
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            for i in annotated_pages:
                p = pdf.pages[i]; height = float(p.height)
                word_cache[i] = [{"text": w["text"], "x0": w["x0"], "x1": w["x1"], "y0": height-w["bottom"], "y1": height-w["top"]} for w in p.extract_words()]
    except Exception:
        pass
    for page_no, page in enumerate(reader.pages, 1):
        annots = page.get("/Annots")
        if not annots: continue
        words = word_cache.get(page_no-1, [])
        for ref in annots.get_object():
            a = ref.get_object(); subtype = str(a.get("/Subtype", "/Unknown"))[1:]
            if subtype in {"Link", "Popup", "Ink", "Caret"}: continue
            rects = rects_from_quadpoints(a)
            if not rects and a.get("/Rect"):
                r = a["/Rect"]; rects = [[float(r[0]), float(r[1]), float(r[2]), float(r[3])]]
            text = text_for_rect(words, rects) if subtype in {"Highlight", "Underline", "Squiggly", "StrikeOut"} else ""
            
            comment = str(a.get("/Contents", "")).strip() or None
            parent = str(a.get("/Parent", a.get("/IRT", ""))) or None
            out.append({"page":page_no,"subtype":subtype,"rects":rects,"highlighted_text":text or None,
                        "surrounding_context":nearby_text(words, rects) or None,"comment":comment,
                        "author":str(a.get("/T", "")).strip() or None,"colour":annotation_colour(a),"parent_ref":parent,
                        "confidence":"exact_coordinates" if text else "coordinates_only"})
    
    return out


def resource_metadata(path: Path, text: str) -> dict[str, Any]:
    s = str(path).lower(); m = re.search(r"0475[_ -]([msw])(\d{2})[_ -](?:qp|ms|er)[_ -]?(\d{2})?", path.name.lower())
    return {"year": 2000+int(m.group(2)) if m else None, "session":m.group(1) if m else None,
            "component":m.group(3) if m and m.group(3) else None,
            "question_type": "unseen" if "42" in path.name or "41" in path.name else None,
            "possible_work": next((x for x in ["Things Fall Apart", "Blues for an Alabama Sky", "The Bus", "The Road", "These are the Times"] if x.lower().split()[0] in s), None),
            "text_chars":len(text)}


def extract_text(path: Path) -> tuple[str, int, str]:
    if path.suffix.lower() in {".md", ".txt"}: return path.read_text(encoding="utf-8", errors="replace"), 0, "ok"
    if path.suffix.lower() != ".pdf": return "", 0, "unsupported"
    try:
        r = PdfReader(str(path)); return "\n".join(p.extract_text() or "" for p in r.pages), len(r.pages), "ok"
    except Exception as e: return "", 0, f"failed:{type(e).__name__}"


def canonical_descriptor(text: str) -> str:
    
    lines = [re.sub(r"\s+", " ", x).strip().lower() for x in text.splitlines() if re.search(r"level|band|mark|response|analysis", x, re.I)]
    return "\n".join(lines[:180])


def ingest(root: Path, db_path: Path) -> dict[str, Any]:
    conn = connect(db_path); counts = Counter(); annotation_count = 0; failures=[]
    for path in root.rglob("*"):
        if not path.is_file() or path.name.lower() == "desktop.ini": continue
        kind = classify(path); digest = sha256(path)
        existing = conn.execute("SELECT id,sha256,extraction_status FROM resources WHERE path=?", (str(path),)).fetchone()
        
        
        if existing and existing["sha256"] == digest and existing["extraction_status"] == "ok":
            conn.execute("UPDATE resources SET kind=? WHERE id=?", (kind, existing["id"]))
            counts[kind] += 1
            continue
        text, pages, status = extract_text(path)
        meta = resource_metadata(path, text)
        cur=conn.execute("INSERT INTO resources(path,filename,kind,sha256,pages,text,extraction_status,verification_status,metadata_json) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(path) DO UPDATE SET kind=excluded.kind,sha256=excluded.sha256,text=excluded.text,pages=excluded.pages,extraction_status=excluded.extraction_status,verification_status=excluded.verification_status,metadata_json=excluded.metadata_json", (str(path),path.name,kind,digest,pages,text,status,"primary_text_verified" if kind=="primary_literary_text" else "extracted_unverified",json.dumps(meta)))
        row=conn.execute("SELECT id FROM resources WHERE path=?",(str(path),)).fetchone(); rid=row[0]; counts[kind]+=1
        conn.execute("DELETE FROM annotations WHERE resource_id=?",(rid,))
        
        
        if path.suffix.lower()==".pdf" and kind in {"primary_literary_text", "literary_annotation"}:
            try:
                records=annotation_records(path)
                for a in records:
                    conn.execute("INSERT INTO annotations(resource_id,page,subtype,rect_json,highlighted_text,surrounding_context,comment,author,colour,parent_ref,confidence,verification_status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (rid,a["page"],a["subtype"],json.dumps(a["rects"]),a["highlighted_text"],a["surrounding_context"],a["comment"],a["author"],a["colour"],a["parent_ref"],a["confidence"],"human_annotation"))
                annotation_count += len(records)
            except Exception as e: failures.append({"file":str(path),"error":type(e).__name__})
        if kind == "assessment_criteria":
            descriptor=canonical_descriptor(text); fp=hashlib.sha256(descriptor.encode()).hexdigest()
            app=json.dumps([{"years":[2026,2027],"source":path.name}])
            existing = conn.execute("SELECT applicability_json FROM rubrics WHERE fingerprint=?", (fp,)).fetchone()
            if existing:
                mappings = json.loads(existing[0])
                mapping = {"years":[2026,2027],"source":path.name}
                if mapping not in mappings:
                    mappings.append(mapping)
                    conn.execute("UPDATE rubrics SET applicability_json=? WHERE fingerprint=?", (json.dumps(mappings), fp))
            else:
                conn.execute("INSERT INTO rubrics(fingerprint,source_resource_id,descriptor_text,applicability_json) VALUES(?,?,?,?)", (fp,rid,descriptor,app))
    conn.commit()
    total_annotations = conn.execute("SELECT count(*) FROM annotations").fetchone()[0]
    return {"resources":dict(counts),"annotations":total_annotations,"new_or_changed_annotations":annotation_count,"annotation_failures":failures,"canonical_rubrics":conn.execute("SELECT count(*) FROM rubrics").fetchone()[0]}


