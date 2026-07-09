"""
gran_report_dialog.py

QDialog-окно со статистикой грансоставов.
Схема БД: objects -> partii -> probi -> fizika / grans / grans_raschet

Эффективный статус вычисляется динамически из реального состояния БД:
    grans_raschet есть               → Намыт            (и монолит, и нарушен)
    grans есть, grans_raschet нет:
        монолит                      → Намыт
        нарушен                      → Промыв выполнен
    fizika.status_gran = 'Кр. р.'
        и grans нет                  → Кр. р.
    монолит, нет grans               → Назначен на намыв
    нарушен, нет grans               → В ожидании намыва или промыва
    нет fizika вообще                → Не назначен
"""
import sqlite3
import traceback

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QPushButton, QPlainTextEdit,
    QGroupBox, QFrame, QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QColor, QPalette

from gran_sync import EFFECTIVE_STATUS_SQL


MONTHS_RU = {
    'Все':      'Все',
    'Январь':   '01', 'Февраль': '02', 'Март':     '03',
    'Апрель':   '04', 'Май':     '05', 'Июнь':     '06',
    'Июль':     '07', 'Август':  '08', 'Сентябрь': '09',
    'Октябрь':  '10', 'Ноябрь':  '11', 'Декабрь':  '12',
}


# Эффективный статус вычисляется через JOIN-ы (импортирован из gran_sync)
# EFFECTIVE_STATUS_SQL уже импортирован выше


CARD_STYLES = {
    'Назначен на намыв':           ('#1a6b9a', '🔵'),
    'В ожидании намыва или промыва': ('#8b6914', '🟡'),
    'Кр. р.':                      ('#7a3a9a', '🟣'),
    'Намыт':                       ('#1a7a3a', '🟢'),
    'Промыв выполнен':             ('#1a5a7a', '✅'),
    'Не назначен':                 ('#555555', '⚪'),
}


def _card_html(label: str, count: int, icon: str, color: str) -> str:
    return (
        f'<div style="'
        f'background:{color};border-radius:6px;padding:8px 12px;'
        f'margin:3px;display:inline-block;">'
        f'<span style="font-size:18px">{icon}</span> '
        f'<b style="color:white;font-size:14px">{count}</b> '
        f'<span style="color:#ddd;font-size:11px">{label}</span>'
        f'</div>'
    )


