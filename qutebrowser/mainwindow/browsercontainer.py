from qutebrowser.qt.widgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)
from qutebrowser.qt.core import Qt


class BrowserContainer(QWidget):
    """Edge-style layout container.

    Vertical arrangement:

        TabRow   (tab bar + "+" button)   <- top row, always visible
        Toolbar  (back / reload / url bar / baidu search)
        tabs     (the TabWidget rendering the page stack)

    The TabBar and its "+" button are owned by the TabWidget, but the
    BrowserContainer plucks them out (Qt layouts re-parent the widgets into
    the TabRow) so no duplicate tab bar is rendered by the page area.
    """

    def __init__(self, toolbar, tab_widget, parent=None):
        super().__init__(parent)

        self.toolbar = toolbar
        self.tabs = tab_widget

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # -- Top tab row: [optional-leading-stretch content ... tabBar | +] --
        self.tab_bar = self.tabs.tabBar()
        # Edge top row stays permanently visible (overrides tabs.show).
        self.tab_bar._edge_always_visible = True

        # Create a thin container whose only published children are the tab
        # bar and the "+" button.
        self.tab_row = QWidget(self)
        row_layout = QHBoxLayout(self.tab_row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(0)

        # The plus button was constructed as a child of the TabWidget; adding
        # it to the row layout re-parents it (exactly once) into tab_row.
        plus_button = self.tabs.plus_button

        row_layout.addWidget(self.tab_bar, 1)
        row_layout.addWidget(plus_button, 0, Qt.AlignmentFlag.AlignCenter)

        # Keep this top row exactly as tall as the tab bar so that the
        # toolbar and page stack start right beneath it.
        #
        # NOTE: an (empty) QTabBar's sizeHint().height() is 0 — using it here
        # would collapse the whole top row.  Use the widget's minimumHeight
        # instead, which is 34 (TabBar calls setFixedHeight(34)).
        row_height = self.tab_bar.minimumHeight()
        if row_height <= 0:
            row_height = 34
        self.tab_row.setFixedHeight(row_height)
        # 单元层为浅色条：顶行与工具栏共享同一浅背景,
        # 激活标签为纯白以与页面形成“相连”的 Edge 观感。
        bar_bg = '#eceff1'
        self.tab_row.setStyleSheet('background-color: %s;' % bar_bg)
        self.toolbar.setStyleSheet('QToolBar { background-color: %s; border: none; }'
                                   % bar_bg)

        self._layout.addWidget(self.tab_row)
        self._layout.addWidget(self.toolbar)
        self._layout.addWidget(self.tabs, 1)
