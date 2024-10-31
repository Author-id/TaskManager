import sys
from PyQt6 import uic
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit,
    QDateEdit, QDialog, QDialogButtonBox,
    QFormLayout, QMessageBox, QWidget, QLabel,
    QListWidgetItem, QVBoxLayout, QPushButton
)
from design import Ui_Form
from datetime import datetime
from PyQt6.QtCore import QDate
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
        self.show_tasks()
        # обрабатываем нажатия кнопок
        self.add_to_do_btn.clicked.connect(lambda: self.open_task_dialog("to do"))
        self.add_doing_btn.clicked.connect(lambda: self.open_task_dialog("doing"))
        self.add_done_btn.clicked.connect(lambda: self.open_task_dialog("done"))

    # функция для чтения данных от пользователя
    def open_task_dialog(self, status):
        dialog = TaskDialog(status, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            description = dialog.description_input.toPlainText()
            done_date = dialog.date_input.date().toString("yyyy-MM-dd")
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
        for widget in self.status_dict.values():
            widget.clear()
        self.show_tasks()

    # генерация списков из задач
    def generate_lst(self, status):
        conn = sqlite3.connect("tasks.db")
        cur = conn.cursor()
        # меняем статус просроченных задач
        expired = cur.execute("""
        UPDATE tasks
        SET status = 'expired'
        WHERE date(done_date) < date('now')
        """)
        conn.commit()
        result = cur.execute("""
        SELECT description, done_date FROM tasks WHERE status = ?
        """, (status,)).fetchall()
        result.sort(key=lambda x: x[1])
        conn.close()
        return result

    # стили задач для каждой колонки
    def add_form(self, tasks, status):
        if status == "expired":
            tasks.sort(key=lambda x: x[1])
        self.status_dict = {"to do": self.to_do_list, "doing": self.doing_list, "done": self.done_list}

        for task in tasks:
            item = QListWidgetItem()
            task_widget = TaskWidget(task[0], task[1], status)
            item.setSizeHint(task_widget.sizeHint())

            if status == "expired":
                self.status_dict["done"].addItem(item)
                self.status_dict["done"].setItemWidget(item, task_widget)
            else:
                self.status_dict[status].addItem(item)
                self.status_dict[status].setItemWidget(item, task_widget)

    # отображение задач
    def show_tasks(self):
        self.add_form(self.generate_lst("to do"), "to do")
        self.add_form(self.generate_lst("doing"), "doing")
        self.add_form(self.generate_lst("done"), "done")
        self.add_form(self.generate_lst("expired"), "expired")


# класс для создания формы задач
class TaskWidget(QWidget):
    def __init__(self, description, done_date, status, parent=None):
        super(TaskWidget, self).__init__(parent)

        # Основной контейнер для задачи
        self.setStyleSheet("""
                    background-color: white;
                    border-radius: 10px;
                    border: 1px solid black;
                    padding: 6px;
                    color: black;
                """)

        # Создаем вертикальный контейнер
        layout = QVBoxLayout()

        # Соединяем описание и дату в одной метке
        self.task_info_label = QLabel(f"{description}\n{done_date}")
        self.task_info_label.setStyleSheet("font-size: 18px;")
        # если до дедлайна остался 1 день или задача просрочена - выделяем задачу
        if ((datetime.strptime(done_date, "%Y-%m-%d") - datetime.now()).days <= 1
                and status != "done") or status == "expired":
            self.task_info_label.setStyleSheet("""color: red; font-size: 18px;""")

        # Добавляем метку в вертикальный контейнер
        layout.addWidget(self.task_info_label)

        # self.action_button = QPushButton("->")
        # self.action_button.setFixedSize(30, 30)  # Размер маленькой кнопки
        # layout.addWidget(self.action_button)

        # Устанавливаем главный макет на виджет
        self.setLayout(layout)

        # класс для собственного диалога


class TaskDialog(QDialog):
    def __init__(self, status, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить задачу")

        self.setStyleSheet("font-size: 17px;")

        self.layout = QFormLayout(self)

        self.description_input = QPlainTextEdit(self)
        self.layout.addRow("Описание:", self.description_input)

        self.date_input = QDateEdit(self)
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.layout.addRow("Дата выполнения:", self.date_input)

        # создаем бокс и добавляем кнопки ok и cancel
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.layout.addWidget(self.button_box)

    # нельзя ввести дату в прошлом и поле описания не может быть пустым!
    def accept(self):
        selected_date = self.date_input.date()
        current_date = QDate.currentDate()

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
