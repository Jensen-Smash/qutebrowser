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

        # 内容高 < 工具栏总高（toolbar 被容器固定为 32）：上下各留 ~2px，
        # 使按钮与地址栏在栏内“比工具栏稍矮”，观感更饱满且居中。
        content_h = 28
        self.back_button.setFixedHeight(content_h)
        self.reload_button.setFixedHeight(content_h)
        self.url_bar.setFixedHeight(content_h)

        # 与浅色 Chrome 一致的工具条按钮(容器再以统一浅背景底色并齐)
        self.setStyleSheet("""
            QToolBar { background-color: transparent; border: none; }

            QToolBar QPushButton {
                background: transparent;
                color: #202124;
                border: none;
                border-radius: 6px;
                padding: 2px 6px;
                font-size: 15px;
                font-weight: bold;
            }
            QToolBar QPushButton:hover {
                background: #d8dcdf;
            }
            QToolBar QPushButton:pressed {
                background: #c5c9cc;
            }
            QToolBar QPushButton:disabled {
                color: #a5a9ad;
            }

            QToolBar QLineEdit {
                background-color: #ffffff;
                border: 1px solid #d8dcdf;
                border-radius: 7px;
                color: #202124;
                padding: 0 8px;
                selection-background-color: #bcd8f8;
                selection-color: #202124;
            }
            QToolBar QLineEdit:focus {
                border-color: #8ab4f8;
            }
        """)


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