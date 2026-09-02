from qutebrowser.qt.widgets import (
    QToolBar,
    QPushButton,
    QLineEdit,
    QToolButton,
    QMenu,
    QStyle,
)

from qutebrowser.qt.core import QUrl, QSize

class UrlBar(QLineEdit):

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.selectAll()

class Toolbar(QToolBar):

    def __init__(self, navigate_callback, back_callback, reload_callback,
                 open_new_tab_callback=None, parent=None):
        super().__init__(parent)

        self.navigate_callback = navigate_callback
        self.back_button = QPushButton("←")
        self.reload_button = QPushButton("⟳")

        self.open_new_tab_callback = open_new_tab_callback
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

        # --- 历史记录按钮(弹出最近历史的下拉列) ---------------------------
        self.history_button = QToolButton(self)
        self.history_button.setToolTip("历史记录")
        style = self.style()
        assert style is not None
        self.history_button.setIcon(style.standardIcon(
            QStyle.StandardPixmap.SP_BrowserReload))
        self.history_button.setFixedSize(34, content_h)
        self.history_button.setIconSize(QSize(20, 20))
        self.history_button.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
            }
            QToolButton:hover {
                background: #d8dcdf;
            }
            QToolButton:pressed {
                background: #c5c9cc;
            }
        """)

        self.history_menu = QMenu(self)
        self.history_button.setMenu(self.history_menu)
        self.history_button.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup)
        self.history_menu.aboutToShow.connect(self._populate_history_menu)

        self.addWidget(self.history_button)

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

    # ------------------------------------------------------------------ #
    # History popup : show the latest 30 web-history pages, click opens a
    # new tab.  Data comes straight from qutebrowser's web_history module,
    # so nothing new persists or re-implements storage.
    def _history_url_title(self, entry):
        """Give a stable (url, title) string pair for a history entry."""
        url = entry.url
        urlstr = url.toString() if hasattr(url, 'toString') else str(url)
        title = getattr(entry, 'title', None) or urlstr
        return urlstr, title

    def _populate_history_menu(self):
        menu = self.history_menu
        menu.clear()

        try:
            import time
            from qutebrowser.browser import history as hist_module
            web_history = hist_module.web_history
        except Exception:
            web_history = None

        if web_history is None:
            item = menu.addAction("History unavailable")
            item.setEnabled(False)
            return

        try:
            entries = web_history.entries_before(
                int(time.time()), limit=30)
        except Exception:
            entries = []

        seen = set()
        added = 0
        for entry in entries:
            if added >= 30:
                break
            try:
                urlstr, title = self._history_url_title(entry)
            except Exception:
                continue
            if urlstr in seen or not urlstr:
                continue
            seen.add(urlstr)
            action = menu.addAction(title)
            action.setToolTip(urlstr)
            action.triggered.connect(
                lambda _checked=False, u=urlstr:
                self._open_history_url(u))
            added += 1

        if added == 0:
            item = menu.addAction("No history entries")
            item.setEnabled(False)

    def _open_history_url(self, url):
        cb = self.open_new_tab_callback
        if cb is not None:
            cb(url)