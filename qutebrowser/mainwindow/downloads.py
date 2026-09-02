# SPDX-FileCopyrightText: edge-layout fork authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Right-hand downloads sidebar (Edge-like, directory-backed for history).

Displays every file currently present in the default downloads folder.
Finished files are opened with the OS handler; right-click offers
Open-folder / Remove-from-list / Delete-file (with confirmation).
Removed-from-list only hides the row for this session; the file keeps existing.

Note: percent state for paused/failed in-progress transfers cannot be fully
recovered without a history database (a2 trade-off) - active partial files
are marked with a neutral "…".
"""

import os
import time
import datetime
import subprocess

from qutebrowser.qt.widgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
)
from qutebrowser.qt.core import Qt

WIDTH = 240
_DOWNLOADS_DIR = 'C:/Users/y1787/Downloads'


def _fmt_time(ts):
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')


def _open_with_system(path):
    """Open with OS default application (never in the browser)."""
    path = os.path.abspath(path)
    try:
        if os.name == 'nt':  # pylint: disable=no-member
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(['xdg-open', path])
    except Exception as exc:  # noqa: BLE001 - surface to user
        from qutebrowser.utils import message
        message.error("无法打开 {}：{}".format(path, exc))


def _open_folder(path=None):
    try:
        folder = os.path.abspath(path or _DOWNLOADS_DIR)
        if os.name == 'nt':  # pylint: disable=no-member
            os.startfile(folder)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(['xdg-open', folder])
    except Exception as exc:  # noqa: BLE001
        from qutebrowser.utils import message
        message.error("无法打开文件夹 {}：{}".format(folder, exc))


class DownloadsSidebar(QWidget):
    """Right sidebar listing files under the download directory."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hidden = set()  # relpaths hidden this session (keep file!)

        self.setObjectName('downloads_sidebar')
        self.setFixedWidth(WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget(self)
        header.setFixedHeight(32)
        hh = QHBoxLayout(header)
        hh.setContentsMargins(12, 0, 8, 0)
        title = QLabel("下载", header)
        hh.addWidget(title)
        hh.addStretch(1)
        layout.addWidget(header)

        self.list = QListWidget(self)
        self.list.setUniformItemSizes(True)
        self.list.itemClicked.connect(self._on_click)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._on_context)
        layout.addWidget(self.list, 1)

        self.setStyleSheet("""
            QWidget#downloads_sidebar {
                background-color: #f7f8f9;
                border-left: 1px solid #d8dcdf;
            }
            QWidget#downloads_sidebar QLabel {
                color: #3c4043; font-size: 14px; font-weight: 600;
            }
            QListWidget { background: transparent; border: none; outline: none; }
            QListWidget::item {
                color: #202124; padding: 5px 8px;
            }
            QListWidget::item:hover { background: #e8eaed; }
            QListWidget::item:selected { background: #d2e3fc; color: #202124; }
        """)

    # -- data -------------------------------------------------------------
    def _scan(self):
        """Return absolute paths newest-first, skipping folders/hidden rows."""
        folder = _DOWNLOADS_DIR
        items = []
        try:
            names = os.listdir(folder)
        except OSError:
            names = []
        for name in names:
            rel = name
            if rel in self._hidden:
                continue
            full = os.path.join(folder, name)
            if not os.path.isfile(full):
                continue  # directories down arrows not offered
            try:
                mtime = os.path.getmtime(full)
            except OSError:
                mtime = 0
            items.append((mtime, rel, full))
        items.sort(key=lambda x: x[0], reverse=True)
        return items

    def _refresh(self):
        self.list.clear()
        for _mtime, rel, full in self._scan():
            is_partial = rel.endswith('.part')
            if is_partial:
                label = "{}  · 下载中…".format(rel)
            else:
                label = "{}  ·{}".format(
                    rel, _fmt_time(os.path.getmtime(full)))
            item = QListWidgetItem(label, self.list)
            item.setData(Qt.ItemDataRole.UserRole, full)
            item.setData(Qt.ItemDataRole.UserRole + 1, rel)
        if self.list.count() == 0:
            ph = QListWidgetItem("暂无下载", self.list)
            ph.setFlags(Qt.ItemFlag.NoItemFlags)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh()

    # -- rows helpers -----------------------------------------------------
    def _row(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        rel = item.data(Qt.ItemDataRole.UserRole + 1)
        return path, rel

    def _on_click(self, item):
        path, _ = self._row(item)
        if not path or not os.path.isfile(path):
            return
        _open_with_system(path)

    def _on_context(self, pos):
        item = self.list.itemAt(pos)
        if item is None:
            return
        path, rel = self._row(item)
        if not path:
            return
        menu = QMenu(self)
        a_folder = menu.addAction("打开下载文件夹")
        a_delrec = menu.addAction("删除记录")
        a_delfile = menu.addAction("删除文件")
        chosen = menu.exec(self.list.viewport().mapToGlobal(pos))
        if chosen is a_folder:
            _open_folder()
        elif chosen is a_delrec:
            self._hidden.add(rel)
            self._refresh()
        elif chosen is a_delfile:
            self._delete_file(path, rel)

    def _delete_file(self, path, rel):
        """Delete the real file + row, with confirmation & exception guards."""
        if not os.path.isfile(path):
            from qutebrowser.utils import message
            message.error("文件不存在：{}".format(path))
            return
        ans = QMessageBox.question(
            self, "删除文件",
            "确定从磁盘删除下载文件并移除侧栏记录？\n\n{}".format(path),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if ans != QMessageBox.StandardButton.Yes:
            return
        try:
            os.remove(path)
        except FileNotFoundError:
            from qutebrowser.utils import message
            message.info("文件已被移除")
        except OSError as exc:
            from qutebrowser.utils import message
            message.error("删除失败：{}".format(exc))
            return
        self._hidden.add(rel)
        self._refresh()
