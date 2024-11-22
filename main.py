import sys
from PyQt6 import uic, QtGui
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit,
    QDateEdit, QDialog, QDialogButtonBox,
    QFormLayout, QMessageBox, QWidget, QLabel,
    QListWidgetItem, QVBoxLayout, QPushButton,
    QMenu, QInputDialog, QListWidget, QAbstractItemView
)
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QDrag, QPixmap
from PyQt6.QtCore import QDate, Qt, QMimeData, QByteArray, QDataStream, QIODevice
from design import Ui_TaskManager
from functools import partial
from datetime import datetime
import sqlite3


# основной класс
class TaskManager(QMainWindow, Ui_TaskManager):
    def __init__(self):
        super(TaskManager, self).__init__()
        uic.loadUi('design.ui', self)

        self.sorted_lists = []  # отсортированные списки
        self.status_dict = {"to do": self.to_do_list, "doing": self.doing_list, "done": self.done_list}
        self.btn_dict = {"to do": self.add_to_do_ex_btn, "doing": self.add_doing_ex_btn, "done": self.add_done_ex_btn}

        # переопределение кнопок и колонок со статусами под класс CustomListWidget и задание стилей
        self.to_do_lst = CustomListWidget("to do", self)
        self.add_to_do_btn = QPushButton("+", self)
        self.remake_to_custom(self.to_do_lst, self.add_to_do_btn, "to do")

        self.doing_lst = CustomListWidget("doing", self)
        self.add_doing_btn = QPushButton("+", self)
        self.remake_to_custom(self.doing_lst, self.add_doing_btn, "doing")

        self.done_lst = CustomListWidget("done", self)
        self.add_done_btn = QPushButton("+", self)
        self.remake_to_custom(self.done_lst, self.add_done_btn, "done")

        # создание бд
        conn = sqlite3.connect("tasks.db")
        cur = conn.cursor()
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS tasks
             (id INTEGER PRIMARY KEY,
              description TEXT NOT NULL,
              done_date TEXT,
              status TEXT,
              marked INTEGER NOT NULL)'''
        )
        conn.commit()
        conn.close()

        # кнопки добавления задач
        self.add_to_do_btn.clicked.connect(lambda: self.open_task_dialog("to do"))
        self.add_doing_btn.clicked.connect(lambda: self.open_task_dialog("doing"))
        self.add_done_btn.clicked.connect(lambda: self.open_task_dialog("done"))

        # кнопки сортировки задач
        self.sort_to_do_btn.clicked.connect(lambda: self.sort_widgets("to do"))
        self.sort_doing_btn.clicked.connect(lambda: self.sort_widgets("doing"))
        self.sort_done_btn.clicked.connect(lambda: self.sort_widgets("done"))

        # установка контекстного меню и режима перемещения
        for task_list in self.status_dict.values():
            task_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            # передаем task_list в качестве дополнительного параметра
            # вызываем контекстное меню нажатием правой кнопкой мыши по задаче
            task_list.customContextMenuRequested.connect(partial(self.show_context_menu, task_list=task_list))
            # устанавливаем режим перемещения
            task_list.setAcceptDrops(True)
            task_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
            # установка расстояния между объектами
            task_list.setSpacing(-4)

        self.show_tasks()

    # переопределение колонок под кастомный класс
    def remake_to_custom(self, task_list, btn, status):
        task_list.setGeometry(self.status_dict[status].geometry())  # расположение и размеры
        task_list.setStyleSheet(self.status_dict[status].styleSheet())  # стили
        self.status_dict[status] = task_list
        btn.setGeometry(self.btn_dict[status].geometry())
        btn.setStyleSheet(self.btn_dict[status].styleSheet())
        font = QtGui.QFont()
        font.setPointSize(25)  # размер текста
        btn.setFont(font)

    # чтение данных от пользователя
    def open_task_dialog(self, status):
        dialog = TaskDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            description = dialog.description_input.toPlainText()  # описание
            done_date = dialog.date_input.date().toString("yyyy-MM-dd")  # дата окончания
            self.add_task(description, done_date, status)

    # добавление задач в базу
    def add_task(self, description, done_date, status):
        conn = sqlite3.connect("tasks.db")
        cur = conn.cursor()
        try:
            cur.execute('''
                        INSERT INTO tasks (description, done_date, status, marked) VALUES (?, ?, ?, ?)
                    ''', (description, done_date, status, 0))
        except sqlite3.Error as error:
            print(f"Ошибка: {error}")
        finally:
            conn.commit()
            conn.close()
            self.show_tasks()

    # сортировка по дате при нажатии на кнопку
    def sort_widgets(self, status):
        if status not in self.sorted_lists:
            self.sorted_lists.append(status)
        self.show_tasks()

    # генерация списков из задач
    def generate_lst(self, status):
        conn = sqlite3.connect("tasks.db")
        cur = conn.cursor()
        # меняем статус просроченных задач
        cur.execute("""
        UPDATE tasks
        SET status = 'expired'
        WHERE date(done_date) < date('now') and status != 'done'
        """)
        conn.commit()
        result = cur.execute("""
        SELECT id, description, done_date, marked FROM tasks WHERE status = ?
        """, (status,)).fetchall()
        if status in self.sorted_lists:  # сортируем по дате
            result.sort(key=lambda x: x[2])
        conn.close()
        return result

    # стили задач для каждой колонки
    def add_form(self, tasks, status):
        if status == "expired":
            tasks.sort(key=lambda x: x[2])

        for task in tasks:
            item = QListWidgetItem()
            task_widget = TaskWidget(task[0], task[1], task[2], status, task[3])
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
        menu.setStyleSheet("""
            border: 1px solid black;
        """)
        mark_action = menu.addAction("Важное")  # пометить задачу как важную
        edit_action = menu.addAction("Редактировать")
        delete_action = menu.addAction("Удалить")

        # Отображаем меню и получаем выбранное пользователем действие
        action = menu.exec(task_list.mapToGlobal(position))
        if action == edit_action:
            self.edit_task(task_list)
        elif action == delete_action:
            self.delete_task(task_list)
        elif action == mark_action:
            self.mark_task(task_list)

    # редактирование задач
    def edit_task(self, task_list):
        item = task_list.currentItem()  # текущая задача
        if item:
            task_widget = task_list.itemWidget(item)  # получаем виджет
            if task_widget:
                task_id = task_widget.get_id()
                old_description = task_widget.get_description()  # достаем старое описание
                new_description, ok = QInputDialog.getText(self, "Редактирование задачи", "Описание:",
                                                           text=old_description)
                if ok and new_description:
                    conn = sqlite3.connect("tasks.db")
                    cur = conn.cursor()
                    # обновляем описание
                    cur.execute("UPDATE tasks SET description = ? WHERE id = ?",
                                (new_description, task_id))
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
                # запрашиваем подтверждение
                reply = QMessageBox.question(self, 'Удаление задачи', f'Удалить "{description}"?',
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                             QMessageBox.StandardButton.Yes)
                if reply == QMessageBox.StandardButton.Yes:
                    conn = sqlite3.connect("tasks.db")
                    cur = conn.cursor()
                    # удаляем задачу
                    current_id = task_widget.get_id()  # получаем id
                    cur.execute("DELETE FROM tasks WHERE id = ?", (current_id,))
                    conn.commit()
                    self.show_tasks()

    # функция для пометки задач
    def mark_task(self, task_list):
        item = task_list.currentItem()
        if item:
            task_widget = task_list.itemWidget(item)
            if task_widget:
                task_id = task_widget.get_id()
                conn = sqlite3.connect("tasks.db")
                cur = conn.cursor()
                # обновляем значение поля marked
                if task_widget.get_marked() == 0:
                    cur.execute("UPDATE tasks SET marked = ? WHERE id = ?", (1, task_id))
                else:
                    cur.execute("UPDATE tasks SET marked = ? WHERE id = ?", (0, task_id))
                conn.commit()
                conn.close()
                self.show_tasks()


# кастомный расширенный класс для реализации режима DragDropMde
class CustomListWidget(QListWidget):
    def __init__(self, status, parent=None):
        super(CustomListWidget, self).__init__(parent)
        self.status = status  # Статус задач в данном списке

        # Установка режимов
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)  # однократный выбор
        self.setDragEnabled(True)  # Включение перетаскивания элементов
        self.setAcceptDrops(True)  # Разрешение на прием сброса элементов
        self.setDropIndicatorShown(True)  # Показ индикатора сброса при перемещении
        self.setDefaultDropAction(Qt.DropAction.MoveAction)  # перемещение по умолчанию

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()  # позиция начала
        super().mousePressEvent(event)

    def startDrag(self, supportedActions):
        item = self.currentItem()  # текущий элемент
        widget = self.itemWidget(item)  # получаем виджет
        if widget is None:
            return

        # Создаем QMimeData для передачи данных элемента
        mime_data = QMimeData()
        data = QByteArray()
        stream = QDataStream(data, QIODevice.OpenModeFlag.WriteOnly)
        # Записываем описание, дату выполнения и ID задачи в поток данных
        stream.writeQString(widget.get_description())
        stream.writeQString(widget.get_done_date())
        stream.writeInt(widget.get_id())
        stream.writeInt(widget.get_marked())
        mime_data.setData('application/x-item', data)

        # Создаем изображение, чтобы отобразить во время перетаскивания
        pixmap = QPixmap(widget.size())
        widget.render(pixmap)

        # Настройка объекта QDrag
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.setPixmap(pixmap)

        # Вычисляем горячую точку, чтобы объект взялся за правильное место
        if self.drag_start_position:
            rect = self.visualItemRect(item)
            hotSpot = self.drag_start_position - rect.topLeft()
            drag.setHotSpot(hotSpot)

        # Начинаем перемещение элемента
        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event: QDragEnterEvent):
        # Проверяем формат данных и решаем принимать или игнорировать событие
        if event.mimeData().hasFormat('application/x-item'):  # проверяем что объект нестандартного типа
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragEnterEvent):
        # Устанавливаем действие перемещения и принимаем событие, если данные в нужном формате
        if event.mimeData().hasFormat('application/x-item'):
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        # Проверяем формат данных при сбросе
        if event.mimeData().hasFormat('application/x-item'):
            data = event.mimeData().data('application/x-item')
            stream = QDataStream(data, QIODevice.OpenModeFlag.ReadOnly)
            # Извлекаем описание, дату выполнения и ID задачи
            description = stream.readQString()
            done_date = stream.readQString()
            task_id = stream.readInt()
            is_marked = stream.readInt()

            # Подготовка к добавлению нового элемента в текущий список
            new_item = QListWidgetItem()
            new_task_widget = TaskWidget(task_id, description, done_date, self.status, is_marked)
            new_item.setSizeHint(new_task_widget.sizeHint())
            # Добавляем элемент в список и привязываем к нему виджет
            self.addItem(new_item)
            self.setItemWidget(new_item, new_task_widget)

            # Обновляем статус задачи
            self.update_task_status(new_task_widget, self.status)

            # Удаляем элемент из источника
            source = event.source()
            if source:
                for i in range(source.count()):
                    item = source.item(i)
                    widget = source.itemWidget(item)
                    # Проверяем совпадение ID
                    if widget.get_id() == task_id:
                        source.takeItem(i)
                        break
            # Устанавливаем действие перемещения и принимаем событие
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
        else:
            event.ignore()

    def update_task_status(self, task_widget, status):
        task_id = task_widget.get_id()  # получаем ID

        # Обновление статуса задачи в базе данных
        conn = sqlite3.connect("tasks.db")
        cur = conn.cursor()
        try:
            cur.execute('UPDATE tasks SET status = ? WHERE id = ?', (status, task_id))
            conn.commit()
        except sqlite3.Error as error:
            print("Ошибка базы данных:", error)
        finally:
            conn.close()


# класс для создания формы задач
class TaskWidget(QWidget):
    def __init__(self, id, description, done_date, status, is_marked, parent=None):
        self.description = description
        self.id = id
        self.status = status
        self.done_date = done_date
        self.is_marked = is_marked
        super(TaskWidget, self).__init__(parent)

        # основной контейнер для задачи
        if is_marked == 0:  # проверяем задачу на пометку "важное"
            self.setStyleSheet("""
                background-color: white;
                border-radius: 10px;
                border: 1px solid black;
                padding: 4px;
                color: black;
            """)
        else:
            self.setStyleSheet("""
                background-color: rgb(255, 249, 210);
                border-radius: 10px;
                border: 1px solid rgb(202, 159, 58);
                padding: 4px;
                color: black;
            """)

        # Создаем вертикальный контейнер
        layout = QVBoxLayout()

        # Соединяем описание и дату в одной метке
        done_date_obj = datetime.strptime(done_date, "%Y-%m-%d")  # преобразовываем в нужный формат
        self.task_info_label = QLabel(f"{description}\n{done_date_obj.strftime('%d.%m.%Y')}")
        self.task_info_label.setStyleSheet("font-size: 18px;")

        # если до дедлайна остался 1 день или задача просрочена - выделяем задачу
        if ((datetime.strptime(done_date, "%Y-%m-%d") - datetime.now()).days < 1
            and status != "done") or status == "expired":
            self.task_info_label.setStyleSheet("""color: red; font-size: 18px;""")

        # Добавляем метку в вертикальный контейнер
        layout.addWidget(self.task_info_label)

        # Устанавливаем главный макет на виджет
        self.setLayout(layout)

    def get_description(self):  # получение описания
        return self.description

    def get_done_date(self):  # получение даты
        return self.done_date

    def get_id(self):  # получение id
        return self.id

    def get_status(self):  # получение статуса
        return self.status

    def get_marked(self):  # получение поля marked
        return self.is_marked


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