class StatCard(QFrame):
    """Цветная карточка с числом и подписью."""

    def __init__(self, label: str, count: int = 0, icon: str = '●',
                 bg_color: str = '#444', parent=None):
        super().__init__(parent)
        self._label = label
        self._icon = icon
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumHeight(72)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(f"""
            StatCard {{
                background-color: {bg_color};
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.10);
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)

        top = QHBoxLayout()
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet("font-size: 22px; background: transparent;")
        top.addWidget(lbl_icon)
        top.addStretch()

        self.lbl_count = QLabel(str(count))
        font_count = QFont()
        font_count.setPointSize(24)
        font_count.setBold(True)
        self.lbl_count.setFont(font_count)
        self.lbl_count.setStyleSheet("color: white; background: transparent;")

        lbl_text = QLabel(label)
        lbl_text.setWordWrap(True)
        lbl_text.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 11px; background: transparent;")

        layout.addLayout(top)
        layout.addWidget(self.lbl_count)
        layout.addWidget(lbl_text)

    def set_count(self, count: int):
        self.lbl_count.setText(str(count))


class GranReportDialog(QDialog):
    """Диалог отчёта по грансоставам."""

    def __init__(self, db_file: str, parent=None):
        super().__init__(parent)
        self.db_file = db_file
        self.setWindowTitle("📊 Отчёт по грансоставам")
        self.resize(900, 700)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self._build_ui()
        self._load_filters()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # ---- Заголовок ----
        title = QLabel("Аналитика грансоставов")
        font_title = QFont()
        font_title.setPointSize(16)
        font_title.setBold(True)
        title.setFont(font_title)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # ---- Фильтры ----
        filter_box = QGroupBox("Фильтры")
        filter_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        fl = QHBoxLayout(filter_box)
        fl.setSpacing(8)

        for lbl_text, cb_attr, min_w, items in [
            ("Год:",    'cb_year',   80,  None),
            ("Месяц:", 'cb_month', 110,  list(MONTHS_RU.keys())),
            ("Объект:", 'cb_object', 160, None),
            ("Партия:", 'cb_party',  110, None),
        ]:
            fl.addWidget(QLabel(lbl_text))
            cb = QComboBox()
            cb.setMinimumWidth(min_w)
            if items:
                cb.addItems(items)
                cb.setCurrentText('Все')
            setattr(self, cb_attr, cb)
            fl.addWidget(cb)

        fl.addStretch()
        self.btn_generate = QPushButton("⚡ Сформировать")
        self.btn_generate.setMinimumHeight(32)
        self.btn_generate.setStyleSheet(
            "QPushButton { background: #1a6b9a; color: white; border-radius: 5px; "
            "padding: 4px 16px; font-weight: bold; }"
            "QPushButton:hover { background: #2280b8; }"
            "QPushButton:pressed { background: #145580; }"
        )
        self.btn_generate.clicked.connect(self._generate_report)
        fl.addWidget(self.btn_generate)
        main_layout.addWidget(filter_box)

        # ---- Карточки статистики ----
        cards_label = QLabel("Статистика по статусам")
        cards_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #aaa;")
        main_layout.addWidget(cards_label)

        cards_grid = QGridLayout()
        cards_grid.setSpacing(6)

        self._cards = {}
        card_defs = [
            ('Назначен на намыв',             '🔵', '#1a5e8a', 0, 0),
            ('В ожидании намыва или промыва',  '🟡', '#7a5e10', 0, 1),
            ('Назначен на промыв',         '🟠', '#8a4e10', 0, 2),
            ('Кр. р.',                         '🟣', '#6a2a8a', 0, 3),
            ('Намыт',                          '🟢', '#1a6a30', 1, 0),
            ('Промыв выполнен',               '✅', '#155a70', 1, 1),
            ('Намыт + Промыт',             '🌟', '#1a6a50', 1, 2),
            ('Без грана',                   '🟤', '#6b4226', 1, 3),
            ('Не назначен',                    '⚪', '#444444', 2, 0),
        ]
        for label, icon, color, row, col in card_defs:
            card = StatCard(label, 0, icon, color)
            self._cards[label] = card
            cards_grid.addWidget(card, row, col)

        main_layout.addLayout(cards_grid)

        # ---- Разделитель ----
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #555;")
        main_layout.addWidget(sep)

        # ---- Текстовый лог (детали) ----
        detail_label = QLabel("Детали")
        detail_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #aaa;")
        main_layout.addWidget(detail_label)

        self.text_area = QPlainTextEdit()
        self.text_area.setReadOnly(True)
        mono_font = QFont("Consolas", 9)
        self.text_area.setFont(mono_font)
        self.text_area.setStyleSheet(
            "QPlainTextEdit { background: #1e1e2e; color: #cdd6f4; "
            "border: 1px solid #444; border-radius: 5px; }"
        )
        main_layout.addWidget(self.text_area, stretch=1)

    # ------------------------------------------------------------------
    # БД
    # ------------------------------------------------------------------
    def _get_conn(self):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------
    # Фильтры
    # ------------------------------------------------------------------
    def _load_filters(self):
        try:
            conn = self._get_conn()
            cur = conn.cursor()

            cur.execute("SELECT DISTINCT year FROM objects WHERE year IS NOT NULL ORDER BY year")
            years = ['Все'] + [str(r[0]) for r in cur.fetchall()]
            self.cb_year.addItems(years)
            self.cb_year.setCurrentText('Все')

            cur.execute("SELECT DISTINCT name_object FROM objects ORDER BY name_object")
            objects = ['Все'] + [r[0] for r in cur.fetchall()]
            self.cb_object.addItems(objects)
            self.cb_object.setCurrentText('Все')

            cur.execute("SELECT DISTINCT name_partii FROM partii ORDER BY name_partii")
            parties = ['Все'] + [r[0] for r in cur.fetchall()]
            self.cb_party.addItems(parties)
            self.cb_party.setCurrentText('Все')

            conn.close()
        except Exception as e:
            self._print(f"Ошибка загрузки фильтров: {e}")

    # ------------------------------------------------------------------
    # Построение WHERE по фильтрам
    # ------------------------------------------------------------------
    def _build_where(self):
        f_year       = self.cb_year.currentText()
        f_month_name = self.cb_month.currentText()
        f_month_num  = MONTHS_RU.get(f_month_name, 'Все')
        f_object     = self.cb_object.currentText()
        f_party      = self.cb_party.currentText()

        conditions, params = [], []
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
        return where, params, f_year, f_month_name, f_object, f_party

    # ------------------------------------------------------------------
    # Генерация отчёта
    # ------------------------------------------------------------------
    def _generate_report(self):
        self.text_area.clear()
        # Сбросить карточки
        for card in self._cards.values():
            card.set_count(0)

        where, params, f_year, f_month_name, f_object, f_party = self._build_where()

        # --- Основной запрос: эффективный статус считается через JOIN-ы ---
        # Не читаем fizika.status_gran напрямую — вычисляем из реального состояния таблиц
        sql_effective = f"""
            SELECT
                {EFFECTIVE_STATUS_SQL} AS eff_status,
                COUNT(*) AS cnt
            FROM probi pr
            JOIN partii pa ON pa.id = pr.partiya_id
            JOIN objects o  ON o.id  = pa.object_id
            LEFT JOIN fizika       f  ON f.proba_id  = pr.id
            LEFT JOIN grans        g  ON g.proba_id  = pr.id
            LEFT JOIN grans_raschet gr ON gr.proba_id = pr.id
            {where}
            GROUP BY eff_status
        """

        # --- Список проб «Назначен на намыв» ---
        sql_namyv_list = f"""
            SELECT pr.lab_nomer, pa.name_partii, o.name_object, pa.file_path
            FROM probi pr
            JOIN partii pa ON pa.id = pr.partiya_id
            JOIN objects o  ON o.id  = pa.object_id
            LEFT JOIN fizika        f  ON f.proba_id  = pr.id
            LEFT JOIN grans         g  ON g.proba_id  = pr.id
            LEFT JOIN grans_raschet gr ON gr.proba_id = pr.id
            {where}
            {"AND" if where else "WHERE"} (
                {EFFECTIVE_STATUS_SQL}
            ) = 'Назначен на намыв'
            ORDER BY o.name_object, pa.name_partii, pr.lab_nomer
        """

        # --- Список проб «Кр. р.» ---
        sql_kr_r_list = f"""
            SELECT pr.lab_nomer, pa.name_partii, o.name_object
            FROM probi pr
            JOIN partii pa ON pa.id = pr.partiya_id
            JOIN objects o  ON o.id  = pa.object_id
            LEFT JOIN fizika        f  ON f.proba_id  = pr.id
            LEFT JOIN grans         g  ON g.proba_id  = pr.id
            LEFT JOIN grans_raschet gr ON gr.proba_id = pr.id
            {where}
            {"AND" if where else "WHERE"} (
                {EFFECTIVE_STATUS_SQL}
            ) = 'Кр. р.'
            ORDER BY o.name_object, pa.name_partii, pr.lab_nomer
        """

        try:
            conn = self._get_conn()
            cur = conn.cursor()

            # Статистика
            cur.execute(sql_effective, params)
            statuses = {row['eff_status']: row['cnt'] for row in cur.fetchall()}

            namyv      = statuses.get('Назначен на намыв', 0)
            ozhid      = statuses.get('В ожидании намыва или промыва', 0)
            kr_r       = statuses.get('Кр. р.', 0)
            namyt      = statuses.get('Намыт', 0)
            promyt     = statuses.get('Промыв выполнен', 0)
            nazn_promyv = statuses.get('Назначен на промыв', 0)
            namyt_promyt = statuses.get('Намыт + Промыт', 0)
            bez_grana  = statuses.get('Без грана', 0)
            not_set    = statuses.get('Не назначен', 0)
            total      = sum(statuses.values())

            # Обновляем карточки
            self._cards['Назначен на намыв'].set_count(namyv)
            self._cards['В ожидании намыва или промыва'].set_count(ozhid)
            self._cards['Назначен на промыв'].set_count(nazn_promyv)
            self._cards['Кр. р.'].set_count(kr_r)
            self._cards['Намыт'].set_count(namyt)
            self._cards['Промыв выполнен'].set_count(promyt)
            self._cards['Намыт + Промыт'].set_count(namyt_promyt)
            self._cards['Без грана'].set_count(bez_grana)
            self._cards['Не назначен'].set_count(not_set)

            # Текстовый отчёт
            lines = []
            lines.append("=" * 62)
            lines.append("  📊  ОТЧЁТ ПО ГРАНСОСТАВАМ")
            lines.append(
                f"  Год: {f_year}  |  Месяц: {f_month_name}  |  "
                f"Объект: {f_object}  |  Партия: {f_party}"
            )
            lines.append("=" * 62)
            lines.append(f"  Всего проб по фильтру:  {total} шт.")
            lines.append("")
            lines.append("🔹 ГЛАВНОЕ НА ДАННЫЙ МОМЕНТ:")
            lines.append(f"  🔵 Ожидает намыва:              {namyv:>5} шт.")
            lines.append(f"  🟡 Ожидает намыва/промыва:      {ozhid:>5} шт.")
            lines.append(f"  🟠 Назначен на промыв:        {nazn_promyv:>5} шт.")
            lines.append(f"  🟣 Ожидает кр.р.:               {kr_r:>5} шт.")
            lines.append("-" * 62)
            lines.append(f"  🟢 Намыто:                      {namyt:>5} шт.")
            lines.append(f"  ✅ Промыв выполнен:             {promyt:>5} шт.")
            lines.append(f"  🌟 Намыт + Промыт:              {namyt_promyt:>5} шт.")
            lines.append(f"  🟤 Без грана (торф/прс/ск):     {bez_grana:>5} шт.")
            lines.append(f"  ⚪ Статус не назначен:          {not_set:>5} шт.")
            lines.append("=" * 62)

            # Детальный список «Назначен на намыв»
            cur.execute(sql_namyv_list, params)
            namyv_list = cur.fetchall()
            if namyv_list:
                lines.append("")
                lines.append(f"📋 Назначено на намыв ({len(namyv_list)} шт.):")
                lines.append("-" * 62)
                for row in namyv_list:
                    fp = f"  ← {row['file_path']}" if row['file_path'] else ""
                    lines.append(
                        f"  {row['lab_nomer']:<14}  "
                        f"[{row['name_object']} / {row['name_partii']}]{fp}"
                    )

            # Детальный список «Кр. р.»
            cur.execute(sql_kr_r_list, params)
            kr_list = cur.fetchall()
            if kr_list:
                lines.append("")
                lines.append(f"🟣 Ожидают кр.р. ({len(kr_list)} шт.):")
                lines.append("-" * 62)
                for row in kr_list:
                    lines.append(
                        f"  {row['lab_nomer']:<14}  "
                        f"[{row['name_object']} / {row['name_partii']}]"
                    )

            conn.close()
            self._print("\n".join(lines))


        except Exception as e:
            self._print(f"Ошибка:\n{traceback.format_exc()}")

    def _print(self, text: str):
        self.text_area.appendPlainText(text)
