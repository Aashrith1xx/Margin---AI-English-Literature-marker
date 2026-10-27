# Margin

Margin is a local web app for reviewing Cambridge IGCSE Literature in English 0475 responses for 2026 and 2027.

You enter a question and an answer of up to 1,000 words. Margin uses the applicable marking descriptors, selected source material, and a local language model to produce a provisional mark and detailed feedback. Completed assessments are stored on your computer and can be reopened from saved work.

This is an independent educational prototype. Its feedback is AI generated and is not an official Cambridge assessment.

## What it does

- Awards a holistic mark out of 25 and derives the corresponding best fit level
- Explains strengths and what limits the response from reaching the next band
- Provides qualitative comments on AO1, AO2, AO3, and AO4
- Reviews every paragraph in the submitted response
- Selects up to three lines for specific revision
- Shows the original wording, the weakness, why it matters, an improvement, and example wording
- Saves completed reports locally
- Shows progress while marking continues in the background
- Preserves submitted work when an assessment fails so it can be retried

The interface deliberately uses plain input boxes and a plain output area. Year, component, work, question type, and the optional primary passage are available under other details.

## How marking works

1. **Validate and save the submission**  
   The backend checks the year, question type, required fields, and word limit. It saves the request as a background job before inference begins.

2. **Keep the complete answer**  
   The answer is divided into paragraph and sentence spans. Each sentence has an identifier and offsets into the original text. Accepted answers are not silently shortened.

3. **Find relevant evidence**  
   Margin selects eligible 2026–2027 rubric descriptors and searches the local resource index for relevant passages. Retrieval uses SQLite FTS5 keyword search, with resource metadata and work or component checks. It does not use a semantic embedding database.

4. **Build the model request**  
   The model receives the full candidate response, exact question, rubric, optional user supplied passage, and selected reference snippets. Human annotations are labelled as interpretations rather than primary literary text. The entire resource library is not sent with every request.

5. **Generate a report locally**  
   Ollama runs `qwen3:4b` on the same computer. The model is asked to judge the answer against the holistic descriptors and return a structured report with the required paragraph and assessment objective fields.

6. **Check and store the result**  
   The application validates the mark, paragraph coverage, objective comments, sentence identifiers, and source identifiers. Candidate quotations are resolved directly from the original response rather than reconstructed by the model. The level is derived from the mark range in the supplied rubric. A report that fails the final checks is not saved as a completed assessment.

If optional retrieved material exceeds the context budget, it can be omitted and recorded in the audit data. The candidate response is retained in full. A response and passage that still exceed the context capacity produce an explicit error.

## Resources supplied to the project

The local development library contains the following inventory. These are counts from the indexed resource collection, not files distributed with this repository.

| Resource category | Files | Role |
| --- | ---: | --- |
| Question papers | 21 | Indexed question material and reference context |
| Literary notes | 9 | Potential interpretive material for the relevant work |
| Examiner reports | 8 | Reference material retained in the library |
| Example candidate responses | 8 | Indexed examples and records awaiting calibration alignment |
| Teaching packs and learner guides | 8 | Reference and teaching material retained in the library |
| Primary literary texts | 5 | Potential source evidence for the matching work |
| Generic mark schemes | 3 | Sources for eligible assessment descriptors |
| Unclassified resources | 8 | Retained in the inventory but excluded from normal retrieval |
| **Total** | **70** | |

The index currently contains:

- 1,494 extracted pages or logical document units
- 4,330 searchable passages
- 1,655 annotation records, including 531 highlights
- 2 canonical rubric records after descriptor deduplication
- 8 candidate document records awaiting question, response, and teacher mark alignment

The primary text collection covers:

- Things Fall Apart
- Blues for an Alabama Sky
- Children of Wealth
- The Bus
- The Road

Examples of other supplied material include:

- `0475_s26_ms_12.pdf`
- `0475_s26_ms_32.pdf`
- `0475_s26_ms_42.pdf`
- Examiner reports for several sessions from 2023 to 2026
- Example candidate response documents for poetry, prose, drama, and unseen work
- The Cambridge Literature learner guide and literature teaching packs
- Annotated literary PDFs containing highlights, comments, and related annotation objects

These filenames describe the supplied collection. They do not establish independent verification of every document or edition.

### What is actually fed into the model

Being indexed does not mean a document is automatically used in an assessment.

The marking request includes the applicable rubric and selected eligible literary material. The supplied primary passage is treated as the authority for textual facts. General candidate examples about other works are excluded from the literary evidence packet.

Question papers, examiner reports, and teaching packs remain available in the resource store, but they are not all copied into each model request. The user still supplies the exact question.

For a poem or extract that is not available as a primary text in the local collection, include it in the passage field.

### Extraction and annotation handling

PDF text is extracted with `pypdf`. Highlight geometry is matched to words recovered with `pdfplumber`. The pipeline preserves source filenames, pages, annotation text, coordinates, authorship metadata, and provenance where available.

Native text and normalized search text are stored separately. Duplicate files and repeated descriptors are tracked so they do not automatically become additional independent evidence.

Extraction has known gaps. In this inventory, six pages were flagged because OCR was unavailable. Also, 1,322 annotation records could not be linked to an exact normalized text span; their original records are still retained. These flags need review and should not be read as complete source verification.

