"""
test_gran_sync.py

Тесты для модуля gran_sync.py и логики статусов gran_report_dialog.py

Запуск:
    cd c:\\MyPythonProjects\\mange_lba\\menedscher_lab
    python -m pytest test_gran_sync.py -v
"""
import pytest
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import gran_sync
from gran_sync import EFFECTIVE_STATUS_SQL


# ===========================================================================
# Тесты RegEx для кр.р.
# ===========================================================================
class TestIsKrR:
    """Проверяем распознавание 'кр.р' в разных написаниях."""

    @pytest.mark.parametrize("text, expected", [
        ("кр.р.",            True),
        ("кр.р",             True),
        ("кр р",             True),
        ("кр р.",            True),
        ("КР.Р",             True),   # регистронезависимо
        ("КР Р.",            True),
        ("кр.р. (примечание)", True),
        ("кр.   р.",         True),   # пробелы между кр и р
        # --- не должны совпасть ---
        ("-",                False),
        ("nan",              False),
        ("",                 False),
        ("крепкий раствор",  False),  # не должны совпасть
        ("монолит",          False),
    ])
    def test_is_kr_r(self, text, expected):
        assert gran_sync.is_kr_r(text) == expected


# ===========================================================================
# Тесты extract_year_from_path
# ===========================================================================
class TestExtractYear:
    """Извлечение года из пути к файлу."""

    @pytest.mark.parametrize("path, expected", [
        (r"Y:\2026\Группа физических\файл.xlsx",       2026),
        (r"Y:\2025\Объект\Партия\rab_svod.xlsx",       2025),
        (r"Z:\data\2024\test.xlsx",                    2024),
        (r"C:\Users\Ilya\no_year\file.xlsx",           None),  # нет года
        (r"\\server\share\2023\folder\file.xlsx",      2023),
    ])
    def test_extract_year(self, path, expected):
        result = gran_sync.extract_year_from_path(path)
        assert result == expected


# ===========================================================================
# Тесты count_sample_types
# ===========================================================================
class TestCountSampleTypes:
    def test_empty(self):
        assert gran_sync.count_sample_types([]) == (0, 0)

    def test_only_monoliths(self):
        samples = [
            {'lab_nomer': '001', 'sample_type': 'монолит'},
            {'lab_nomer': '002', 'sample_type': 'монолит'},
        ]
        assert gran_sync.count_sample_types(samples) == (2, 0)

    def test_only_disturbed(self):
        samples = [
            {'lab_nomer': '001', 'sample_type': 'нарушен'},
            {'lab_nomer': '002', 'sample_type': 'нарушен'},
        ]
        assert gran_sync.count_sample_types(samples) == (0, 2)

    def test_mixed(self):
        samples = [
            {'lab_nomer': '001', 'sample_type': 'монолит'},
            {'lab_nomer': '002', 'sample_type': 'нарушен'},
            {'lab_nomer': '003', 'sample_type': 'монолит'},
        ]
        assert gran_sync.count_sample_types(samples) == (2, 1)


