import sqlite3
from datetime import datetime
import pandas as pd
from config_core import config


class Database:
    def __init__(self, db_file):
        self.db_file = db_file
        self.init_database()

    def get_connection(self):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn

    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()
#Добавил year - задается (берётся из пути Y:\2026\...), а name_ilya - парсится из названий папок на диске
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS objects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_object TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                year INTEGER,
                name_ilya TEXT
            )
        """)
# Добавил party_number - последние цифры раб свод экселя,  monoliths_count, disturbed_count, file_path, last_modified
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS partii (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_partii TEXT NOT NULL,
                object_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                party_number TEXT,
                monoliths_count INTEGER DEFAULT 0,
                disturbed_count INTEGER DEFAULT 0,
                file_path TEXT UNIQUE,
                last_modified TEXT,
                
                FOREIGN KEY(object_id) REFERENCES objects(id)
                    ON DELETE CASCADE
                )
        """)
#Добавил sample_type - монолит или нарушка, UNIQUE(partiya_id, lab_nomer) - чтобы избежать дублей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS probi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lab_nomer TEXT NOT NULL UNIQUE,
                partiya_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                sample_type TEXT,
                UNIQUE(partiya_id, lab_nomer),
                
                FOREIGN KEY(partiya_id) REFERENCES partii(id)
                    ON DELETE CASCADE
                )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS grans (
                proba_id INTEGER PRIMARY KEY,
                gran_10 REAL,
                gran_5_10 REAL,
                gran_5_2 REAL,
                gran_2_1 REAL,
                gran_1_0_5 REAL,
                gran_0_5_0_25 REAL,
                gran_0_25_0_10 REAL,
                gran_0_10_0_05 REAL,
                gran_0_05_0_01 REAL,
                gran_0_01_0_002 REAL,
                gran_0_002 REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            
                FOREIGN KEY(proba_id) REFERENCES probi(id)
                    ON DELETE CASCADE
            )
        """)

        cursor.execute("""  
            CREATE TABLE IF NOT EXISTS grans_archive (
                archive_id          INTEGER PRIMARY KEY AUTOINCREMENT,
                proba_id            INTEGER NOT NULL,
                gran_10             REAL,
                gran_5_10           REAL,
                gran_5_2            REAL,
                gran_2_1            REAL,
                gran_1_0_5          REAL,
                gran_0_5_0_25       REAL,
                gran_0_25_0_10      REAL,
                gran_0_10_0_05      REAL,
                gran_0_05_0_01      REAL,
                gran_0_01_0_002     REAL,
                gran_0_002          REAL,
                created_at          TEXT,
                archived_at         TEXT NOT NULL
            );       
        """)

        cursor.execute("""  
            CREATE TABLE IF NOT EXISTS grans_raschet (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                proba_id                INTEGER NOT NULL,
                kolba_naveska_first     REAL,
                kolba_naveska_last      REAL,
                areometr_first          REAL,
                zamer_temp_1_first      REAL,
                zamer_temp_1_last       REAL,
                zamer_temp_2_first      REAL,
                zamer_temp_2_last       REAL,
                zamer_temp_3_first      REAL,
                zamer_temp_3_last       REAL,
                gran_10_first           REAL,
                gran_5_10_first         REAL,
                gran_5_2_first          REAL,
                gran_2_1_first          REAL,
                gran_1_0_5_first        REAL,
                gran_0_5_0_25_first     REAL,
                gran_0_25_0_10_first    REAL,
                created_at              TEXT DEFAULT CURRENT_TIMESTAMP
            );       
        """)
#Добавил status_gran
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fizika (
                proba_id INTEGER PRIMARY KEY,
                ukol TEXT,
                opisanie_razbor TEXT,
                wlashn REAL,
                plotn REAL,
                udelka REAL,
                organika REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                status_gran TEXT DEFAULT 'Не назначен',
                
                FOREIGN KEY(proba_id) REFERENCES probi(id)
                    ON DELETE CASCADE
            )
        """)

        # --- Безопасная миграция: добавляем колонки если их ещё нет ---
        self._run_migration(conn)

        conn.commit()
        conn.close()

    def _run_migration(self, conn):
        """Добавляет отсутствующие колонки в существующие таблицы (идемпотентная миграция)."""
        cursor = conn.cursor()

        # --- Миграция таблицы objects ---
        # SQLite не позволяет DROP COLUMN NOT NULL напрямую, используем пересоздание таблицы
        cursor.execute("PRAGMA table_info(objects)")
        obj_cols = {row[1]: row[3] for row in cursor.fetchall()}  # name -> notnull
        # Если year или name_ilya помечены NOT NULL — пересоздаём таблицу
        if obj_cols.get('year', 0) == 1 or obj_cols.get('name_ilya', 0) == 1:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS objects_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name_object TEXT NOT NULL UNIQUE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    year INTEGER,
                    name_ilya TEXT
                )
            """)
            cursor.execute("""
                INSERT OR IGNORE INTO objects_new (id, name_object, created_at, year, name_ilya)
                SELECT id, name_object, created_at, year, name_ilya FROM objects
            """)
            cursor.execute("DROP TABLE objects")
            cursor.execute("ALTER TABLE objects_new RENAME TO objects")

        # --- Миграция таблицы partii ---
        cursor.execute("PRAGMA table_info(partii)")
        existing_cols = {row[1] for row in cursor.fetchall()}

        if 'file_path' not in existing_cols:
            cursor.execute("ALTER TABLE partii ADD COLUMN file_path TEXT")
        if 'last_modified' not in existing_cols:
            cursor.execute("ALTER TABLE partii ADD COLUMN last_modified TEXT")
        if 'party_number' not in existing_cols:
            cursor.execute("ALTER TABLE partii ADD COLUMN party_number TEXT")
        if 'monoliths_count' not in existing_cols:
            cursor.execute("ALTER TABLE partii ADD COLUMN monoliths_count INTEGER DEFAULT 0")
        if 'disturbed_count' not in existing_cols:
            cursor.execute("ALTER TABLE partii ADD COLUMN disturbed_count INTEGER DEFAULT 0")

        # --- Миграция таблицы probi ---
        cursor.execute("PRAGMA table_info(probi)")
        existing_cols_probi = {row[1] for row in cursor.fetchall()}
        if 'sample_type' not in existing_cols_probi:
            cursor.execute("ALTER TABLE probi ADD COLUMN sample_type TEXT")


    """Методы для объекта"""
    def add_object(self, name_object, year=None, name_ilya=None):
        """Добавляет объект. year — год (напр. 2026), name_ilya — папка на диске."""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            current_time = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO objects (name_object, created_at, year, name_ilya)
                VALUES (?, ?, ?, ?)
            """, (name_object, current_time, year, name_ilya))

            conn.commit()

        except sqlite3.Error:
            conn.rollback()
            raise

        finally:
            conn.close()

    def delete_object(self, object_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM objects WHERE id = ?', (object_id,))
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            raise
        finally:
            conn.close()

    def show_all_objects(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT id, name_object FROM objects ORDER BY created_at DESC')
            list_objects = cursor.fetchall()
            return list_objects

        except sqlite3.Error:
            raise
        finally:
            conn.close()

    def name_object_by_id(self, object_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT name_object FROM objects WHERE id = ?', (object_id,))
            name_object = cursor.fetchone()
            return name_object

        except sqlite3.Error:
            raise
        finally:
            conn.close()

    def id_object_by_name(self, name_object):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT id FROM objects WHERE name_object = ?', (name_object,))
            id_object = cursor.fetchone()
            return id_object

        except sqlite3.Error:
            raise
        finally:
            conn.close()

    def date_object_by_name(self, name_object):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT created_at FROM objects WHERE name_object = ?', (name_object,))
            date_object = cursor.fetchone()
            return date_object

        except sqlite3.Error:
            raise
        finally:
            conn.close()

    def add_partiya(self, name_partii, object_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            current_time = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO partii (name_partii, object_id, created_at)
                VALUES (?, ?, ?)
            """, (name_partii, object_id, current_time))

            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            raise
        finally:
            conn.close()

    def delete_partiya(self, partiya_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM partii WHERE id = ?', (partiya_id,))
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            raise
        finally:
            conn.close()

    def show_all_partii_by_object(self, object_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT * FROM partii WHERE object_id = ?', (object_id,))
            list_partii = cursor.fetchall()

            return list_partii

        except sqlite3.Error:
            raise
        finally:
            conn.close()

    def add_probi(self, df, partiya_id):

        df_to_save = df[['lab_nomer']].copy()

        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            points = [
                (row.lab_nomer, partiya_id)
                for row in df_to_save.itertuples(index=False)
            ]

            cursor.executemany("""  
                INSERT INTO probi (lab_nomer, partiya_id)            
                VALUES (?, ?)
                ON CONFLICT(lab_nomer) DO UPDATE SET partiya_id = excluded.partiya_id        
            """, points)

            conn.commit()

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

    def save_grans_bulk_by_lab_nomer(self, df):
        conn = self.get_connection()

        try:
            df_probi = pd.read_sql_query(
                "SELECT id AS proba_id, lab_nomer FROM probi",
                conn
            )

            df_merged = df.merge(df_probi, on='lab_nomer', how='left')

            if df_merged['proba_id'].isna().any():
                missing = df_merged.loc[df_merged['proba_id'].isna(), 'lab_nomer'].tolist()
                raise ValueError(f'В базе данных нет лабораторных номеров: {missing}')

            df_to_save = df_merged[config.COLUMNS_GRAN_BD].copy()

            current_time = datetime.now().isoformat()

            rows = [
                (
                    int(row.proba_id),
                    row.gran_10,
                    row.gran_5_10,
                    row.gran_5_2,
                    row.gran_2_1,
                    row.gran_1_0_5,
                    row.gran_0_5_0_25,
                    row.gran_0_25_0_10,
                    row.gran_0_10_0_05,
                    row.gran_0_05_0_01,
                    row.gran_0_01_0_002,
                    row.gran_0_002,
                    current_time
                )
                for row in df_to_save.itertuples(index=False)
            ]

            cursor = conn.cursor()
            conn.execute("BEGIN")

            cursor.execute("DROP TABLE IF EXISTS temp_grans_import")

            cursor.execute("""
                CREATE TEMP TABLE temp_grans_import (
                    proba_id            INTEGER PRIMARY KEY,
                    gran_10             REAL,
                    gran_5_10           REAL,
                    gran_5_2            REAL,
                    gran_2_1            REAL,
                    gran_1_0_5          REAL,
                    gran_0_5_0_25       REAL,
                    gran_0_25_0_10      REAL,
                    gran_0_10_0_05      REAL,
                    gran_0_05_0_01      REAL,
                    gran_0_01_0_002     REAL,
                    gran_0_002          REAL,
                    created_at          TEXT
                )
            """)

            cursor.executemany("""
                INSERT INTO temp_grans_import (
                    proba_id, gran_10, gran_5_10, gran_5_2, gran_2_1, gran_1_0_5,
                    gran_0_5_0_25, gran_0_25_0_10, gran_0_10_0_05, gran_0_05_0_01,
                    gran_0_01_0_002, gran_0_002, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)

            cursor.execute("""
                INSERT INTO grans_archive (
                    proba_id, gran_10, gran_5_10, gran_5_2, gran_2_1, gran_1_0_5,
                    gran_0_5_0_25, gran_0_25_0_10, gran_0_10_0_05, gran_0_05_0_01,
                    gran_0_01_0_002, gran_0_002, created_at, archived_at
                )
                SELECT
                    g.proba_id, g.gran_10, g.gran_5_10, g.gran_5_2, g.gran_2_1, g.gran_1_0_5,
                    g.gran_0_5_0_25, g.gran_0_25_0_10, g.gran_0_10_0_05, g.gran_0_05_0_01,
                    g.gran_0_01_0_002, g.gran_0_002, g.created_at, ?
                FROM grans g
                INNER JOIN temp_grans_import t
                    ON t.proba_id = g.proba_id
            """, (current_time,))

            cursor.execute("""
                INSERT INTO grans (
                    proba_id, gran_10, gran_5_10, gran_5_2, gran_2_1, gran_1_0_5,
                    gran_0_5_0_25, gran_0_25_0_10, gran_0_10_0_05, gran_0_05_0_01,
                    gran_0_01_0_002, gran_0_002, created_at
                )
                SELECT
                    proba_id, gran_10, gran_5_10, gran_5_2, gran_2_1, gran_1_0_5,
                    gran_0_5_0_25, gran_0_25_0_10, gran_0_10_0_05, gran_0_05_0_01,
                    gran_0_01_0_002, gran_0_002, created_at
                FROM temp_grans_import
                WHERE true
                ON CONFLICT(proba_id) DO UPDATE SET
                    gran_10 = excluded.gran_10,
                    gran_5_10 = excluded.gran_5_10,
                    gran_5_2 = excluded.gran_5_2,
                    gran_2_1 = excluded.gran_2_1,
                    gran_1_0_5 = excluded.gran_1_0_5,
                    gran_0_5_0_25 = excluded.gran_0_5_0_25,
                    gran_0_25_0_10 = excluded.gran_0_25_0_10,
                    gran_0_10_0_05 = excluded.gran_0_10_0_05,
                    gran_0_05_0_01 = excluded.gran_0_05_0_01,
                    gran_0_01_0_002 = excluded.gran_0_01_0_002,
                    gran_0_002 = excluded.gran_0_002,
                    created_at = excluded.created_at
            """)

            cursor.execute("DROP TABLE IF EXISTS temp_grans_import")

            conn.commit()

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

    def save_grans_raschet_bulk_by_lab_nomer(self, df_raschet):
        conn = self.get_connection()

        try:
            df_probi = pd.read_sql_query(
                "SELECT id AS proba_id, lab_nomer FROM probi",
                conn
            )

            df_merged = df_raschet.merge(df_probi, on='lab_nomer', how='left')

            if df_merged['proba_id'].isna().any():
                missing = df_merged.loc[df_merged['proba_id'].isna(), 'lab_nomer'].tolist()
                raise ValueError(f'В базе данных нет лабораторных номеров: {missing}')

            current_time = datetime.now().isoformat()

            rows = [
                (
                    int(row.proba_id),
                    row.kolba_naveska_first,
                    row.kolba_naveska_last,
                    row.areometr_first,
                    row.zamer_temp_1_first,
                    row.zamer_temp_1_last,
                    row.zamer_temp_2_first,
                    row.zamer_temp_2_last,
                    row.zamer_temp_3_first,
                    row.zamer_temp_3_last,
                    row.gran_10_first,
                    row.gran_5_10_first,
                    row.gran_5_2_first,
                    row.gran_2_1_first,
                    row.gran_1_0_5_first,
                    row.gran_0_5_0_25_first,
                    row.gran_0_25_0_10_first,
                    current_time
                )
                for row in df_merged.itertuples(index=False)
            ]

            cursor = conn.cursor()
            conn.execute("BEGIN")

            # # Удаляем старые расчеты намыва для этих проб (чтобы перезаписать гран полностью)
            # proba_ids_to_delete = [row[0] for row in rows]
            # if proba_ids_to_delete:
            #     placeholders = ','.join('?' * len(proba_ids_to_delete))
            #     cursor.execute(f"DELETE FROM grans_raschet WHERE proba_id IN ({placeholders})", proba_ids_to_delete)

            cursor.executemany("""
                INSERT INTO grans_raschet (
                    proba_id,
                    kolba_naveska_first,
                    kolba_naveska_last,
                    areometr_first,
                    zamer_temp_1_first,
                    zamer_temp_1_last,
                    zamer_temp_2_first,
                    zamer_temp_2_last,
                    zamer_temp_3_first,
                    zamer_temp_3_last,
                    gran_10_first,
                    gran_5_10_first,
                    gran_5_2_first,
                    gran_2_1_first,
                    gran_1_0_5_first,
                    gran_0_5_0_25_first,
                    gran_0_25_0_10_first,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)

            conn.commit()

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

    def save_fizika_bulk_by_lab_nomer(self, df):
        conn = self.get_connection()

        try:
            df_probi = pd.read_sql_query(
                "SELECT id AS proba_id, lab_nomer FROM probi",
                conn
            )

            df_merged = df.merge(df_probi, on='lab_nomer', how='left')

            if df_merged['proba_id'].isna().any():
                missing = df_merged[df_merged['proba_id'].isna()]['lab_nomer'].tolist()
                raise ValueError(f'В базе данных нет лабораторных номеров: {missing}')

            columns = ['proba_id', 'ukol', 'opisanie_razbor', 'wlashn', 'plotn', 'udelka', 'organika']
            df_to_save = df_merged[columns].copy()

            cursor = conn.cursor()
            current_time = datetime.now().isoformat()

            rows = [
                (
                    int(row.proba_id),
                    row.ukol,
                    row.opisanie_razbor,
                    row.wlashn,
                    row.plotn,
                    row.udelka,
                    row.organika,
                    current_time
                )
                for row in df_to_save.itertuples(index=False)
            ]

            cursor.executemany("""
                INSERT INTO fizika (
                    proba_id, ukol, opisanie_razbor, wlashn, plotn, udelka, organika, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(proba_id) DO UPDATE SET
                    ukol = excluded.ukol,
                    opisanie_razbor = excluded.opisanie_razbor,
                    wlashn = excluded.wlashn,
                    plotn = excluded.plotn,
                    udelka = excluded.udelka,
                    organika = excluded.organika
            """, rows)

            conn.commit()

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

    def get_gran_data_by_party_name(self, party_name):
        conn = self.get_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                p.lab_nomer AS proba_lab_nomer,
                g.gran_10, g.gran_5_10, g.gran_5_2, g.gran_2_1, g.gran_1_0_5, g.gran_0_5_0_25,
                g.gran_0_25_0_10, g.gran_0_10_0_05, g.gran_0_05_0_01, g.gran_0_01_0_002, g.gran_0_002
            FROM partii pa
            JOIN probi p ON pa.id = p.partiya_id
            JOIN grans g ON p.id = g.proba_id
            WHERE pa.name_partii = ?
        """

        cursor.execute(query, (party_name,))
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_gran_data_by_party_id(self, party_id):
        conn = self.get_connection()

        query = """
            SELECT 
                p.lab_nomer AS proba_lab_nomer,
                g.gran_10, g.gran_5_10, g.gran_5_2, g.gran_2_1, g.gran_1_0_5, g.gran_0_5_0_25,
                g.gran_0_25_0_10, g.gran_0_10_0_05, g.gran_0_05_0_01, g.gran_0_01_0_002, g.gran_0_002
            FROM probi p
            JOIN grans g ON p.id = g.proba_id
            WHERE p.partiya_id = ?
        """

        # read_sql_query сам выполнит запрос и вернёт DataFrame
        df = pd.read_sql_query(query, conn, params=(party_id,))

        conn.close()
        return df

    def get_poln_info_data_by_party_id(self, party_id):
        conn = self.get_connection()

        query = """
            SELECT 
            * 
            FROM probi p
                LEFT JOIN fizika f ON p.id = f.proba_id
                LEFT JOIN grans g ON p.id = g.proba_id
            WHERE p.partiya_id = ?;
        """

        # read_sql_query сам выполнит запрос и вернёт DataFrame
        df = pd.read_sql_query(query, conn, params=(party_id,))

        conn.close()
        return df

    # --- Методы для работы с путями файлов партий и статусами грансоставов ---

    def update_partii_file_info(self, partiya_id, file_path, last_modified, monoliths_count=None, disturbed_count=None):
        """Сохраняет путь к файлу и дату его изменения для партии."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if monoliths_count is not None and disturbed_count is not None:
                cursor.execute("""
                    UPDATE partii
                    SET file_path = ?, last_modified = ?, monoliths_count = ?, disturbed_count = ?
                    WHERE id = ?
                """, (file_path, last_modified, monoliths_count, disturbed_count, partiya_id))
            else:
                cursor.execute("""
                    UPDATE partii
                    SET file_path = ?, last_modified = ?
                    WHERE id = ?
                """, (file_path, last_modified, partiya_id))
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            raise
        finally:
            conn.close()

    def update_partii_last_modified(self, partiya_id, last_modified):
        """Обновляет дату последнего изменения файла партии."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE partii SET last_modified = ? WHERE id = ?",
                (last_modified, partiya_id)
            )
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_all_partii_with_files(self):
        """Возвращает все партии, у которых сохранён путь к файлу."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT id, name_partii, file_path, last_modified, object_id
                FROM partii
                WHERE file_path IS NOT NULL AND file_path != ''
            """)
            return cursor.fetchall()
        except sqlite3.Error:
            raise
        finally:
            conn.close()

    def get_probi_by_partii(self, partiya_id):
        """Возвращает все пробы партии с их текущим статусом грансостава."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT p.id, p.lab_nomer, p.sample_type, f.status_gran
                FROM probi p
                LEFT JOIN fizika f ON p.id = f.proba_id
                WHERE p.partiya_id = ?
            """, (partiya_id,))
            return cursor.fetchall()
        except sqlite3.Error:
            raise
        finally:
            conn.close()

    def update_probi_sample_type_and_status(self, partiya_id, sample_updates):
        """Обновляет sample_type в probi и status_gran в fizika для списка проб.
        
        sample_updates: список dict {lab_nomer, sample_type, status_gran}
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            conn.execute("BEGIN")
            for s in sample_updates:
                # Обновляем sample_type в probi
                cursor.execute("""
                    UPDATE probi SET sample_type = ?
                    WHERE lab_nomer = ? AND partiya_id = ?
                """, (s['sample_type'], s['lab_nomer'], partiya_id))

                # Получаем proba_id
                cursor.execute(
                    "SELECT id FROM probi WHERE lab_nomer = ? AND partiya_id = ?",
                    (s['lab_nomer'], partiya_id)
                )
                row = cursor.fetchone()
                if not row:
                    continue
                proba_id = row[0]

                # Обновляем или вставляем статус в fizika
                cursor.execute("""
                    INSERT INTO fizika (proba_id, status_gran)
                    VALUES (?, ?)
                    ON CONFLICT(proba_id) DO UPDATE SET status_gran = excluded.status_gran
                """, (proba_id, s['status_gran']))

            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            raise
        finally:
            conn.close()

    def update_probi_status_gran_incremental(self, partiya_id, status_updates):
        """Инкрементально обновляет только УЛУЧШЕННЫЕ статусы (не откатывает назад).
        
        status_updates: список dict {lab_nomer, status_gran}
        Порядок приоритета статусов (выше = лучше):
          Промыв выполнен > Назначен на промыв > Намыт > Назначен на намыв > В ожидании намыва или промыва > Не назначен
        """
        STATUS_PRIORITY = {
            'Не назначен': 0,
            'В ожидании намыва или промыва': 1,
            'Назначен на намыв': 2,
            'Кр. р.': 3,
            'Намыт': 4,
            'Назначен на промыв': 5,
            'Промыв выполнен': 6,
        }
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            conn.execute("BEGIN")
            for s in status_updates:
                cursor.execute(
                    "SELECT id FROM probi WHERE lab_nomer = ? AND partiya_id = ?",
                    (s['lab_nomer'], partiya_id)
                )
                row = cursor.fetchone()
                if not row:
                    continue
                proba_id = row[0]

                # Получаем текущий статус
                cursor.execute("SELECT status_gran FROM fizika WHERE proba_id = ?", (proba_id,))
                existing = cursor.fetchone()
                current_status = existing[0] if existing else 'Не назначен'

                new_status = s['status_gran']
                # Обновляем только если новый статус «лучше» текущего
                if STATUS_PRIORITY.get(new_status, 0) > STATUS_PRIORITY.get(current_status, 0):
                    cursor.execute("""
                        INSERT INTO fizika (proba_id, status_gran)
                        VALUES (?, ?)
                        ON CONFLICT(proba_id) DO UPDATE SET status_gran = excluded.status_gran
                    """, (proba_id, new_status))

            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            raise
        finally:
            conn.close()

    def add_table(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""  
                CREATE TABLE IF NOT EXISTS grans_archive (
                    archive_id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    proba_id            INTEGER NOT NULL,
                    gran_10             REAL,
                    gran_5_10           REAL,
                    gran_5_2            REAL,
                    gran_2_1            REAL,
                    gran_1_0_5          REAL,
                    gran_0_5_0_25       REAL,
                    gran_0_25_0_10      REAL,
                    gran_0_10_0_05      REAL,
                    gran_0_05_0_01      REAL,
                    gran_0_01_0_002     REAL,
                    gran_0_002          REAL,
                    created_at          TEXT,
                    archived_at         TEXT NOT NULL
                );       
            """)
            conn.commit()

        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def drop_table(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DROP TABLE IF EXISTS fizika")
            conn.commit()

        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_rashet_gran_part_by_id(self, party_id):
        conn = self.get_connection()

        query = """
        SELECT
            p.lab_nomer, 
            g_r.kolba_naveska_first, 
            g_r.kolba_naveska_last,
            g_r.areometr_first,
            g_r.zamer_temp_1_first,
            g_r.zamer_temp_1_last,
            g_r.zamer_temp_2_first,
            g_r.zamer_temp_2_last,
            g_r.zamer_temp_3_first,
            g_r.zamer_temp_3_last,
            g_r.gran_10_first,
            g_r.gran_5_10_first,
            g_r.gran_5_2_first,
            g_r.gran_2_1_first,
            g_r.gran_1_0_5_first,
            g_r.gran_0_5_0_25_first,
            g_r.gran_0_25_0_10_first
        FROM grans_raschet g_r 
        LEFT JOIN probi p ON p.id = g_r.proba_id
        WHERE p.partiya_id = ?
        """

        # read_sql_query сам выполнит запрос и вернёт DataFrame
        df = pd.read_sql_query(query, conn, params=(party_id,))

        conn.close()
        return df

    def get_models_predskaz_part_by_id(self, party_id):
        conn = self.get_connection()

        query = """
        SELECT p.lab_nomer, f.wlashn, f.ukol, f.plotn, 
                g.gran_10,
                g.gran_5_10,
                g.gran_5_2,
                g.gran_2_1,
                g.gran_1_0_5,
                g.gran_0_5_0_25,
                g.gran_0_25_0_10,
                g.gran_0_10_0_05,
                g.gran_0_05_0_01,
                g.gran_0_01_0_002,
                g.gran_0_002
        FROM probi p
            LEFT JOIN fizika f on p.id = f.proba_id
            LEFT JOIN grans g on p.id = g.proba_id
        WHERE p.partiya_id = ?
        """

        # read_sql_query сам выполнит запрос и вернёт DataFrame
        df = pd.read_sql_query(query, conn, params=(party_id,))

        conn.close()
        return df

# db = Database("database.db")
#
# df = db.get_rashet_gran_part_by_id(15)
# print(df)

#
# df = pd.read_excel("testik2.xlsx")
#
# db.save_grans_raschet_bulk_by_lab_nomer(df)

#
# rows = db.show_all_objects()
# for row in rows:
#     print(row["id"], row["name_object"])

# df = pd.read_excel('testtest.xlsx')






