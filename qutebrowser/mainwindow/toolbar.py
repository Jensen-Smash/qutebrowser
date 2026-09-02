from qutebrowser.qt.widgets import (
    QToolBar,
    QPushButton,
    QLineEdit
)

from qutebrowser.qt.core import QUrl

class UrlBar(QLineEdit):

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.selectAll()

class Toolbar(QToolBar):

    def __init__(self,navigate_callback,back_callback,reload_callback,parent=None):
        super().__init__(parent)

        self.navigate_callback = navigate_callback
        self.back_button = QPushButton("←")
        self.reload_button = QPushButton("⟳")

        self.back_callback = back_callback
        self.reload_callback = reload_callback

        self.url_bar = UrlBar()
        self.url_bar.setPlaceholderText(
            "Search or enter address"
        )

        # 输入完成后触发
        self.url_bar.returnPressed.connect(
            self.search_baidu
        )

        self.back_button.clicked.connect(self.back_callback)
        self.reload_button.clicked.connect(self.reload_callback)
        self.addWidget(self.back_button)
        self.addWidget(self.reload_button)
        self.addWidget(self.url_bar)


    def search_baidu(self):
        text = self.url_bar.text()

        if not text:
            return

        if text.startswith("http://") or text.startswith("https://"):
            url = text
        else:
            url = "https://www.baidu.com/s?wd=" + text

        self.navigate_callback(url)

    def set_url(self, url):
        self.url_bar.setText(url)

    def set_back_enabled(self, enabled):
        self.back_button.setEnabled(enabled)