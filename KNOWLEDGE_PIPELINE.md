# Margin evidence pipeline

This document describes the current local extraction and retrieval pipeline used by Margin. The marking workflow uses Ollama and `qwen3:4b`; older descriptions of a rules-only marker are no longer current.

## Building the evidence store

Run from the project directory:

```powershell
python -m app.knowledge --root "C:\path\to\your\resources" --export work/knowledge_export
```

The website's library refresh action updates both its resource dashboard store and the knowledge store. Set `SOURCE_ROOT` in `app/core.py` to the resource folder used by that action.

The command line options `--root`, `--db`, and `--export` support separate resource locations and isolated builds. Use `--refresh-annotations` to reconstruct annotation links again.

Original source files are not modified. Unchanged extraction is cached using checksums and the pipeline version. Canonical membership and content metadata are recalculated during builds.

## Local inventory

The documented development snapshot contains 70 documents, 1,494 pages or logical document units, 4,330 passages, 1,655 annotation records, two canonical rubric records, and eight candidate document staging records.

There are 531 highlight records. Six pages have an OCR unavailable flag. Also, 1,322 annotation records lack an exact normalized primary text span; original annotation data remains stored.

These counts describe the private local resource collection, not material bundled in the GitHub repository. A file's presence in the inventory does not make it eligible for an assessment request.

## Data contracts

The knowledge store is `work/knowledge.sqlite3`.

| Table | Stored information |
| --- | --- |
| `documents` | File manifest, classification evidence, checksum, duplicate relationships, metadata uncertainty, quality flags, and policy eligibility |
| `pages` | Raw extraction, separately normalized search text, page number, extraction method, and flags |
| `passages` | Overlapping page bounded text chunks with offsets and provenance |
| `search` | SQLite FTS5 keyword index of canonical passages |
| `notes` | Original annotation comments, geometry, authorship metadata, related PDF object references, reconstructed highlights, passage links, and unresolved flags |
| `rubrics` | Canonical descriptor text with originating components and source pages |
| `calibration` | Candidate document staging records awaiting aligned questions, responses, and teacher marks |

For DOCX files, the page field describes a logical unit rather than a printed page. For XLSX files it describes a worksheet.

Auditable JSONL exports are written under `work/knowledge_export/`.

## Extraction and provenance

- PDF text extraction uses `pypdf`
- Highlight reconstruction uses `pdfplumber` word coordinates and PDF annotation geometry
- Text and Markdown files are decoded as UTF-8
- Optional DOCX extraction uses `python-docx`
- Optional XLSX extraction uses `openpyxl`
- Optional OCR uses Tesseract and, for scanned PDF rendering, `pdftoppm`

Missing dependencies and extraction problems are recorded rather than treated as successfully recovered text. Repeated short boundary lines can be removed from normalized search text while raw extraction is preserved.

Exact duplicates and repeated descriptor grids are canonicalized. Fuzzy duplicate candidates are not automatically merged. Source identity does not independently verify an edition or every extracted line.

Annotation keyword labels are produced by rules. They are not semantic classifications or confirmed literary interpretations.

## Policy and source selection

The active assessment configuration is limited to 2026 and 2027. Applicable rubric selection checks the requested component. Later assessment systems are not substituted for the configured descriptors.

The primary text classifier requires corroborating content for the supplied text identities. A renamed file or a passing mention of a work does not automatically become primary evidence.

Retrieval is SQLite FTS5 lexical search with metadata filtering, rather than an embedding based search engine. The marking packet further restricts literary evidence to eligible primary text and literary notes. General candidate examples, question papers, and examiner reports are not automatically promoted to primary literary evidence.

Human annotations are labelled separately from primary text. Their inclusion does not establish that their interpretations are correct.

## From response to model report

The answer limit is 1,000 words. Browser checks are backed by server validation.

The complete response is segmented into paragraphs and sentences with offsets into the original input. The preliminary review also records quotation matches and possible revision targets. Missing source matches are not treated as proof of a quotation error because editions, punctuation, and extraction can differ.

The model packet includes the exact question, complete candidate sentence spans, paragraph groupings, eligible rubric, optional supplied passage, and selected source snippets. Optional retrieved sources may be omitted to meet the packet budget. The application does not silently shorten the candidate answer.

Ollama generates a structured report. Every paragraph key and AO1–AO4 key is required. Feedback points select candidate sentence identifiers; the application resolves their exact original wording and location. The mark is checked against the supplied descriptor ranges and the corresponding level is derived from those ranges.

Structural validation and exact candidate quotations do not prove that a model interpretation, contextual assertion, or holistic mark is correct.

## Saved work and diagnostics

Saved submissions and background jobs live in `work/examiner.sqlite3`, separately from the knowledge store.

Background job states distinguish queued, running, completed, and failed assessments. Refreshing the browser does not restart model inference. A server restart interrupts active work and preserves its stored input for retry.

Completed reports retain the evidence review, model audit metadata, selected sources, paragraph comments, objective comments, and line feedback. Raw model runs and validation errors are recorded under `work/model_runs/` where available.

Historical submissions retain their original results. Some older reports were produced by earlier prototype markers and do not contain the current paragraph or qualitative objective fields.

## Calibration status

The model has not been fine tuned on this collection. Candidate document staging records have no aligned teacher mark and are marked ineligible for training.

No completed blind calibration or independent examiner agreement evaluation has been performed. The current checks establish application behaviour and evidence integrity, not examiner equivalence.

Relevant regression checks can be run with:

```powershell
python -m unittest tests.test_limits tests.test_local_model tests.test_api -v
python -m unittest discover -s tests -p test_review.py -v
```

Some extraction tests require the original resource collection. Refer to [README.md](README.md) for setup and publication guidance.
