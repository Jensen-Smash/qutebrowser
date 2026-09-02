# SPDX-FileCopyrightText: edge-layout fork authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Edge-like right-hand favourites sidebar (Favorites Bar/Hub).

Shows every saved bookmark as a single title row.  Left click opens the URL in
the current tab; right click offers  New tab / Rename / Delete.  All data
operations go through qutebrowser's existing ``bookmark-manager`` (no new
storage, no direct file edits).
"""

from qutebrowser.qt.widgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QInputDialog,
)
from qutebrowser.qt.core import Qt

WIDTH = 130


def _multiline(text, width=18):
    """Force a string into horizontal chunks so a Qt tooltip never clips.

    Qt shows tooltips as one unbroken line per newline; a very long, unbroken
    title is otherwise cut off at the screen edge.  Emitting a short line per
    chunk guarantees every character can be read.
    """
    text = str(text or '')
    if not text:
        return ''
    lines = [text[i:i + width] for i in range(0, len(text), width)]
    return '\n'.join(lines)


def _bookmarks_manager():
    """Return the active BookmarkManager (registered by qutebrowser)."""
    try:
        from qutebrowser.utils import objreg
        return objreg.get('bookmark-manager')
    except Exception:
        return None


class FavoritesSidebar(QWidget):
    """A fixed-width right-hand list of all bookmarks."""

    def __init__(self, open_current_cb, open_new_tab_cb, parent=None):
        super().__init__(parent)
        self._open_current_cb = open_current_cb
        self._open_new_tab_cb = open_new_tab_cb
        self._connected = False

        self.setObjectName('favorites_sidebar')
        self.setFixedWidth(WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget(self)
        header.setFixedHeight(32)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 8, 0)
        title = QLabel("收藏夹", header)
        header_layout.addWidget(title)
        header_layout.addStretch(1)
        layout.addWidget(header)

        self.list = QListWidget(self)
        self.list.setUniformItemSizes(True)
        self.list.itemClicked.connect(self._open_current)
        self.list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._show_context)
        layout.addWidget(self.list, 1)

        self.setStyleSheet("""
            QWidget#favorites_sidebar {
                background-color: #f7f8f9;
                border-left: 1px solid #d8dcdf;
            }
            QWidget#favorites_sidebar QLabel {
                color: #3c4043;
                font-size: 14px;
                font-weight: 600;
            }
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                color: #202124;
                padding: 6px 10px;
            }
            QListWidget::item:hover {
                background: #e8eaed;
            }
            QListWidget::item:selected {
                background: #d2e3fc;
                color: #202124;
            }
        """)

    # -- helpers ----------------------------------------------------------

    def _entry(self, item):
        url = item.data(Qt.ItemDataRole.UserRole)
        title = item.data(Qt.ItemDataRole.UserRole + 1)
        return url, title

    def _ensure_connected(self):
        """Subscribe to manager.changed (once) so the list auto-refreshes."""
        if self._connected:
            return
        manager = _bookmarks_manager()
        if manager is None:
            return
        manager.changed.connect(self._refresh)
        self._connected = True

    def _refresh(self):
        """Rebuild the list from the bookmark manager."""
        self._ensure_connected()
        manager = _bookmarks_manager()
        self.list.clear()
        items = list(manager.marks.items()) if manager is not None else []
        for urlstr, title in items:
            display = title if title else urlstr
            item = QListWidgetItem(display, self.list)
            # Hover tooltip shows the full stored title, wrapped onto several
            # short lines so nothing can be clipped (fall back to the url when
            # no title exists).
            tooltip = _multiline(title if title else urlstr)
            item.setToolTip(tooltip)
            item.setData(Qt.ItemDataRole.UserRole, urlstr)
            item.setData(Qt.ItemDataRole.UserRole + 1, title)

        if not items:
            placeholder = QListWidgetItem("暂无收藏", self.list)
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)

    def showEvent(self, event):
        """Refresh whenever the sidebar becomes visible again."""
        super().showEvent(event)
        self._refresh()

    # -- item behaviours --------------------------------------------------

    def _open_current(self, item):
        """Left click: open the URL in the current tab (existing behaviour)."""
        url, _ = self._entry(item)
        if not url or self._open_current_cb is None:
            return
        self._open_current_cb(url)

    def _show_context(self, pos):
        """Right click: New tab / Rename / Delete for the entry under pos."""
        item = self.list.itemAt(pos)
        if item is None:
            return
        url, title = self._entry(item)
        if not url:
            return
        menu = QMenu(self)
        act_new = menu.addAction("在新标签页打开")
        act_rename = menu.addAction("重命名")
        act_del = menu.addAction("删除")
        chosen = menu.exec(self.list.viewport().mapToGlobal(pos))
        if chosen is act_new:
            if self._open_new_tab_cb is not None:
                self._open_new_tab_cb(url)
        elif chosen is act_rename:
            self._rename(url, title)
        elif chosen is act_del:
            self._delete(url)

    def _rename(self, url, old_title):
        """Rename only the title; URL and storage stay untouched."""
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
        manager.marks[url] = new_title
        manager.changed.emit()
        try:
            manager.save()
        except Exception:
            pass
        self._refresh()

    def _delete(self, url):
        """Delete via the bookmark manager and refresh in place."""
        manager = _bookmarks_manager()
        if manager is None:
            return
        if url in manager.marks:
            try:
                manager.delete(url)
            except Exception:
                pass
        self._refresh()
