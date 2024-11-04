from PyQt6.QtWidgets import QListWidget, QAbstractItemView
from PyQt6.QtCore import Qt


class CustomListWidget(QListWidget):
    def __init__(self, parent=None):
        super(CustomListWidget, self).__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            super(CustomListWidget, self).dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            super(CustomListWidget, self).dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            # event.setDropAction(QtCore.Qt.MoveAction)
            super(CustomListWidget, self).dropEvent(event)
