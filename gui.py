import sys
import traceback

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QLineEdit,
                             QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
                             QDialog, QPlainTextEdit)
from PyQt5.QtCore import Qt
import qdarkstyle
from openpyxl import load_workbook
from orkestrator_db import MainCore
from gransostav import RaschetGranov
from core import zagr_file, zagr_file2, zagr_tarirovki, obrabotka_df_posle_zagr, rashet_gran, vigruzka_namiv
import config
from klasspredict import ClassPredict


class NewQDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__()
        self.setWindowTitle("Доп окно")
        self.resize(400, 400)

        self.orkestr_db = db

        main_layout = QVBoxLayout(self)


        self.lineedit = QLineEdit('')  # Поле ввода
        main_layout.addWidget(self.lineedit)

        self.btn = QPushButton("Добавить объект")
        self.btn.clicked.connect(self.btn_calc)
        main_layout.addWidget(self.btn)

    def btn_calc(self):
        try:
            text = self.lineedit.text()
            self.orkestr_db.db_add.add_object_bd(text)
        except Exception as e:
            print(e)
            traceback.print_exc()


class NewQDialog2(QDialog):
    def __init__(self, db, parent=None):
        super().__init__()
        self.setWindowTitle("Доп окно")
        self.resize(400, 400)

        self.orkestr_db = db

        main_layout = QVBoxLayout(self)

        self.list_widget1 = QListWidget()
        rows = self.orkestr_db.db_show.show_all_objects()
        for row in rows:
            item = QListWidgetItem(row["name_object"])
            # Сохраняем ID из БД в роли UserRole (или любой другой роли)
            item.setData(Qt.UserRole, row["id"])
            self.list_widget1.addItem(item)

        main_layout.addWidget(self.list_widget1)

        self.lineedit = QLineEdit('')  # Поле ввода
        main_layout.addWidget(self.lineedit)

        self.btn = QPushButton("Добавить партию")
        self.btn.clicked.connect(self.btn_calc)
        main_layout.addWidget(self.btn)

    def btn_calc(self):
        try:
            item = self.list_widget1.currentItem()

            if item:
                # Получаем данные из Qt.UserRole (роль 0x100)
                db_id = item.data(Qt.UserRole)

                print(f"Данные из UserRole: {db_id}")
            else:
                print("Ничего не выбрано")
            # object = self.list_widget1.currentData()
            text = self.lineedit.text()
            self.orkestr_db.db_add.add_partiya_bd(text, db_id)
        except Exception as e:
            print(e)
            traceback.print_exc()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.orkestr_db = MainCore('database.db')

        self.df_partii = None

        self.initUI()

    def initUI(self):
        self.setGeometry(100, 100, 800, 600)
        self.setWindowTitle('Шаблон')

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        hlayout_1 = QHBoxLayout()
        main_layout.addLayout(hlayout_1)

        self.btn_namiv = QPushButton("Добавить намыв")
        self.btn_namiv.clicked.connect(self.add_namiv)
        hlayout_1.addWidget(self.btn_namiv)

        hlayout = QHBoxLayout()
        main_layout.addLayout(hlayout)

        vlayout1 = QVBoxLayout()
        hlayout.addLayout(vlayout1)

        self.list_widget1 = QListWidget()
        rows = self.orkestr_db.db_show.show_all_objects()
        for row in rows:
            item = QListWidgetItem(row["name_object"])
            # Сохраняем ID из БД в роли UserRole (или любой другой роли)
            item.setData(Qt.UserRole, row["id"])
            self.list_widget1.addItem(item)

        self.list_widget1.itemClicked.connect(self.on_item_clicked1)
        self.list_widget1.setFixedWidth(200)
        vlayout1.addWidget(self.list_widget1)

        self.btn = QPushButton("Добавить объект")
        self.btn.clicked.connect(self.add_object)
        vlayout1.addWidget(self.btn)

        vlayout2 = QVBoxLayout()
        hlayout.addLayout(vlayout2)

        self.list_widget2 = QListWidget()
        self.list_widget2.itemClicked.connect(self.on_item_clicked2)
        self.list_widget2.setFixedWidth(200)
        vlayout2.addWidget(self.list_widget2)

        self.btn2 = QPushButton("Добавить партию")
        self.btn2.clicked.connect(self.add_partiya)
        vlayout2.addWidget(self.btn2)

        vlayout3 = QVBoxLayout()
        hlayout.addLayout(vlayout3)

        hlayout2 = QHBoxLayout()
        vlayout3.addLayout(hlayout2)

        self.btn5 = QPushButton("Добавить рабочую сводную")
        self.btn5.clicked.connect(self.add_rab_svodn)
        hlayout2.addWidget(self.btn5)

        self.info_label = QLabel()
        vlayout3.addWidget(self.info_label)

        self.warning_box = QPlainTextEdit()
        hlayout.addWidget(self.warning_box)

        self.btn6 = QPushButton("Получить все намывы по этой партии")
        self.btn6.clicked.connect(self.get_namivs)
        vlayout3.addWidget(self.btn6)

        self.btn7 = QPushButton("Выгрузить в Excel отчет по партии")
        self.btn7.clicked.connect(self.save_part_excel)
        vlayout3.addWidget(self.btn7)

        self.btn8 = QPushButton("Проверка по статистике")
        self.btn8.clicked.connect(self.btn_calc)
        vlayout3.addWidget(self.btn8)


    def btn_calc(self):
        try:
            df_table = self.df_partii

            bad_rows = ClassPredict.predict(df_table)
            bad_rows = bad_rows.sort_values(by=['lab_nomer'], ascending=True)
            # bad_rows = bad_rows[config.COLUMNS2]

            if not bad_rows.empty:
                messages = []
                for idx, row in bad_rows.iterrows():
                    err_type = row['error_type']
                    if err_type == 'плотность':
                        messages.append(
                            f"{row['lab_nomer']}: {err_type} (испытание, статистика)="
                            f"{row['plotn']:.2f}, "
                            f"{row['plotn_predict']:.2f}"
                        )
                    elif err_type == 'влажность':
                        messages.append(
                            f"{row['lab_nomer']}: {err_type} (испытание, статистика)="
                            f"{row['wlashn']:.3f}, "
                            f"{row['wlashn_predict']:.3f}"
                        )

                    elif err_type == 'Укол':
                        messages.append(
                            f"{row['lab_nomer']}: {err_type} (испытание, статистика)="
                            f"{row['ukol_values']:.1f}, "
                            f"{row['ukol_predict']:.1f}"
                        )

                self.warning_box.setPlainText("\n\n".join(messages))
                QMessageBox.warning(
                    self,
                    "Предупреждение",
                    f"Найдено подозрительных номеров: {len(bad_rows)}"
                )
            else:
                self.warning_box.setPlainText("Расхождений не найдено.")



        except Exception as e:
            print(e)
            traceback.print_exc()

    def save_part_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить испытание",
            f"Намыв.xlsx",
            "Excel Files (*.xlsx *.xls)"
        )
        if not file_path:
            return
        
        self.df_partii.to_excel(file_path)

    def add_rab_svodn(self):
        path_rab_svodn, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл намыва", "", "Excel Files (*.xlsx *.xls)")
        if not path_rab_svodn:
            return

        try:
            df = zagr_file2(path_rab_svodn)

            item = self.list_widget2.currentItem()
            if item:
                db_id = item.data(Qt.UserRole)
                print(f"Данные из UserRole: {db_id}")
            else:
                print("Ничего не выбрано")

            self.orkestr_db.db_add.add_rab_svodnaya(df, db_id)

            df2 = RaschetGranov.zagr_excel(path_rab_svodn)
            df2 = RaschetGranov.raschet_gran_pesk(df2)

            self.orkestr_db.db_add.add_gran_bd(df2)
        except Exception as e:
            print(e)
            traceback.print_exc()

    def get_namivs(self):
        try:
            item = self.list_widget2.currentItem()
            if item:
                # Получаем данные из Qt.UserRole (роль 0x100)
                db_id = item.data(Qt.UserRole)
                text = item.text()

            df = self.orkestr_db.db_show.get_namivs(db_id)

            result = vigruzka_namiv(df)

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить испытание",
                f"Намыв_{text}.xlsx",
                "Excel Files (*.xlsx *.xls)"
            )
            if not file_path:
                return

            result.to_excel(file_path)

            wb = load_workbook(file_path)
            ws = wb["Sheet1"]

            # Какие столбцы объединять (по номеру колонки в Excel)
            # Например, столбцы A и C
            cols_to_merge = ["B", "D", "H", "I", "J", "K", "L", "M", "N"]

            # Определяем последнюю строку
            max_row = ws.max_row

            # Объединяем по две строки: (1,2), (3,4), ...
            for col in cols_to_merge:
                row = 2  # 1-я строка — заголовки, начинаем со 2-й
                while row <= max_row:
                    # объединяем только если есть пара строк row и row+1
                    if row + 1 <= max_row:
                        ws.merge_cells(start_row=row, start_column=ws[col + str(row)].column,
                                       end_row=row + 1, end_column=ws[col + str(row)].column)
                    row += 2

            wb.save(file_path)
        except Exception as e:
            print(e)
            traceback.print_exc()


    def add_namiv(self):
        path_namiv, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл намыва", "", "Excel Files (*.xlsx *.xls)")
        if not path_namiv:
            return

        path_tarirovki = "tarirovki.xlsx"

        try:
            df = zagr_file(path_namiv)
            df_tarirovk = zagr_tarirovki(path_tarirovki)
            udelka = 2.7

            df_agg = obrabotka_df_posle_zagr(df)
            df_itog, spisok_otrizat_grani = rashet_gran(df_agg, df_tarirovk, udelka)

            if spisok_otrizat_grani:
                QMessageBox.warning(self, "Внимание", f"Есть отрицательные граны {spisok_otrizat_grani}")

            df = df_itog.rename(columns=config.cols_bd_rename)

            df_rashet = df_agg[config.cols_bd_rashet]

            self.orkestr_db.db_add.add_gran_bd(df)
            self.orkestr_db.db_add.add_gran_rashet_bd(df_rashet)

            QMessageBox.information(self, "Успех", f"Граны ({len(df_itog)} шт.) в базе данных")

        except Exception as e:
            print(e)
            QMessageBox.critical(self, "Ошибка", f"Рабочий журнал не получилось добавить: {e}")
            traceback.print_exc()



    def add_object(self):
        try:
            dialog = NewQDialog(self.orkestr_db, self)
            dialog.exec_()

            self.list_widget1.clear()
            rows = self.orkestr_db.db_show.show_all_objects()
            for row in rows:
                item = QListWidgetItem(row["name_object"])
                item.setData(Qt.UserRole, row["id"])
                self.list_widget1.addItem(item)
        except Exception as e:
            print(e)
            traceback.print_exc()

    def add_partiya(self):
        try:
            dialog = NewQDialog2(self.orkestr_db, self)
            dialog.exec_()

            # self.list_widget2.clear()
            # rows = self.orkestr_db.db_show.show_all_partii_object(db_id)
            # for row in rows:
            #     item = QListWidgetItem(row["name_partii"])
            #     item.setData(Qt.UserRole, row["id"])
            #     self.list_widget2.addItem(item)
        except Exception as e:
            print(e)
            traceback.print_exc()

    def on_item_clicked1(self, item):
        try:
            db_id = item.data(Qt.UserRole)
            object = item.text()

            self.list_widget2.clear()
            rows = self.orkestr_db.db_show.show_all_partii_object(db_id)
            for row in rows:
                item = QListWidgetItem(row["name_partii"])
                item.setData(Qt.UserRole, row["id"])
                self.list_widget2.addItem(item)



            self.info_label.setText(f"Выбран объект: {object}")
        except Exception as e:
            print(e)

    def on_item_clicked2(self, item):
        try:
            object = self.list_widget1.currentItem().text()
            partiya = item.text()
            db_id = item.data(Qt.UserRole)

            self.df_partii = self.orkestr_db.db_show.poln_info_part(db_id)

            print(self.df_partii)
            print(self.df_partii)

            count = len(self.df_partii)
            count_pust_gran = len(self.df_partii[self.df_partii[config.cols_bd_rename.values()].isna().any(axis=1)])
            count_pust_wlashn = len(self.df_partii[self.df_partii['wlashn'].isna()])

            mask = self.df_partii['plotn'].isna() & self.df_partii['ukol'].notna()
            count_pust_plotn = mask.sum()

            mask_org = self.df_partii['organika'].notna()
            count_org = mask_org.sum()

            mask_udelka = self.df_partii['udelka'].notna()
            count_udelka = mask_udelka.sum()

            self.info_label.setText(f"Выбрано: {object}, Партия: {partiya}\n\n"
                                    f"Количество проб {count}\n"
                                    f"Количество не хватающих гранов {count_pust_gran}\n"
                                    f"Количество не хватающих влажностей {count_pust_wlashn}\n"
                                    f"Количество не хватающих плотностей {count_pust_plotn}\n\n"
                                    f"Количество сделанной органики {count_org}\n"
                                    f"Количество сделанной уделки {count_udelka}")
        except Exception as e:
            print(e)
            traceback.print_exc()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())