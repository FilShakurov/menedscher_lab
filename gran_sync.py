"""
gran_sync.py

Логика парсинга рабочих сводных и синхронизации статусов грансоставов с БД.

Новая логика статусов (определяется при парсинге Excel-файла):
    ┌──────────────┬───────────────────────────────────────────────────────────┐
    │ Тип пробы    │ Правило                                                   │
    ├──────────────┼───────────────────────────────────────────────────────────┤
    │ монолит      │ + есть уколы (ukol) → «Назначен на намыв»                 │
    │ монолит      │ + есть в grans_raschet ИЛИ grans → «Намыт»               │
    │ нарушен      │ начальный → «В ожидании намыва или промыва»              │
    │ нарушен      │ + есть в grans_raschet → «Намыт»                         │
    │ нарушен      │ + только в grans (без grans_raschet) → «Промыв выполнен» │
    │ любой        │ описание содержит кр.р./кр р/кр.р → «Кр. р.»            │
    └──────────────┴───────────────────────────────────────────────────────────┘

Статус «Кр. р.» имеет приоритет выше «Назначен на намыв» но ниже «Намыт».
"""

import os
import re
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# SQL-выражение для вычисления эффективного статуса грансостава
# (используется и в gran_report_dialog, и в тестах)
# ---------------------------------------------------------------------------
EFFECTIVE_STATUS_SQL = """
    CASE
        -- Намыт из журнала И промыв выполнен (оба процесса завершены)
        WHEN gr.proba_id IS NOT NULL AND f.status_gran = 'Промыв выполнен'
            THEN 'Намыт + Промыт'
        -- Намыт из журнала (только намыв)
        WHEN gr.proba_id IS NOT NULL
            THEN 'Намыт'
        -- Промыв выполнен (кол. K листа, нет намыва)
        WHEN f.status_gran = 'Промыв выполнен'
            THEN 'Промыв выполнен'
        -- Назначен на промыв (кол. J листа есть значение, K пустой)
        WHEN f.status_gran = 'Назначен на промыв'
            THEN 'Назначен на промыв'
        -- Без грана (торф/прс/ск)
        WHEN f.status_gran = 'Без грана'
            THEN 'Без грана'
        -- Кр. р.
        WHEN f.status_gran = 'Кр. р.'
            THEN 'Кр. р.'
        -- Монолит, нет данных
        WHEN pr.sample_type = 'монолит'
            THEN 'Назначен на намыв'
        -- Нарушен, нет данных
        WHEN pr.sample_type = 'нарушен'
            THEN 'В ожидании намыва или промыва'
        ELSE 'Не назначен'
    END
"""

RE_KR_R = re.compile(
    r'кр[\.\s]*р[\.\s]?',
    flags=re.IGNORECASE
)


def is_kr_r(text: str) -> bool:
    """Возвращает True если в тексте найдено 'кр.р' / 'кр р' и аналоги."""
    if not text or text in ('-', 'nan'):
        return False
    return bool(RE_KR_R.search(text))


# ---------------------------------------------------------------------------
# Год из пути файла
# ---------------------------------------------------------------------------
def extract_year_from_path(file_path: str) -> int | None:
    """
    Извлекает год из пути вида  Y:\\2026\\...
    Ищет первый 4-значный год между 2000 и 2100.
    """
    parts = Path(file_path).parts  # ('Y:\\', '2026', 'Группа ...', ...)
    for part in parts:
        m = re.fullmatch(r'(20[0-9]{2})', part)
        if m:
            return int(m.group(1))
    return None


# ---------------------------------------------------------------------------
# Работа с датой изменения файла
# ---------------------------------------------------------------------------
def get_file_mtime_str(file_path: str) -> str:
    """Возвращает дату изменения файла в формате 'YYYY-MM-DD HH:MM:SS'."""
    mtime = os.path.getmtime(file_path)
    return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')


def file_has_changed(file_path: str, stored_modified: str) -> bool:
    """Возвращает True, если файл изменился по сравнению с сохранённой датой."""
    if not os.path.exists(file_path):
        return False
    current_mtime = get_file_mtime_str(file_path)
    return current_mtime > stored_modified


