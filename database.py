import sqlite3
from datetime import datetime
import pandas as pd
import config

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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS objects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_object TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS partii (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_partii TEXT NOT NULL,
                object_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY(object_id) REFERENCES objects(id)
                    ON DELETE CASCADE
                )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS probi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lab_nomer TEXT NOT NULL UNIQUE,
                partiya_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,

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

        conn.commit()
        conn.close()



    """Методы для объекта"""
    def add_object(self, name_object):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            current_time = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO objects (name_object, created_at)
                VALUES (?, ?)
            """, (name_object, current_time))

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
                raise ValueError(f'Не найдены proba_id для lab_nomer: {missing}')

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

    def get_poln_gran_data_by_party_id(self, party_id):
        conn = self.get_connection()

        query = """
            SELECT 
                p.lab_nomer AS proba_lab_nomer,
                g.gran_10, g.gran_5_10, g.gran_5_2, g.gran_2_1, g.gran_1_0_5, g.gran_0_5_0_25,
                g.gran_0_25_0_10, g.gran_0_10_0_05, g.gran_0_05_0_01, g.gran_0_01_0_002, g.gran_0_002
            FROM probi p
            LEFT JOIN grans g ON p.id = g.proba_id
            WHERE p.partiya_id = ?
        """

        # read_sql_query сам выполнит запрос и вернёт DataFrame
        df = pd.read_sql_query(query, conn, params=(party_id,))

        conn.close()
        return df

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
            cursor.execute("DROP TABLE IF EXISTS WLASHN")
            conn.commit()

        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

db = Database("database.db")
#
# rows = db.show_all_objects()
# for row in rows:
#     print(row["id"], row["name_object"])