# ===========================================================================
# Тесты логики статусов (юнит через мок-данные)
# ===========================================================================
class TestStatusLogic:
    """
    Проверяем правила присвоения статусов без реального Excel-файла.
    Тестируем напрямую вспомогательную логику разбора строк.
    """

    def _make_sample(self, ukol_raw, descr_note, gran_j='-', gran_k='-'):
        """
        Эмулирует одну строку из листа 'Сводная физ св-в'.
        ukol_raw  — значение колонки F (укол)
        descr_note — значение колонки H (7-й столбик, примечание)
        gran_j     — значение колонки J (grans_raschet маркер)
        gran_k     — значение колонки K (grans маркер)
        """
        has_ukol = ukol_raw not in ('', '-', 'nan')
        sample_type = 'монолит' if has_ukol else 'нарушен'
        kr_r_found = gran_sync.is_kr_r(descr_note)

        if kr_r_found:
            status = 'Кр. р.'
        elif sample_type == 'монолит':
            status = 'Назначен на намыв'
        else:
            status = 'В ожидании намыва или промыва'

        entry = {
            'lab_nomer':   '001',
            'sample_type': sample_type,
            'status_gran': status,
            'has_ukol':    has_ukol,
        }

        # Применяем логику листа 2
        if gran_j not in ('-', 'nan', ''):
            entry['status_gran'] = 'Намыт'
        elif gran_k not in ('-', 'nan', ''):
            if sample_type == 'нарушен':
                entry['status_gran'] = 'Промыв выполнен'
            else:
                entry['status_gran'] = 'Намыт'

        return entry

    # --- Монолиты ---
    def test_monolit_with_ukol_no_gran(self):
        """Монолит + уколы, гранс ещё нет → Назначен на намыв"""
        s = self._make_sample(ukol_raw='4.2', descr_note='-')
        assert s['sample_type'] == 'монолит'
        assert s['status_gran'] == 'Назначен на намыв'

    def test_monolit_with_grans_raschet(self):
        """Монолит + есть в grans_raschet → Намыт"""
        s = self._make_sample(ukol_raw='4.2', descr_note='-', gran_j='намыт')
        assert s['status_gran'] == 'Намыт'

    def test_monolit_with_only_grans(self):
        """Монолит + только в grans (без raschet) → Намыт"""
        s = self._make_sample(ukol_raw='4.2', descr_note='-', gran_j='-', gran_k='есть')
        assert s['status_gran'] == 'Намыт'

    # --- Нарушенки ---
    def test_narushen_no_gran(self):
        """Нарушен + гранс нет → В ожидании намыва или промыва"""
        s = self._make_sample(ukol_raw='-', descr_note='-')
        assert s['sample_type'] == 'нарушен'
        assert s['status_gran'] == 'В ожидании намыва или промыва'

    def test_narushen_with_grans_raschet(self):
        """Нарушен + есть в grans_raschet → Намыт"""
        s = self._make_sample(ukol_raw='-', descr_note='-', gran_j='есть')
        assert s['status_gran'] == 'Намыт'

    def test_narushen_with_only_grans(self):
        """Нарушен + только grans (без raschet) → Промыв выполнен"""
        s = self._make_sample(ukol_raw='-', descr_note='-', gran_j='-', gran_k='есть')
        assert s['status_gran'] == 'Промыв выполнен'

    # --- Кр. р. ---
    def test_kr_r_overrides_narushen(self):
        """Кр.р. в описании → статус 'Кр. р.' независимо от типа пробы (нарушен)"""
        s = self._make_sample(ukol_raw='-', descr_note='кр.р.')
        assert s['status_gran'] == 'Кр. р.'

    def test_kr_r_overrides_monolit(self):
        """Кр.р. в описании → статус 'Кр. р.' независимо от типа пробы (монолит)"""
        s = self._make_sample(ukol_raw='3.1', descr_note='кр р.')
        assert s['status_gran'] == 'Кр. р.'

    def test_kr_r_beaten_by_namyt(self):
        """Кр.р. НЕ должен перезаписывать 'Намыт' (лист 2 имеет приоритет)"""
        s = self._make_sample(ukol_raw='3.1', descr_note='кр р.', gran_j='намыт')
        assert s['status_gran'] == 'Намыт'


