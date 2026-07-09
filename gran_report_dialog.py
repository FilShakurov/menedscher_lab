"""
gran_report_dialog.py

QDialog-окно со статистикой грансоставов.
Адаптировано под схему БД p1 (menedscher_lab):
    objects  -> partii  -> probi  -> fizika (status_gran)
Аналог report_app.py из p2, но на PyQt5.
"""
import sqlite3

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QPlainTextEdit, QGroupBox
)
from PyQt5.QtCore import Qt


MONTHS_RU = {
    'Все': 'Все',
    'Январь': '01', 'Февраль': '02', 'Март': '03',
    'Апрель': '04', 'Май': '05', 'Июнь': '06', 'Июль': '07',
    'Август': '08', 'Сентябрь': '09', 'Октябрь': '10',
    'Ноябрь': '11', 'Декабрь': '12'
}


class GranReportDialog(QDialog):
    """Диалог отчёта по грансоставам (статистика по статусам проб)."""

    def __init__(self, db_file: str, parent=None):
        super().__init__(parent)
        self.db_file = db_file
        self.setWindowTitle("Отчёт грансоставов")
        self.resize(750, 600)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self._build_ui()
        self._load_filters()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Панель фильтров ---
        filter_box = QGroupBox("Фильтры")
        filter_layout = QHBoxLayout(filter_box)

        filter_layout.addWidget(QLabel("Год:"))
        self.cb_year = QComboBox()
        self.cb_year.setMinimumWidth(90)
        filter_layout.addWidget(self.cb_year)

        filter_layout.addWidget(QLabel("Месяц:"))
        self.cb_month = QComboBox()
        self.cb_month.addItems(list(MONTHS_RU.keys()))
        self.cb_month.setCurrentText('Все')
        self.cb_month.setMinimumWidth(110)
        filter_layout.addWidget(self.cb_month)

        filter_layout.addWidget(QLabel("Объект:"))
        self.cb_object = QComboBox()
        self.cb_object.setMinimumWidth(150)
        filter_layout.addWidget(self.cb_object)

        filter_layout.addWidget(QLabel("Партия:"))
        self.cb_party = QComboBox()
        self.cb_party.setMinimumWidth(100)
        filter_layout.addWidget(self.cb_party)

        self.btn_generate = QPushButton("Сформировать отчёт")
        self.btn_generate.clicked.connect(self._generate_report)
        filter_layout.addWidget(self.btn_generate)

        main_layout.addWidget(filter_box)

        # --- Текстовая область ---
        self.text_area = QPlainTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setFont(self.font())
        main_layout.addWidget(self.text_area)

    # ------------------------------------------------------------------
    # БД
    # ------------------------------------------------------------------
    def _get_conn(self):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------
    # Загрузка фильтров
    # ------------------------------------------------------------------
    def _load_filters(self):
        try:
            conn = self._get_conn()
            cur = conn.cursor()

            # Года из objects
            cur.execute("SELECT DISTINCT year FROM objects WHERE year IS NOT NULL ORDER BY year")
            years = ['Все'] + [str(r[0]) for r in cur.fetchall()]
            self.cb_year.addItems(years)
            self.cb_year.setCurrentText('Все')

            # Объекты
            cur.execute("SELECT DISTINCT name_object FROM objects ORDER BY name_object")
            objects = ['Все'] + [r[0] for r in cur.fetchall()]
            self.cb_object.addItems(objects)
            self.cb_object.setCurrentText('Все')

            # Партии
            cur.execute("SELECT DISTINCT name_partii FROM partii ORDER BY name_partii")
            parties = ['Все'] + [r[0] for r in cur.fetchall()]
            self.cb_party.addItems(parties)
            self.cb_party.setCurrentText('Все')

            conn.close()
        except Exception as e:
            self._print(f"Ошибка загрузки фильтров: {e}")

    # ------------------------------------------------------------------
    # Формирование отчёта
    # ------------------------------------------------------------------
    def _generate_report(self):
        self.text_area.clear()

        f_year       = self.cb_year.currentText()
        f_month_name = self.cb_month.currentText()
        f_month_num  = MONTHS_RU.get(f_month_name, 'Все')
        f_object     = self.cb_object.currentText()
        f_party      = self.cb_party.currentText()

        conditions = []
        params = []

        if f_year != 'Все':
            conditions.append("o.year = ?")
            params.append(int(f_year))
        if f_month_num != 'Все':
            conditions.append("strftime('%m', pa.last_modified) = ?")
            params.append(f_month_num)
        if f_object != 'Все':
            conditions.append("o.name_object = ?")
            params.append(f_object)
        if f_party != 'Все':
            conditions.append("pa.name_partii = ?")
            params.append(f_party)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # --- Запрос: статусы грансоставов ---
        sql_status = f"""
            SELECT f.status_gran, COUNT(f.proba_id)
            FROM fizika f
            JOIN probi pr  ON pr.id = f.proba_id
            JOIN partii pa ON pa.id = pr.partiya_id
            JOIN objects o ON o.id  = pa.object_id
            {where}
            GROUP BY f.status_gran
        """

        # --- Запрос: пробы без записи в fizika (статус «Не назначен» фактически) ---
        sql_no_fizika = f"""
            SELECT COUNT(pr.id)
            FROM probi pr
            JOIN partii pa ON pa.id = pr.partiya_id
            JOIN objects o ON o.id  = pa.object_id
            LEFT JOIN fizika f ON f.proba_id = pr.id
            {where}
            AND f.proba_id IS NULL
        """

        # --- Запрос: список проб, ожидающих намыва (с путём к файлу) ---
        sql_waiting = f"""
            SELECT pr.lab_nomer, pa.name_partii, o.name_object, pa.file_path
            FROM fizika f
            JOIN probi pr  ON pr.id = f.proba_id
            JOIN partii pa ON pa.id = pr.partiya_id
            JOIN objects o ON o.id  = pa.object_id
            {where}
            {"AND" if where else "WHERE"} f.status_gran = 'Назначен на намыв'
            ORDER BY o.name_object, pa.name_partii, pr.lab_nomer
        """
        # Если where уже есть — добавляем AND, иначе WHERE
        # Упрощаем: пересобираем условие со статусом
        conditions_wait = conditions + ["f.status_gran = 'Назначен на намыв'"]
        params_wait = params + []
        where_wait = "WHERE " + " AND ".join(conditions_wait)
        sql_waiting = f"""
            SELECT pr.lab_nomer, pa.name_partii, o.name_object, pa.file_path
            FROM fizika f
            JOIN probi pr  ON pr.id = f.proba_id
            JOIN partii pa ON pa.id = pr.partiya_id
            JOIN objects o ON o.id  = pa.object_id
            {where_wait}
            ORDER BY o.name_object, pa.name_partii, pr.lab_nomer
        """

        try:
            conn = self._get_conn()
            cur = conn.cursor()

            cur.execute(sql_status, params)
            statuses = dict(cur.fetchall())

            cur.execute(sql_no_fizika, params)
            row_no_fizika = cur.fetchone()
            not_assigned_implicit = row_no_fizika[0] if row_no_fizika else 0

            waiting_namyv   = statuses.get('Назначен на намыв', 0)
            waiting_promyv  = statuses.get('Назначен на промыв', 0)
            waiting_both    = statuses.get('В ожидании намыва или промыва', 0)
            completed_promyv = statuses.get('Промыв выполнен', 0)
            completed_namyv  = statuses.get('Намыт', 0)
            not_assigned_expl = statuses.get('Не назначен', 0)
            not_assigned_total = not_assigned_expl + not_assigned_implicit

            total = sum(statuses.values()) + not_assigned_implicit

            report = []
            report.append("=" * 60)
            report.append("📊 ОТЧЁТ ПО ГРАНСОСТАВАМ 📊")
            report.append(
                f"Год: {f_year} | Месяц: {f_month_name} | "
                f"Объект: {f_object} | Партия: {f_party}"
            )
            report.append("=" * 60)
            report.append(f"Всего проб по фильтру: {total} шт.")
            report.append("")
            report.append("🔹 ГЛАВНОЕ НА ДАННЫЙ МОМЕНТ:")
            report.append(f"  • Ожидает намыва:                   {waiting_namyv} шт.")
            report.append(f"  • Ожидает промыва:                  {waiting_promyv} шт.")
            report.append(f"  • Ожидает намыва/промыва (общ):     {waiting_both} шт.")
            report.append("-" * 60)
            report.append(f"  ✅ Уже намыто:                       {completed_namyv} шт.")
            report.append(f"  ✅ Промыв (и кр.р.) выполнен:        {completed_promyv} шт.")
            report.append(f"  ❔ Статус не назначен:               {not_assigned_total} шт.")
            report.append("=" * 60)

            # Список ожидающих намыва
            cur.execute(sql_waiting, params_wait)
            waiting_list = cur.fetchall()

            if waiting_list:
                report.append("")
                report.append(f"📋 Список проб, ожидающих намыва ({len(waiting_list)} шт.):")
                report.append("-" * 60)
                for row in waiting_list:
                    lab      = row['lab_nomer']   if row.keys() else row[0]
                    partiya  = row['name_partii']  if row.keys() else row[1]
                    obj      = row['name_object']  if row.keys() else row[2]
                    fpath    = row['file_path']    if row.keys() else row[3]
                    fpath_str = f" | {fpath}" if fpath else ""
                    report.append(f"  {lab}  [{obj} / {partiya}]{fpath_str}")

            conn.close()
            self._print("\n".join(report))

        except Exception as e:
            import traceback
            self._print(f"Ошибка выполнения запроса: {e}\n{traceback.format_exc()}")

    def _print(self, text: str):
        self.text_area.appendPlainText(text)
