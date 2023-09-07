
# STANDARD LIBS
import sys; sys.path.append('..')
from functools import partial

# THIRD PARTY LIBS
import pandas
from pandas.core.frame import DataFrame
from PySide6.QtWidgets import QApplication, QCheckBox ,QGridLayout, QLineEdit ,QWidget
from PySide6.QtCore import Qt, QRegularExpression

# CUSTOM LIBS
from dimsumpy.qt.dataframemodel import DataFrameModel

# PROGRAM MODULES
from database_update.stock_list_model import stock_list_dict
from database_update.postgres_connection_model import execute_pandas_read

from general_update.gui_model import MySortFilterProxyModel 
from core_stock_browser.core_browser_view import CoreBrowserView
from typing import Any, List, Tuple


class CoreBrowserController(CoreBrowserView):
    def __init__(self) -> None:
        super().__init__()
        self.b_list_guru.clicked.connect(self.load_table)
        self.b_le_guru.clicked.connect(self.load_table)

        self.b_list_zacks.clicked.connect(self.load_table)
        self.b_le_zacks.clicked.connect(self.load_table)
        self.b_list_option.clicked.connect(self.load_table)
        self.b_le_option.clicked.connect(self.load_table)

    def load_table(self) -> None:
        self.clear()
        sender: str = self.sender().accessibleName()
        if sender == 'b_list_guru':
            tablename: str = 'stock_guru'
            stockstr: str = self.combo.currentText()
            stocklist: List[str] = stock_list_dict.get(stockstr)
            stockliststr: str = str(tuple(stocklist))
        elif sender == 'b_le_guru':
            tablename: str = 'stock_guru'
            stockstr: str = self.le.text().upper()
            stocklist: List[str] = stockstr.split()
            stockliststr: str = str(stocklist).replace('[', '(').replace(']', ')')  # for single tuple

        elif sender == 'b_list_zacks':
            tablename: str = 'usstock_z'
            stockstr: str = self.combo.currentText()
            stocklist: List[str] = stock_list_dict.get(stockstr)
            stockliststr: str = str(tuple(stocklist))
        elif sender == 'b_le_zacks':
            tablename: str = 'usstock_z'
            stockstr: str = self.le.text().upper()
            stocklist: List[str] = stockstr.split()
            stockliststr: str = str(stocklist).replace('[', '(').replace(']', ')')  # for single tuple

        elif sender == 'b_list_option':
            tablename: str = 'usstock_option'
            stockstr: str = self.combo.currentText()
            stocklist: List[str] = stock_list_dict.get(stockstr)
            stockliststr: str = str(tuple(stocklist))
        elif sender == 'b_le_option':
            tablename: str = 'usstock_option'
            stockstr: str = self.le.text().upper()
            stocklist: List[str] = stockstr.split()
            stockliststr: str = str(stocklist).replace('[', '(').replace(']', ')')  # for single tuple

        q_clause: str = '' if not stocklist else f' WHERE symbol IN {stockliststr} '  # prevent empty LineEdit
        q: str = f'SELECT * FROM {tablename} {q_clause}'
        print(q)
        df: DataFrame = execute_pandas_read(q)
        model: DataFrameModel = DataFrameModel(df)
        proxy: MySortFilterProxyModel = MySortFilterProxyModel(self)
        proxy.setSourceModel(model)
        self.pandasTv.setModel(proxy)

        grid: QGridLayout = QGridLayout()   # If the Grid was created in the view, it will get deleted
        checkboxes: List[QCheckBox] = [QCheckBox(x) for x in df.columns]
        for count, checkbox in enumerate(checkboxes):
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(partial(self.display_column, index=count))
            le1: QLineEdit = QLineEdit()
            le2: QLineEdit = QLineEdit()
            le1.textChanged.connect(lambda text, col=count: proxy.setFilterByColumn(
                QRegularExpression(text, QRegularExpression.CaseInsensitiveOption), col))
            le2.textChanged.connect(lambda text, col=count: proxy.setFilterByColumn(
                QRegularExpression(text, QRegularExpression.CaseInsensitiveOption), col))

            grid.addWidget(checkbox, count, 0)
            grid.addWidget(le1, count, 1)
            grid.addWidget(le2, count, 2)

        QWidget().setLayout(self.dockwin.layout()) # get rid of the default layout
        self.dockwin.setLayout(grid)

    def display_column(self, state: int, index: int) -> None:
        if state == Qt.Checked:
            self.pandasTv.setColumnHidden(index, False)
        else:
            self.pandasTv.setColumnHidden(index, True)


def main() -> None:
    app: QApplication = QApplication(sys.argv)
    win: CoreBrowserController = CoreBrowserController()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()