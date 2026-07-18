# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A PyQt5 desktop app for a soil-testing laboratory (физические и механические испытания грунтов). It tracks
objects (объекты) → batches (партии) → samples (пробы) and their granulometric (particle-size, "грансостав")
and physical-property (влажность, плотность, органика, etc.) test results, most of which are imported from
Excel workbooks produced by the lab. Domain language is Russian throughout — table names, columns, UI text,
and status strings are Russian, don't translate them when editing.

## Commands

```bash
# Activate the existing venv (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python gui.py

# Run tests
python -m pytest test_gran_sync.py -v

# Run a single test / class
python -m pytest test_gran_sync.py::TestEffectiveStatusSQL -v
python -m pytest test_gran_sync.py::TestIsKrR::test_is_kr_r -v
```

There is no build/lint step configured — `requirements.txt` is the only dependency manifest and
`test_gran_sync.py` is the only test file.

## Architecture

### Layers

- `gui.py` — PyQt5 UI (`MainWindow` + dialogs `NewQDialog`, `NewQDialog2`). All user actions (add object,
  add batch, import an Excel file, run stat checks, sync files) live here as button handlers. It talks to the
  DB only through `orkestrator_db.MainCore`, never through `database.Database` directly.
- `orkestrator_db.py` — `MainCore` is the facade the GUI uses. It wraps a single `Database` instance in three
  role objects: `db_add` (`ZagrVDatabase`, inserts), `db_show` (`ShowIzDatabase`, reads), `db_delete`
  (`DeleteIzDatabase`, deletes). When adding DB operations, extend the relevant role class rather than calling
  `Database` methods from the GUI.
- `database.py` — `Database` owns the raw `sqlite3` connection and schema (`init_database`, idempotent
  `_run_migration` for adding columns to existing DBs) plus all SQL. Every public method opens its own
  connection and closes it (no persistent connection/session object).
- `config_core/` — Excel-import plumbing shared by the GUI and `gransostav.py`:
  - `config.py` — column-rename dicts and column-list constants that translate the (multi-row-header) Excel
    layouts into DB column names. This is the single source of truth for "which Excel column means what".
  - `core.py` — `zagr_file`/`zagr_file2` (load+reshape Excel into DataFrames), the "намыв" (hydrometer
    sedimentation) percentage calculation pipeline (`rashet_gran` → `rashet_popravki_areometr` →
    `rashet_x1_x2_x3` → `itog_raschet_gran`), and `vigruzka_namiv` (export helper).
  - `klasspredict.py` — `ClassPredict.predict`: loads the three joblib models from `models/` and flags samples
    whose lab-measured влажность/плотность/укол deviate from the model's statistical prediction beyond a
    threshold (used by the "Проверка по статистике" button).
  - `vspomogat_func.py` — `process_multiheader_column`, shared by `config_core.core` and `gransostav.py` to
    flatten pandas multi-row Excel headers into single column names.
- `gransostav.py` — `RaschetGranov`: parses the "Грансост_кр_расс_с_пром" sheet of a рабочая сводная workbook
  and computes gran fraction percentages (namyv/промыв path, distinct from the `config_core.core` намыв
  pipeline above).
- `gran_sync.py` — status-tracking logic, independent of the GUI:
  - `EFFECTIVE_STATUS_SQL` — a SQL `CASE` expression, the single source of truth for a sample's *effective*
    грансостав status. It is composed into queries via JOINs against `grans`/`grans_raschet`/`fizika` rather
    than trusting a stored value, and is reused identically in `gran_report_dialog.py` and in
    `test_gran_sync.py`. If the status rules change, update this expression (and its parsing counterpart
    below) — don't hardcode the logic elsewhere.
  - `parse_rab_svodn_excel` — parses a рабочая сводная workbook's two sheets ("Сводная физ св-в" and
    "Грансост_кр_расс_с_пром") into per-sample `{lab_nomer, sample_type, status_gran, has_ukol}` records; this
    is the initial-status counterpart to `EFFECTIVE_STATUS_SQL`.
  - `sync_all_files` — walks every batch with a saved `file_path`, compares file mtime to the stored one, and
    either does an incremental update (`update_probi_status_gran_incremental`, only moves a status *forward*
    per `STATUS_PRIORITY`) or a full rescan (`update_probi_sample_type_and_status`, overwrites).
- `gran_report_dialog.py` — `GranReportDialog`, a filterable stats/report window built entirely on top of
  `EFFECTIVE_STATUS_SQL`.
- `models/*.joblib` — pretrained sklearn models consumed by `klasspredict.py`.
- `excelki/` — sample/reference Excel workbooks, including `tarirovki.xlsx` (areometer calibration table
  required by `rashet_popravki_areometr`).
- `database.db` — the working SQLite database file, checked into the repo (not just a schema/fixture).

### Data model

`objects` (1) → `partii` (N) → `probi` (N) → `fizika` (1:1), `grans` (N, versioned), `grans_raschet` (N,
versioned).

- `grans` and `grans_raschet` are append-only/versioned: each save bumps `version` and flips the previous
  current row's `is_current` to 0 (see `Database.save_grans_bulk_by_lab_nomer` /
  `save_grans_raschet_bulk_by_lab_nomer`). Reads must always filter `is_current = 1` — see
  `get_poln_info_data_by_party_id` and the JOINs inside `EFFECTIVE_STATUS_SQL`'s callers.
- `fizika.status_gran` is a raw stored hint (from parsing), not the value to display — the *displayed* status
  is always `EFFECTIVE_STATUS_SQL`, computed live from `grans`/`grans_raschet` presence plus `status_gran`.
- Status priority order (low→high), used by the incremental sync to avoid regressing a status: Не назначен <
  В ожидании намыва или промыва < Назначен на намыв < Кр. р. < Намыт < Назначен на промыв < Промыв выполнен
  (see `STATUS_PRIORITY` in `gran_sync.py`).
- `database.py`'s `_run_migration` is how schema changes are rolled out to existing `database.db` files
  (idempotent `ALTER TABLE ... ADD COLUMN`, plus a table-rebuild for the `objects` NOT NULL fix) — add new
  migrations there rather than editing the `CREATE TABLE` statements in a way that breaks existing databases.

### Excel import paths (two distinct pipelines, don't conflate)

1. **"Намыв" workflow** (`gui.py: add_namiv`) — loads a намыв journal via `config_core.core.zagr_file`,
   dedups/pairs rows (`obrabotka_df_posle_zagr`), computes fine-fraction percentages via areometer-temperature
   correction (`rashet_gran` and friends, needs `tarirovki.xlsx`), and writes to `grans` + `grans_raschet`.
2. **"Рабочая сводная" workflow** (`gui.py: NewQDialog2.add_rab_svodn`) — loads sample metadata via
   `config_core.core.zagr_file2` into `probi`/`fizika`, separately computes gran percentages via
   `gransostav.RaschetGranov` (промыв/wash method) into `grans`, and parses status info via
   `gran_sync.parse_rab_svodn_excel`.

Both pipelines rely on `process_multiheader_column` to flatten pandas' multi-row Excel headers before applying
the `config.py` rename dicts, and both are order-sensitive to the rename dict's `.values()` — column lists are
derived from dict values, so key/value pairs must stay in sync with the actual Excel layout.