import sys
from PyQt6 import uic
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit,
    QDateTimeEdit, QDialog, QDialogButtonBox, QFormLayout, QMessageBox
)
from design import Ui_Form
from PyQt6.QtCore import QDateTime
import sqlite3


# основной класс
class TaskManager(QMainWindow, Ui_Form):
    def __init__(self):
        super(TaskManager, self).__init__()
        uic.loadUi('design.ui', self)

        conn = sqlite3.connect("tasks.db")
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS tasks
                         (id INTEGER PRIMARY KEY,
                          description TEXT NOT NULL,
                          done_date TEXT,
                          status TEXT)''')
        conn.commit()
        conn.close()
        # обрабатываем нажатия кнопок
        self.add_to_do_btn.clicked.connect(lambda: self.open_task_dialog("to do"))
        self.add_doing_btn.clicked.connect(lambda: self.open_task_dialog("doing"))
        self.add_done_btn.clicked.connect(lambda: self.open_task_dialog("done"))

    # функция для чтения данных от пользователя
    def open_task_dialog(self, status):
        dialog = TaskDialog(status, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            description = dialog.description_input.toPlainText()
            done_date = dialog.date_input.dateTime().toString("yyyy-MM-dd hh:mm")
            self.add_task(description, done_date, status)
        else:
            pass

    # функция добавления задач в базу
    def add_task(self, description, done_date, status):
        conn = sqlite3.connect("tasks.db")
        cur = conn.cursor()

        cur.execute('''
                    INSERT INTO tasks (description, done_date, status) VALUES (?, ?, ?)
                ''', (description, done_date, status))

        conn.commit()
        conn.close()
        self.show_tasks()

    # функция для отображения задач
    def show_tasks(self):
        pass


# класс для собственного диалога
class TaskDialog(QDialog):
    def __init__(self, status, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить задачу")

        self.layout = QFormLayout(self)

        self.description_input = QPlainTextEdit(self)
        self.layout.addRow("Описание:", self.description_input)

        self.date_input = QDateTimeEdit(self)
        self.date_input.setCalendarPopup(True)
        self.date_input.setDateTime(QDateTime.currentDateTime())
        self.layout.addRow("Дата выполнения:", self.date_input)

        # создаем бокс и добавляем кнопки ok и cancel
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.layout.addWidget(self.button_box)

    # нельзя ввести дату в прошлом и поле описания не может быть пустым!
    def accept(self):
        selected_date = self.date_input.dateTime()
        current_date = QDateTime.currentDateTime()

        if self.description_input.toPlainText() == "":
            QMessageBox.warning(self, "Ошибка", "Не введено описание!")

        elif selected_date < current_date:
            QMessageBox.warning(self, "Ошибка", "Дата в прошлом!")
        else:
            super().accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = TaskManager()
    ex.show()
    sys.exit(app.exec())