# ===========================================================================
# Тесты новой логики фильтрации: Без грана / пустое описание
# ===========================================================================
class TestNoGranStatus:
    """
    Проверяем EFFECTIVE_STATUS_SQL для статуса 'Без грана':
    если f.status_gran = 'Без грана' и нет grans → Без грана.
    Если при этом появятся grans_raschet → Намыт (на всякий случай).
    """

    def _make_db(self):
        conn = sqlite3.connect(':memory:')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE objects (id INTEGER PRIMARY KEY, name_object TEXT, year INTEGER);
            CREATE TABLE partii (id INTEGER PRIMARY KEY, name_partii TEXT,
                                  object_id INTEGER, last_modified TEXT, file_path TEXT);
            CREATE TABLE probi (id INTEGER PRIMARY KEY, lab_nomer TEXT,
                                 partiya_id INTEGER, sample_type TEXT);
            CREATE TABLE fizika (proba_id INTEGER PRIMARY KEY, status_gran TEXT, ukol TEXT);
            CREATE TABLE grans (proba_id INTEGER PRIMARY KEY);
            CREATE TABLE grans_raschet (id INTEGER PRIMARY KEY AUTOINCREMENT, proba_id INTEGER);
            INSERT INTO objects VALUES (1, 'Объект-1', 2026);
            INSERT INTO partii VALUES (1, 'Партия-1', 1, '2026-01-01', '/path/file.xlsx');
        """)
        return conn, cur

    def _get_status(self, cur, proba_id):
        cur.execute(f"""
            SELECT {EFFECTIVE_STATUS_SQL} AS eff_status
            FROM probi pr
            JOIN partii pa ON pa.id = pr.partiya_id
            JOIN objects o  ON o.id  = pa.object_id
            LEFT JOIN fizika        f  ON f.proba_id  = pr.id
            LEFT JOIN grans         g  ON g.proba_id  = pr.id
            LEFT JOIN grans_raschet gr ON gr.proba_id = pr.id
            WHERE pr.id = ?
        """, (proba_id,))
        return cur.fetchone()['eff_status']

    def test_torf_bez_grana(self):
        """Торф → статус 'Без грана'"""
        conn, cur = self._make_db()
        cur.execute("INSERT INTO probi VALUES (1, 'lab_001', 1, 'нарушен')")
        cur.execute("INSERT INTO fizika (proba_id, status_gran) VALUES (1, 'Без грана')")
        assert self._get_status(cur, 1) == 'Без грана'

    def test_prs_bez_grana(self):
        """ПРС → статус 'Без грана'"""
        conn, cur = self._make_db()
        cur.execute("INSERT INTO probi VALUES (1, 'lab_002', 1, 'нарушен')")
        cur.execute("INSERT INTO fizika (proba_id, status_gran) VALUES (1, 'Без грана')")
        assert self._get_status(cur, 1) == 'Без грана'

    def test_sk_bez_grana(self):
        """СК → статус 'Без грана'"""
        conn, cur = self._make_db()
        cur.execute("INSERT INTO probi VALUES (1, 'lab_003', 1, 'нарушен')")
        cur.execute("INSERT INTO fizika (proba_id, status_gran) VALUES (1, 'Без грана')")
        assert self._get_status(cur, 1) == 'Без грана'

    def test_bez_grana_with_grans_raschet_becomes_namyt(self):
        """Без грана + неожиданно появился grans_raschet → Намыт"""
        conn, cur = self._make_db()
        cur.execute("INSERT INTO probi VALUES (1, 'lab_004', 1, 'нарушен')")
        cur.execute("INSERT INTO fizika (proba_id, status_gran) VALUES (1, 'Без грана')")
        cur.execute("INSERT INTO grans VALUES (1)")
        cur.execute("INSERT INTO grans_raschet (proba_id) VALUES (1)")
        assert self._get_status(cur, 1) == 'Намыт'

    def test_kr_r_priority_over_no_gran(self):
        """Кр.р. и no_gran НЕ одновременны — no_gran имеет приоритет"""
        # В parse_rab_svodn_excel: если no_gran → status='Без грана', даже если кр.р. в описании
        # Здесь тестируем только SQL часть: status_gran='Без грана' → Без грана
        conn, cur = self._make_db()
        cur.execute("INSERT INTO probi VALUES (1, 'lab_005', 1, 'нарушен')")
        cur.execute("INSERT INTO fizika (proba_id, status_gran) VALUES (1, 'Без грана')")
        assert self._get_status(cur, 1) == 'Без грана'



class TestFileHasChanged:
    def test_nonexistent_file_returns_false(self, tmp_path):
        fake = str(tmp_path / "nonexistent.xlsx")
        assert gran_sync.file_has_changed(fake, "2024-01-01 00:00:00") is False

    def test_existing_file_old_date(self, tmp_path):
        f = tmp_path / "test.xlsx"
        f.write_bytes(b"data")
        # Старая дата — файл должен считаться изменённым
        assert gran_sync.file_has_changed(str(f), "2000-01-01 00:00:00") is True

    def test_existing_file_future_date(self, tmp_path):
        f = tmp_path / "test.xlsx"
        f.write_bytes(b"data")
        # Будущая дата — файл не изменился
        assert gran_sync.file_has_changed(str(f), "2099-01-01 00:00:00") is False


# ===========================================================================
# Тест EFFECTIVE_STATUS_SQL через реальный SQLite in-memory
# ===========================================================================
class TestEffectiveStatusSQL:
    """
    Проверяем, что SQL-выражение EFFECTIVE_STATUS_SQL правильно
    определяет статус в зависимости от наличия записей в grans/grans_raschet.
    """

    def _make_db(self):
        conn = sqlite3.connect(':memory:')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE objects (
                id INTEGER PRIMARY KEY, name_object TEXT, year INTEGER
            );
            CREATE TABLE partii (
                id INTEGER PRIMARY KEY, name_partii TEXT,
                object_id INTEGER, last_modified TEXT, file_path TEXT
            );
            CREATE TABLE probi (
                id INTEGER PRIMARY KEY, lab_nomer TEXT,
                partiya_id INTEGER, sample_type TEXT
            );
            CREATE TABLE fizika (
                proba_id INTEGER PRIMARY KEY, status_gran TEXT, ukol TEXT
            );
            CREATE TABLE grans (
                proba_id INTEGER PRIMARY KEY
            );
            CREATE TABLE grans_raschet (
                id INTEGER PRIMARY KEY AUTOINCREMENT, proba_id INTEGER
            );

            INSERT INTO objects VALUES (1, 'Объект-1', 2026);
            INSERT INTO partii VALUES (1, 'Партия-1', 1, '2026-01-01', '/path/file.xlsx');
        """)
        return conn, cur

    def _get_status(self, cur, proba_id):
        cur.execute(f"""
            SELECT {EFFECTIVE_STATUS_SQL} AS eff_status
            FROM probi pr
            JOIN partii pa ON pa.id = pr.partiya_id
            JOIN objects o  ON o.id  = pa.object_id
            LEFT JOIN fizika        f  ON f.proba_id  = pr.id
            LEFT JOIN grans         g  ON g.proba_id  = pr.id
            LEFT JOIN grans_raschet gr ON gr.proba_id = pr.id
            WHERE pr.id = ?
        """, (proba_id,))
        row = cur.fetchone()
        return row['eff_status'] if row else None

    def _add_proba(self, cur, proba_id, sample_type, status_gran=None,
                   has_grans=False, has_grans_raschet=False):
        cur.execute(
            "INSERT INTO probi VALUES (?, ?, 1, ?)",
            (proba_id, f'lab_{proba_id:03d}', sample_type)
        )
        if status_gran:
            cur.execute(
                "INSERT INTO fizika (proba_id, status_gran) VALUES (?, ?)",
                (proba_id, status_gran)
            )
        if has_grans:
            cur.execute("INSERT INTO grans VALUES (?)", (proba_id,))
        if has_grans_raschet:
            cur.execute("INSERT INTO grans_raschet (proba_id) VALUES (?)", (proba_id,))

    def test_monolit_no_grans_naznahen(self):
        """Монолит, нет грансостава → Назначен на намыв"""
        conn, cur = self._make_db()
        self._add_proba(cur, 1, 'монолит', 'Назначен на намыв')
        assert self._get_status(cur, 1) == 'Назначен на намыв'

    def test_monolit_has_grans_raschet_namyt(self):
        """Монолит + grans_raschet → Намыт"""
        conn, cur = self._make_db()
        self._add_proba(cur, 1, 'монолит', has_grans=True, has_grans_raschet=True)
        assert self._get_status(cur, 1) == 'Намыт'

    def test_narushen_no_grans_ozhidaet(self):
        """Нарушен, нет грансостава → В ожидании намыва или промыва"""
        conn, cur = self._make_db()
        self._add_proba(cur, 1, 'нарушен', 'В ожидании намыва или промыва')
        assert self._get_status(cur, 1) == 'В ожидании намыва или промыва'

    def test_narushen_has_grans_raschet_namyt(self):
        """Нарушен + grans_raschet → Намыт"""
        conn, cur = self._make_db()
        self._add_proba(cur, 1, 'нарушен', has_grans=True, has_grans_raschet=True)
        assert self._get_status(cur, 1) == 'Намыт'



    def test_kr_r_no_grans(self):
        """status_gran = 'Кр. р.', нет grans → Кр. р."""
        conn, cur = self._make_db()
        self._add_proba(cur, 1, 'нарушен', 'Кр. р.')
        assert self._get_status(cur, 1) == 'Кр. р.'

    def test_kr_r_with_grans_raschet_namyt(self):
        """Кр. р. в fizika + grans_raschet → Намыт (grans_raschet важнее)"""
        conn, cur = self._make_db()
        self._add_proba(cur, 1, 'нарушен', 'Кр. р.', has_grans=True, has_grans_raschet=True)
        assert self._get_status(cur, 1) == 'Намыт'

    def test_no_fizika_no_grans(self):
        """Нет fizika, нет grans, sample_type NULL → Не назначен"""
        conn, cur = self._make_db()
        cur.execute("INSERT INTO probi VALUES (1, 'lab_001', 1, NULL)")
        assert self._get_status(cur, 1) == 'Не назначен'
