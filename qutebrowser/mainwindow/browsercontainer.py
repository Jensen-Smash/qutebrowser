from qutebrowser.qt.widgets import QWidget, QVBoxLayout


class BrowserContainer(QWidget):

    def __init__(self, toolbar, parent=None):
        super().__init__(parent)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(
            0, 0, 0, 0
        )
        self._layout.setSpacing(0)

        self.toolbar = toolbar

        self._layout.addWidget(
            self.toolbar
        )