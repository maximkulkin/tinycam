from PySide6 import QtWidgets


class PushButton(QtWidgets.QPushButton):
    def paintEvent(self, event):
        painter = QtWidgets.QStylePainter(self)
        options = QtWidgets.QStyleOptionButton();
        self.initStyleOption(options)
        options.rect = self.rect().adjusted(0, -2, 0, -2)
        painter.drawControl(QtWidgets.QStyle.CE_PushButton, options)
