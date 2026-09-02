from qutebrowser.qt.widgets import (
    QToolBar,
    QPushButton,
    QLineEdit,
    QToolButton,
    QMenu,
    QStyle,
    QFrame,
    QListWidget,
    QListWidgetItem,
    QInputDialog,
    QVBoxLayout,
)

from qutebrowser.qt.core import QUrl, QSize, Qt

class UrlBar(QLineEdit):

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.selectAll()

def _bookmarks_manager():
    """Return the active BookmarkManager (already registered by qutebrowser)."""
    try:
        from qutebrowser.utils import objreg
        return objreg.get('bookmark-manager')
    except Exception:
        return None


class FavoritesPopup(QFrame):
    """Row-based favourites list used in place of a plain QMenu.

    Left click opens in the current tab; right-click an entry shows a context
    menu:  New tab / Rename / Delete.
    """

    def __init__(self, toolbar, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName('favorites_popup')
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)

        self.toolbar = toolbar
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        self.list = QListWidget(self)
        self.list.setUniformItemSizes(True)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.itemClicked.connect(self._open_current)
        self.list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._show_context)
        vbox.addWidget(self.list)

        self.setStyleSheet("""
            QListWidget { background: #ffffff; border: 1px solid #d8dcdf;
                          border-radius: 4px; }
            QListWidget::item { padding: 3px 8px; color: #202124; }
            QListWidget::item:hover { background: #eceff1; }
        """)

    # -- helpers ----------------------------------------------------------
    def _display(self, _urlstr, title):
        """Only the name/title is shown in the list."""
        return title if title else ""

    def _refresh(self):
        """(Re)build rows from the manager, keeping current visible."""
        manager = _bookmarks_manager()
        self.list.clear()
        items = list(manager.marks.items()) if manager is not None else []
        for urlstr, title in items:
            display = title if title else urlstr
            item = QListWidgetItem(display, self.list)
            item.setToolTip(urlstr)
            item.setData(Qt.ItemDataRole.UserRole, urlstr)
            item.setData(Qt.ItemDataRole.UserRole + 1, title)

        if not items:
            placeholder = QListWidgetItem("收藏夹为空", self.list)
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)

    def show_at(self, anchor_button):
        """Re-fill and show popup just under the given toolbar button."""
        self._refresh()
        self.adjustSize()
        width = max(self.toolbar.bookmarks_button.width(), 280)
        self.setMinimumWidth(width)
        pos = anchor_button.mapToGlobal(anchor_button.rect().bottomLeft())
        self.setGeometry(pos.x(), pos.y(), width, min(max(self.list.sizeHint().height(), 60), 340))
        self.show()
        self.raise_()
        self.list.setFocus()

    # -- item behaviours --------------------------------------------------
    def _entry(self, item):
        url = item.data(Qt.ItemDataRole.UserRole)
        title = item.data(Qt.ItemDataRole.UserRole + 1)
        return url, title

    def _open_current(self, item):
        url, _ = self._entry(item)
        if not url:
            return
        self.hide()
        cb = self.toolbar.navigate_callback
        if cb is not None and url:
            cb(url)

    def _show_context(self, pos):
        item = self.list.itemAt(pos)
        if item is None:
            return
        url, title = self._entry(item)
        menu = QMenu(self)
        act_new = menu.addAction("在新标签页打开")
        act_rename = menu.addAction("重命名")
        act_del = menu.addAction("删除")
        chosen = menu.exec(self.list.viewport().mapToGlobal(pos))
        if chosen is act_new:
            self.hide()
            cb = self.toolbar.open_new_tab_callback
            if cb is not None and url:
                cb(url)
        elif chosen is act_rename:
            self._rename(url, title)
        elif chosen is act_del:
            self._delete(url)

    def _rename(self, url, old_title):
        new_title, ok = QInputDialog.getText(
            self, "重命名收藏", "书签标题:", text=old_title or '')
        if not ok:
            return
        new_title = new_title.strip()
        if not new_title or new_title == old_title:
            return
        manager = _bookmarks_manager()
        if manager is None:
            return
        # Update only the title through the bookmark manager interface.
        manager.marks[url] = new_title
        manager.changed.emit()
        try:
            manager.save()
        except Exception:
            pass
        self._refresh()
        self.show()

    def _delete(self, url):
        manager = _bookmarks_manager()
        if manager is None:
            return
        if url in manager.marks:
            try:
                manager.delete(url)
            except Exception:
                pass
        self._refresh()
        self.show()