## Retrieval rather than model training

Margin uses a pretrained local model with retrieved context and constrained prompting.

The supplied resource collection has **not** been used to fine tune the model weights. Candidate example documents are staged for possible future calibration, but their question, response, and teacher mark relationships are not yet aligned. They are marked ineligible for training.

The tests check application behaviour, evidence handling, word limits, and saved results. They do not demonstrate agreement with Cambridge examiners.

## Running locally

### Requirements

- Python 3.10 or later
- Ollama with `qwen3:4b` installed
- The Python packages in `requirements.txt`
- A local resource folder containing eligible assessment criteria and any source texts you want to use

The resource collection, model weights, portable model runtime, and local databases are not included in the GitHub source repository. A fresh clone needs its own local setup before marking will work.

### Standard installation

From the project directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Install and start [Ollama for Windows](https://docs.ollama.com/windows), then download the configured model:

```powershell
ollama pull qwen3:4b
```

The model API must be available at `http://127.0.0.1:11434`. If you are using a command line installation rather than the background app, run `ollama serve` in a separate terminal.

Set `SOURCE_ROOT` in `app/core.py` to your own resource directory. Its development default points to a folder on the original machine.

Start Margin:

```powershell
python -m app.server
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765), select library, and use refresh library to build or refresh the resource stores.

An eligible mark scheme must be present for the component being assessed. The supplied development collection supports components such as 12, 32, and 42.

Optional DOCX and XLSX extraction requires `python-docx` and `openpyxl`. OCR requires Tesseract and, for scanned PDF rendering, `pdftoppm`. These optional tools are not installed by the core requirements file.

### Existing portable setup

If the portable Ollama runtime is already present at `work/local-model/runtime/ollama.exe`, the convenience script starts the model service and website:

```powershell
.\start-margin.ps1
```

It reuses an installed model, downloads it if missing, and detects an already running Margin server. The portable runtime directory is intentionally excluded from source control.

## Word limit and processing time

The limit is **1,000 words for the candidate answer**. The question and primary passage are not included in that answer limit.

The browser displays the word count and disables submission above the limit. The server independently rejects over limit requests. It never silently cuts the answer to fit.

Marking speed depends on the computer and its current workload. One complete 1,000 word development test took about 16 minutes on the original CPU based setup. This is an observed test result, not a promised average.

Model processing has a 30 minute upper bound. The page can be reloaded or left while a submitted job runs, provided the local server remains running and the computer stays awake. Restarting the server interrupts an active job; its stored response can be retried.

## Project structure

```text
app/
  index.html       Plain web interface
  app.js           Form handling progress and report display
  server.py        Local HTTP server and API
  jobs.py          Background jobs and saved results
  limits.py        Shared response word limit
  core.py          Submission entry point and resource ingestion
  knowledge.py     Extraction metadata annotations and search index
  review.py        Paragraph spans source lookup and quote checks
  local_model.py   Ollama request report schema and validation
tests/             Regression checks and manual integration checks
local_model.json   Local model address model name and runtime settings
start-margin.ps1   Windows portable setup launcher
requirements.txt   Core Python dependencies
```

Generated local data is stored under `work/`:

| Location | Contents |
| --- | --- |
| `work/knowledge.sqlite3` | Resource manifests, extracted text, annotations, search passages, and rubrics |
| `work/examiner.sqlite3` | Saved submissions, assessment jobs, and completed reports |
| `work/knowledge_export/` | JSONL exports for resource inspection |
| `work/model_runs/` | Raw model output and validation diagnostics |
| `work/local-model/` | Portable runtime and downloaded model files |

## Tests

```powershell
python -m unittest tests.test_limits tests.test_local_model tests.test_api -v
node tests/test_ui_limits.cjs
```

The Node command checks browser script behaviour; Node is not required to run the website itself.

Additional extraction and corpus tests are available with:

```powershell
python -m unittest discover -s tests -v
```

Some extraction tests depend on the original local resource collection and will not run unchanged on a source only clone.

## GitHub and privacy

Commit the application source, tests, configuration, requirements, and documentation.

Keep `work/`, `outputs/`, private submissions, source documents, extracted annotations, model weights, secrets, and generated logs out of the repository. Resource indexing does not grant permission to redistribute Cambridge documents, literary works, or annotations.

The application sends marking requests to the loopback model address, rather than a cloud model API. Downloads and package installation still require network access.

Uploading this repository to GitHub stores the code. It does not deploy the marking service. [GitHub Pages is static hosting](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages); the complete application also needs its Python backend and Ollama service.

Margin currently runs as a local single user prototype. Public or multi user deployment needs additional engineering.

## Limitations

- Marks and literary interpretations remain provisional AI judgements
- There is no completed teacher marked calibration or independent examiner agreement evaluation
- A valid output structure and exact candidate quotations do not prove that an interpretation or mark is correct
- Primary text extraction, annotation alignment, and OCR can be incomplete
- Human notes are interpretations rather than authoritative primary text
- The supported assessment configuration is limited to 2026 and 2027

See [KNOWLEDGE_PIPELINE.md](KNOWLEDGE_PIPELINE.md) for the resource data contracts and extraction details.
