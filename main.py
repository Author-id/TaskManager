import sys
from PyQt6 import uic
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit,
    QDateEdit, QDialog, QDialogButtonBox,
    QFormLayout, QMessageBox, QWidget, QLabel,
    QListWidgetItem, QVBoxLayout, QPushButton,
    QMenu, QInputDialog, QListWidget
)
from design import Ui_TaskManager
from functools import partial
from datetime import datetime
from PyQt6.QtCore import QDate, Qt
import sqlite3


# основной класс
class TaskManager(QMainWindow, Ui_TaskManager):
    def __init__(self):
        super(TaskManager, self).__init__()
        uic.loadUi('design.ui', self)

        # создание бд
        conn = sqlite3.connect("tasks.db")
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS tasks
                         (id INTEGER PRIMARY KEY,
                          description TEXT NOT NULL,
                          done_date TEXT,
                          status TEXT)''')
        conn.commit()
        conn.close()

        self.request = None  # запрос на сортировку
        self.sorted_lists = []  # отсортированные списки
        self.status_dict = {"to do": self.to_do_list, "doing": self.doing_list, "done": self.done_list}
        self.show_tasks()
        # кнопки добавления задач
        self.add_to_do_btn.clicked.connect(lambda: self.open_task_dialog("to do"))
        self.add_doing_btn.clicked.connect(lambda: self.open_task_dialog("doing"))
        self.add_done_btn.clicked.connect(lambda: self.open_task_dialog("done"))

        # кнопки сортировки задач
        self.sort_to_do_btn.clicked.connect(lambda: self.sort_widgets("to do"))
        self.sort_doing_btn.clicked.connect(lambda: self.sort_widgets("doing"))
        self.sort_done_btn.clicked.connect(lambda: self.sort_widgets("done"))

        # установка контекстного меню
        for task_list in [self.to_do_list, self.doing_list, self.done_list]:
            task_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            # передаем task_list в качестве дополнительного параметра
            # вызываем контекстное меню нажатием правой кнопкой мыши по задаче
            task_list.customContextMenuRequested.connect(partial(self.show_context_menu, task_list=task_list))
            # изменение порядка в колонках
            task_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)

    # функция для чтения данных от пользователя
    def open_task_dialog(self, status):
        dialog = TaskDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            description = dialog.description_input.toPlainText()  # описание
            done_date = dialog.date_input.date().toString("yyyy-MM-dd")  # дата окончания
            self.add_task(description, done_date, status)

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

    # сортировка по дате при нажатии на кнопку
    def sort_widgets(self, status):
        self.request = status
        if status not in self.sorted_lists:
            self.sorted_lists.append(status)
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
        if status in self.sorted_lists:  # сортируем по дате
            result.sort(key=lambda x: x[1])
        conn.close()
        return result

    # стили задач для каждой колонки
    def add_form(self, tasks, status):
        if status == "expired":
            tasks.sort(key=lambda x: x[1])

        for task in tasks:
            item = QListWidgetItem()
            task_widget = TaskWidget(task[0], task[1], status)
            item.setSizeHint(task_widget.sizeHint())

            # добавляем задачи в колонки
            if status == "expired":
                self.status_dict["done"].addItem(item)
                self.status_dict["done"].setItemWidget(item, task_widget)
            else:
                self.status_dict[status].addItem(item)
                self.status_dict[status].setItemWidget(item, task_widget)

    # отображение задач
    def show_tasks(self):
        # очищаем и заполняем колонки
        for widget in self.status_dict.values():
            widget.clear()
        self.add_form(self.generate_lst("to do"), "to do")
        self.add_form(self.generate_lst("doing"), "doing")
        self.add_form(self.generate_lst("done"), "done")
        self.add_form(self.generate_lst("expired"), "expired")

    # отображение контекстного меню
    def show_context_menu(self, position, task_list):
        menu = QMenu(self)  # Создаем объект контекстного меню

        edit_action = menu.addAction("Редактировать")
        delete_action = menu.addAction("Удалить")

        # Отображаем меню и получаем выбранное пользователем действие
        action = menu.exec(task_list.mapToGlobal(position))
        if action == edit_action:
            self.edit_task(task_list)
        elif action == delete_action:
            self.delete_task(task_list)

    # редактирование задач
    def edit_task(self, task_list):
        item = task_list.currentItem()  # текущая задача
        if item:
            task_widget = task_list.itemWidget(item)
            if task_widget:
                old_description = task_widget.get_description()  # достаем старое описание
                new_description, ok = QInputDialog.getText(self, 'Редактирование задачи', 'Описание:',
                                                           text=old_description)
                if ok and new_description:
                    conn = sqlite3.connect("tasks.db")
                    cur = conn.cursor()
                    # обновляем описание
                    cur.execute("UPDATE tasks SET description = ? WHERE description = ?",
                                (new_description, old_description))
                    conn.commit()
                    conn.close()
                    self.show_tasks()

    # удаление задач
    def delete_task(self, task_list):
        item = task_list.currentItem()
        if item:
            task_widget = task_list.itemWidget(item)
            if task_widget:
                description = task_widget.get_description()
                reply = QMessageBox.question(self, 'Удаление задачи', f'Удалить "{description}"?',
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                             QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    conn = sqlite3.connect("tasks.db")
                    cur = conn.cursor()
                    # удаляем задачу
                    cur.execute("DELETE FROM tasks WHERE description = ?", (description,))
                    conn.commit()
                    self.show_tasks()


# класс для создания формы задач
class TaskWidget(QWidget):
    def __init__(self, description, done_date, status, parent=None):
        self.description = description
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

    # получение описания
    def get_description(self):
        return self.description


# класс для собственного диалога
class TaskDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить задачу")

        self.setStyleSheet("font-size: 17px;")

        self.layout = QFormLayout(self)

        self.description_input = QPlainTextEdit(self)
        self.layout.addRow("Описание:", self.description_input)

        self.date_input = QDateEdit(self)
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())  # по умолчанию текущая дата
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