class Toolbar(QToolBar):

    def __init__(self, navigate_callback, back_callback, reload_callback,
                 open_new_tab_callback=None, bookmark_toggle_callback=None,
                 parent=None):
        super().__init__(parent)

        self.navigate_callback = navigate_callback
        self.back_button = QPushButton("←")
        self.reload_button = QPushButton("⟳")

        self.open_new_tab_callback = open_new_tab_callback
        self.bookmark_toggle_callback = bookmark_toggle_callback
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

        # --- 收藏：星标按钮 + 收藏夹下拉；显示在地址栏右侧(历史仍居最右) --
        self.bookmark_button = QToolButton(self)
        self.bookmark_button.setToolTip("收藏当前页面")
        self.bookmark_button.setFixedHeight(content_h)
        self.bookmark_button.setText("☆")
        self._set_bookmarked(False)

        self.bookmarks_button = QToolButton(self)
        self.bookmarks_button.setToolTip("收藏夹")
        self.bookmarks_button.setText("收藏夹")
        self.bookmarks_button.setFixedHeight(content_h)

        self.favorites_pop = FavoritesPopup(self)
        self.bookmarks_button.clicked.connect(self._toggle_favorites_popup)

        for btn in (self.bookmark_button, self.bookmarks_button):
            btn.setStyleSheet("""
                QToolButton {
                    background: transparent;
                    border: none;
                    color: #202124;
                    padding: 0 4px;
                    font-size: 13px;
                }
                QToolButton:hover {
                    background: #d8dcdf;
                }
                QToolButton:pressed {
                    background: #c5c9cc;
                }
            """)

        self.bookmark_button.clicked.connect(self._toggle_bookmark)

        self.addWidget(self.bookmark_button)
        self.addWidget(self.bookmarks_button)

        # --- 历史记录按钮(弹出最近历史的下拉列) ---------------------------
        self.history_button = QToolButton(self)
        self.history_button.setToolTip("历史记录")
        self.history_button.setText("历史")          # 文字钮(与收藏夹统一)
        self.history_button.setFixedHeight(content_h)
        self.history_button.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                color: #202124;
                padding: 0 4px;
                font-size: 13px;
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
            from qutebrowser.browser import history as hist_module
            web_history = hist_module.web_history
        except Exception:
            web_history = None

        if web_history is None:
            item = menu.addAction("History unavailable")
            item.setEnabled(False)
            return

        # Reuse qutebrowser's own recent-history getter (the same database
        # that qute://history shows). Nothing new is stored.
        entries = []
        try:
            entries = list(web_history.get_recent())[:30]
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

    # ------------------------------------------------------------------ #
    # Bookmarks: star a page (uses qutebrowser bookmark-manager via a main
    # window callback) and a "Favourites" dropdown list.
    def _set_bookmarked(self, is_saved):
        """Update the star glyph to represent whether current url is saved."""
        self._bookmarked = bool(is_saved)
        self.bookmark_button.setText("★" if self._bookmarked else "☆")
        self.bookmark_button.setToolTip(
            "取消收藏" if self._bookmarked else "收藏当前页面")

    def _toggle_bookmark(self):
        """Delegate toggling of the current page bookmark to main window."""
        cb = self.bookmark_toggle_callback
        if cb is not None:
            cb()

    def _toggle_favorites_popup(self):
        """Show/hide the favourites list under the toolbar button."""
        pop = self.favorites_pop
        if pop.isVisible():
            pop.hide()
        else:
            pop.show_at(self.bookmarks_button)

    def toggle_favorites_popup(self, visible: bool = None):
        """Programmatically show/hide (used by context actions)."""
        pop = self.favorites_pop
        if (visible is False) or (visible is None and pop.isVisible()):
            pop.hide()
        elif visible is True or not pop.isVisible():
            pop.show_at(self.bookmarks_button)

    def _populate_bookmarks_menu(self):
        menu = self.bookmarks_menu
        menu.clear()
        try:
            from qutebrowser.utils import objreg
            manager = objreg.get('bookmark-manager')
        except Exception:
            manager = None

        if manager is None:
            item = menu.addAction("Bookmarks unavailable")
            item.setEnabled(False)
            return

        for urlstr, title in manager.marks.items():
            label = title if title else urlstr
            if title and urlstr != title:
                label = f"{title} — {urlstr}"
            action = menu.addAction(label)
            action.setToolTip(urlstr)
            action.triggered.connect(
                lambda _checked=False, u=urlstr:
                self.navigate_callback(u) if self.navigate_callback else None)

        if menu.isEmpty():
            item = menu.addAction("No bookmarks yet")
            item.setEnabled(False)