# ---------------------------------------------------------------------------
# Парсинг рабочей сводной
# ---------------------------------------------------------------------------
def parse_rab_svodn_excel(file_path: str) -> list:
    """
    Парсит рабочую сводную Excel-файл.

    Лист «Сводная физ св-в»:
        col B (idx 0) — лаб. номер
        col F (idx 4) — укол (если не '-'/пусто → монолит, иначе — нарушен)
        col G (idx 5) — описание разборки (6-й столбик, 0-based 5)
        col H (idx 6) — доп. описание/примечание (7-й столбик, 0-based 6) ← ищем кр.р.

    Лист «Грансост_кр_расс_с_пром»:
        col B (idx 0) — лаб. номер
        col J (idx 1) — намытые (grans_raschet-маркер)
        col K (idx 2) — промытые (только grans-маркер)

    Возвращает список словарей:
        [{'lab_nomer': ..., 'sample_type': ..., 'status_gran': ..., 'has_ukol': bool}, ...]
    """
    samples_dict = {}

    try:
        # --- Лист 1: Сводная физ св-в (B:H, строки с 15-й) ---
        df_main = pd.read_excel(
            file_path,
            sheet_name='Сводная физ св-в',
            engine='openpyxl',
            skiprows=14,
            usecols='B:H'
        )

        for _, row in df_main.iterrows():
            sample_num      = str(row.iloc[0]).strip()   # B — лаб. номер
            sample_type_raw = str(row.iloc[4]).strip()   # F — укол
            sample_descr    = str(row.iloc[5]).strip()   # G — описание пробы
            sample_note     = str(row.iloc[6]).strip() if len(row) > 6 else ''  # H — примечание (7-й столб)

            # Конец данных: lab_nomer NaN или пустой → выходим
            if pd.isna(row.iloc[0]) or sample_num in ('', 'nan'):
                break

            # Строка-заглушка без номера → пропускаем
            if sample_num == '-':
                continue

            # Описание пустое/-/nan → проба ещё не разобрана → пропускаем
            if sample_descr in ('-', 'nan', '') or not sample_descr.strip():
                continue

            # Глыб-щеб 5% → гран вообще не понадобится → пропускаем
            if re.search(r'глыб[-\s.,]*щеб.*5%', sample_descr, re.IGNORECASE):
                continue

            # Дубль → пропускаем
            if 'дубль' in sample_descr.lower():
                continue

            # Тип пробы: пустой укол = нарушен
            has_ukol = sample_type_raw not in ('', '-', 'nan')
            sample_type = 'монолит' if has_ukol else 'нарушен'

            # Торф, ПРС, СК → добавляем в БД, но со статусом 'Без грана'
            no_gran = bool(
                re.search(r'\bторф\b', sample_descr, re.IGNORECASE) or
                re.search(r'\bпрс\b',  sample_descr, re.IGNORECASE) or
                re.search(r'\bск\b',   sample_descr, re.IGNORECASE)
            )

            # Кр. р. — проверяем 7-й столбик (H, примечание)
            kr_r_found = is_kr_r(sample_note) or is_kr_r(sample_descr)

            # Начальный статус (приоритет: Без грана > Кр.р. > обычные)
            if no_gran:
                status = 'Без грана'
            elif kr_r_found:
                status = 'Кр. р.'
            elif sample_type == 'монолит':
                status = 'Назначен на намыв'
            else:
                status = 'В ожидании намыва или промыва'

            samples_dict[sample_num] = {
                'lab_nomer':   sample_num,
                'sample_type': sample_type,
                'status_gran': status,
                'has_ukol':    has_ukol,
            }

    except Exception as e:
        print(f"[gran_sync] Ошибка при чтении листа 'Сводная физ св-в' из {file_path}: {e}")
        return []


    # --- Лист 2: Грансост_кр_расс_с_пром (B, J, K, строки с 10-й) ---
    #
    # Кол. B (iloc[0]) — лаб. номер
    # Кол. J (iloc[1]) — «Назначен на промыв»:  есть значение → проба попала в очередь, промыв ещё не выполнен
    # Кол. K (iloc[2]) — «Промыв выполнен»: есть значение → промыв сделан
    #
    # «Намыт» берётся ИСКЛЮЧИТЕЛЬНО из журналов намыва (grans_raschet в БД) — не из этого листа
    try:
        df_gran = pd.read_excel(
            file_path,
            sheet_name='Грансост_кр_расс_с_пром',
            engine='openpyxl',
            skiprows=9,
            usecols='B,J,K'
        )
        df_gran.iloc[:, 0] = df_gran.iloc[:, 0].ffill()

        for _, row in df_gran.iterrows():
            sample_num_gran = str(row.iloc[0]).strip()
            if sample_num_gran not in samples_dict:
                continue

            col_j = str(row.iloc[1]).strip()  # J — «Назначен на промыв»
            col_k = str(row.iloc[2]).strip()  # K — «Промыв выполнен»

            entry  = samples_dict[sample_num_gran]
            stype  = entry['sample_type']
            cur_st = entry['status_gran']  # текущий статус (из листа 1)

            # Если ячейка пустая или содержит 0 (результат пустой формулы), считаем её пустой
            ignored_vals = ('-', 'nan', '', '0', '0.0', '0,0', 'None')

            if col_k not in ignored_vals:
                # K есть → Промыв выполнен
                # (в EFFECTIVE_STATUS_SQL: если ещё и в grans_raschet — покажет 'Намыт + Промыт')
                entry['status_gran'] = 'Промыв выполнен'
            elif col_j not in ignored_vals:
                # J есть, K пустой → Назначен на промыв
                # (проба попала в очередь, но промыв ещё не выполнен)
                entry['status_gran'] = 'Назначен на промыв'
            # если оба '-' — проба есть на листе, но ещё не обработана — статус остаётся из листа 1

    except Exception:
        pass  # Листа может не быть — нормально

    return list(samples_dict.values())


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------
def count_sample_types(samples: list) -> tuple[int, int]:
    """Считает количество монолитов и нарушенок."""
    monoliths = sum(1 for s in samples if s.get('sample_type') == 'монолит')
    disturbed = sum(1 for s in samples if s.get('sample_type') == 'нарушен')
    return monoliths, disturbed


