# Margin

Margin is a website for marking IGCSE English Literature responses.

You enter a question and an answer of up to 1,000 words. Margin uses the applicable marking criterias, source material and a local run model to produce a provisional mark (not 100% accurate) and detailed feedback. Completed assessments are stored on your computer and can be reopened from saved work.

## What it does

- Awards a mark out of 25.
- Explains strengths and what limits the response from reaching the next band
- Provides comments on AO1, AO2, AO3, and AO4
- Shows the original wording, the weakness, why it matters, an improvement, and example wording
- Saves completed reports locally

## How marking works

1. Validate and save the submission
2. Keep the complete answer
3. Find relevant evidence from fed material
4. Build the model request
5. Generate a report locally using qwen 3
6. Check and store the result

## Resources supplied to the project

| Resource category | Files | Role |
| --- | --- | --- |
| Question papers | 21 | Indexed question material and reference context |
| Literary notes | 9 | Potential interpretive material for the relevant work |
| Examiner reports | 8 | Reference material retained in the library |
| Example candidate responses | 8 | Indexed examples and records awaiting calibration alignment |
| Teaching packs and learner guides | 8 | Reference and teaching material retained in the library |
| Primary literary texts | 5 | Potential source evidence for the matching work |
| Generic mark schemes | 3 | Sources for eligible assessment descriptors |
| Unclassified resources | 8 | Retained in the inventory but excluded from normal retrieval |
| Total | 70 | |

## Running locally

### Requirements

- Python 3.10 or later
- Ollama with qwen3:4b installed
- The Python packages in requirements.txt
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

The model API must be available at [http://127.0.0.1:11434](http://127.0.0.1:11434). If you are using a command line installation rather than the background app, run `ollama serve` in a separate terminal.

Set `SOURCE_ROOT` in `app/core.py` to your own resource directory. Its development default points to a folder on the original machine.

Start Margin:

```powershell
python -m app.server
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765), select library, and use refresh library to build or refresh the resource stores.

An eligible mark scheme must be present for the component being assessed. The supplied development collection supports components such as 12, 32, and 42.

Optional DOCX and XLSX extraction requires python-docx and openpyxl. OCR requires Tesseract and, for scanned PDF rendering, pdftoppm. These optional tools are not installed by the core requirements file.

### Existing portable setup

If the portable Ollama runtime is already present at `work/local-model/runtime/ollama.exe`, the convenience script starts the model service and website:

```powershell
.\start-margin.ps1
```

It reuses an installed model, downloads it if missing, and detects an already running Margin server. The portable runtime directory is intentionally excluded from source control.

## Word limit and processing time

The limit is 1,000 words for the candidate answer. The question and primary passage are not included in that answer limit.

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
| work/knowledge.sqlite3 | Resource manifests, extracted text, annotations, search passages, and rubrics |
| work/examiner.sqlite3 | Saved submissions, assessment jobs, and completed reports |
| work/knowledge_export/ | JSONL exports for resource inspection |
| work/model_runs/ | Raw model output and validation diagnostics |
| work/local-model/ | Portable runtime and downloaded model files |
