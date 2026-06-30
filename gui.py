import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
                             QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt
import qdarkstyle
from orkestrator_db import MainCore


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.orkestr_db = MainCore('database.db')

        self.initUI()

    def initUI(self):
        self.setGeometry(100, 100, 800, 600)
        self.setWindowTitle('Шаблон')

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        label = QLabel('Шаблон')
        main_layout.addWidget(label)

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

        self.btn = QPushButton("Добавить партию")
        self.btn.clicked.connect(self.add_partiya)
        vlayout2.addWidget(self.btn)

        vlayout3 = QVBoxLayout()
        hlayout.addLayout(vlayout3)

        self.info_label = QLabel()
        vlayout3.addWidget(self.info_label)

    def add_object(self):
        pass

    def add_partiya(self):
        pass

    def on_item_clicked1(self, item):
        try:
            db_id = item.data(Qt.UserRole)

            self.list_widget2.clear()
            rows = self.orkestr_db.db_show.show_all_partii_object(db_id)
            for row in rows:
                item = QListWidgetItem(row["name_partii"])
                item.setData(Qt.UserRole, row["id"])
                self.list_widget2.addItem(item)

            object = item.text()

            self.info_label.setText(f"Выбран объект: {object}")
        except Exception as e:
            print(e)

    def on_item_clicked2(self, item):
        object = self.list_widget1.currentItem().text()
        partiya = item.text()
        db_id = item.data(Qt.UserRole)

        df = self.orkestr_db.db_show.poln_grani_part(db_id)

        count = len(df)
        count_pust_gran = len(df[df.isna().any(axis=1)])

        self.info_label.setText(f"Выбрано: {object}, Партия: {partiya}\n"
                                f"Количество проб {count}\n"
                                f"Количество не хватающих гранов {count_pust_gran}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())