import os
import re
import pandas as pd
from datetime import datetime
from pathlib import Path


# --- Логика парсинга рабочих сводных (из manage_grane p2) ---

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


def parse_rab_svodn_excel(file_path: str) -> list:
    """
    Парсит рабочую сводную Excel-файл.
    Читает лист 'Сводная физ св-в' для определения sample_type,
    затем лист 'Грансост_кр_расс_с_пром' для определения status_gran.

    Возвращает список словарей:
        [{'lab_nomer': ..., 'sample_type': ..., 'status_gran': ...}, ...]
    """
    samples_dict = {}

    try:
        # --- Лист 1: Сводная физ св-в (B:G, строки с 15-й) ---
        df_main = pd.read_excel(
            file_path,
            sheet_name='Сводная физ св-в',
            engine='openpyxl',
            skiprows=14,
            usecols="B:G"
        )

        for _, row in df_main.iterrows():
            sample_num = str(row.iloc[0]).strip()        # Колонка B
            sample_type_raw = str(row.iloc[4]).strip()   # Колонка F
            sample_discr = str(row.iloc[5]).strip()       # Колонка G

            # Отсекаем ненужные грунты и дубли
            if (re.search(r'глыб[-\s.,]*щеб.*5%', sample_discr, flags=re.IGNORECASE) or
                    re.search(r'\bпрс', sample_discr, flags=re.IGNORECASE) or
                    sample_discr == '-' or
                    re.search(r'\bторф', sample_discr, flags=re.IGNORECASE) or
                    'дубль' in sample_discr.lower() or
                    sample_num == '-' or
                    re.search(r'\bск', sample_discr, flags=re.IGNORECASE)):
                continue

            # Определяем тип пробы: если колонка F пустая или '-' — нарушен, иначе монолит
            sample_type = 'нарушен' if (
                sample_type_raw == '-' or sample_type_raw == '' or sample_type_raw == 'nan'
            ) else 'монолит'

            if pd.isna(row.iloc[0]) or sample_num == 'nan' or not sample_num:
                break

            # Начальный статус по типу пробы
            if sample_type == 'монолит':
                status = 'Назначен на намыв'
            else:
                status = 'В ожидании намыва или промыва'

            samples_dict[sample_num] = {
                'lab_nomer': sample_num,
                'sample_type': sample_type,
                'status_gran': status
            }

    except Exception as e:
        print(f"[gran_sync] Ошибка при чтении листа 'Сводная физ св-в' из {file_path}: {e}")
        return []

    # --- Лист 2: Грансост_кр_расс_с_пром (B, J, K, строки с 10-й) ---
    try:
        df_gran = pd.read_excel(
            file_path,
            sheet_name='Грансост_кр_расс_с_пром',
            engine='openpyxl',
            skiprows=9,
            usecols="B,J,K"
        )
        df_gran.iloc[:, 0] = df_gran.iloc[:, 0].ffill()  # Протягиваем номера проб

        for _, row in df_gran.iterrows():
            sample_num_gran = str(row.iloc[0]).strip()
            if sample_num_gran not in samples_dict:
                continue

            col_j = str(row.iloc[1]).strip()  # Колонка J
            col_k = str(row.iloc[2]).strip()  # Колонка K

            if col_k not in ('-', 'nan', ''):
                samples_dict[sample_num_gran]['status_gran'] = 'Промыв выполнен'
            elif col_j not in ('-', 'nan', ''):
                samples_dict[sample_num_gran]['status_gran'] = 'Назначен на промыв'
            elif samples_dict[sample_num_gran]['sample_type'] == 'монолит':
                samples_dict[sample_num_gran]['status_gran'] = 'Назначен на намыв'

    except Exception:
        pass  # Листа грансостава может не быть — это нормально

    return list(samples_dict.values())


def count_sample_types(samples):
    """Считает количество монолитов и нарушенок в списке проб."""
    monoliths = sum(1 for s in samples if s.get('sample_type') == 'монолит')
    disturbed = sum(1 for s in samples if s.get('sample_type') == 'нарушен')
    return monoliths, disturbed


# --- Синхронизация с БД ---

def sync_all_files(db, full_rescan=False):
    """
    Обходит все партии с сохранёнными путями к файлам.
    Проверяет, изменился ли файл, и если да — обновляет данные в БД.

    Режимы:
        full_rescan=False (по умолчанию) — инкрементальный:
            добавляет только улучшенные статусы, не откатывает назад.
        full_rescan=True — полный:
            полностью перепарсивает файл и перезаписывает все статусы.

    Возвращает строку с итоговым отчётом.
    """
    partii = db.get_all_partii_with_files()
    if not partii:
        return "Нет партий с сохранёнными путями к файлам."

    report_lines = []
    checked = 0
    updated = 0
    skipped = 0
    missing = 0

    for partiya in partii:
        partiya_id    = partiya['id']
        name_partii   = partiya['name_partii']
        file_path     = partiya['file_path']
        last_modified = partiya['last_modified']

        checked += 1

        # Проверяем существование файла
        if not os.path.exists(file_path):
            report_lines.append(f"⚠ [{name_partii}] Файл не найден: {file_path}")
            missing += 1
            continue

        # Проверяем изменился ли файл (в инкрементальном режиме)
        current_mtime = get_file_mtime_str(file_path)
        if not full_rescan and last_modified and current_mtime <= last_modified:
            skipped += 1
            continue

        # Парсим файл
        samples = parse_rab_svodn_excel(file_path)
        if not samples:
            report_lines.append(f"⚠ [{name_partii}] Не удалось прочитать файл или он пустой.")
            continue

        monoliths, disturbed = count_sample_types(samples)

        if full_rescan:
            # Полный перепарс — перезаписываем все статусы
            db.update_probi_sample_type_and_status(partiya_id, samples)
            mode_str = "полный перепарс"
        else:
            # Инкрементальный — только улучшаем статусы
            db.update_probi_status_gran_incremental(partiya_id, samples)
            mode_str = "инкрементально"

        # Обновляем дату файла и счётчики в партии
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
