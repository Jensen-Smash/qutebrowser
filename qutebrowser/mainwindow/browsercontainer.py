from qutebrowser.qt.widgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)
from qutebrowser.qt.core import Qt

from qutebrowser.mainwindow.favorites import FavoritesSidebar


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

        row_layout.addWidget(self.tab_bar, 0)  # tabs sized by content, not stretched
        row_layout.addWidget(plus_button, 0, Qt.AlignmentFlag.AlignCenter)

        # Keep this top row exactly as tall as the tab bar so that the
        # toolbar and page stack start right beneath it.
        #
        # NOTE: an (empty) QTabBar's sizeHint().height() is 0 — using it here
        # would collapse the whole top row.  Use the widget's minimumHeight
        # instead, which is pinned by TabBar.setFixedHeight() (currently 32).
        row_height = self.tab_bar.minimumHeight()
        if row_height <= 0:
            row_height = 34
        self.tab_row.setFixedHeight(row_height)

        # Keep the toolbar the same height as the tab row so both chrome rows
        # read as one uniform bar (Edge-like).
        self.toolbar.setFixedHeight(row_height)
        # 单元层为浅色条：顶行与工具栏共享同一浅背景,
        # 激活标签为纯白以与页面形成“相连”的 Edge 观感。
        bar_bg = '#eceff1'
        self.tab_row.setStyleSheet('background-color: %s;' % bar_bg)
        self.toolbar.setStyleSheet('QToolBar { background-color: %s; border: none; }'
                                   % bar_bg)

        # -- ContentArea: [webview (stretch) | FavoritesSidebar (fixed)] ----
        self.content_area = QWidget(self)
        content_layout = QHBoxLayout(self.content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.sidebar = FavoritesSidebar(
            open_current_cb=self.toolbar.navigate_callback,
            open_new_tab_cb=self.toolbar.open_new_tab_callback,
            parent=self.content_area)
        self.sidebar.hide()

        content_layout.addWidget(self.tabs, 1)
        content_layout.addWidget(self.sidebar, 0)

        self._layout.addWidget(self.tab_row)
        self._layout.addWidget(self.toolbar)
        self._layout.addWidget(self.content_area, 1)

        self.toolbar.set_favorites_active(False)
        self.toolbar.favorites_toggle_requested.connect(
            self.toggle_favorites_sidebar)

    def toggle_favorites_sidebar(self):
        """Show/hide the right-hand favorites sidebar."""
        visible = not self.sidebar.isVisible()
        self.sidebar.setVisible(visible)
        self.toolbar.set_favorites_active(visible)