# ---------------------------------------------------------------------------
# Синхронизация с БД
# ---------------------------------------------------------------------------
def sync_all_files(db, full_rescan: bool = False) -> str:
    """
    Обходит все партии с сохранёнными путями к файлам.
    Проверяет изменилась ли дата модификации файла; если да — обновляет БД.

    full_rescan=False → инкрементальный (только улучшает статусы).
    full_rescan=True  → полный перепарс с перезаписью статусов.

    Возвращает строку с итоговым отчётом.
    """
    partii = db.get_all_partii_with_files()
    if not partii:
        return "Нет партий с сохранёнными путями к файлам."

    report_lines = []
    checked = updated = skipped = missing = 0

    for partiya in partii:
        partiya_id    = partiya['id']
        name_partii   = partiya['name_partii']
        file_path     = partiya['file_path']
        last_modified = partiya['last_modified']
        checked += 1

        if not os.path.exists(file_path):
            report_lines.append(f"⚠ [{name_partii}] Файл не найден: {file_path}")
            missing += 1
            continue

        current_mtime = get_file_mtime_str(file_path)
        if not full_rescan and last_modified and current_mtime <= last_modified:
            skipped += 1
            continue

        samples = parse_rab_svodn_excel(file_path)
        if not samples:
            report_lines.append(f"⚠ [{name_partii}] Не удалось прочитать файл или он пустой.")
            continue

        monoliths, disturbed = count_sample_types(samples)

        if full_rescan:
            db.update_probi_sample_type_and_status(partiya_id, samples)
            mode_str = "полный перепарс"
        else:
            db.update_probi_status_gran_incremental(partiya_id, samples)
            mode_str = "инкрементально"

        db.update_partii_file_info(partiya_id, file_path, current_mtime, monoliths, disturbed)
        report_lines.append(
            f"✓ [{name_partii}] Обновлено ({mode_str}): "
            f"{len(samples)} проб (монолиты: {monoliths}, нарушены: {disturbed})"
        )
        updated += 1

    summary = (
        f"Проверено: {checked} | Обновлено: {updated} | "
        f"Без изменений: {skipped} | Файлы не найдены: {missing}"
    )
    report_lines.insert(0, summary)
    return "\n".join(report_lines)
