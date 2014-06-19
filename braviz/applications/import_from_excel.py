import braviz
import pandas as pd
from PyQt4 import QtGui, QtCore
from braviz.interaction.qt_guis.import_from_excel import Ui_import_from_excel
import logging
from braviz.utilities import remove_non_ascii
from braviz.interaction.qt_models import DataFrameModel
from braviz.readAndFilter import tabular_data
__author__ = 'Diego'

class ImportFromExcel(QtGui.QDialog):
    def __init__(self):
        super(ImportFromExcel,self).__init__()
        self.ui = None
        self.setup_gui()
        self.__df = None
        self.__file_name = None
        self.__model = None


    def setup_gui(self):
        self.ui = Ui_import_from_excel()
        self.ui.setupUi(self)
        self.ui.select_file_button.clicked.connect(self.get_file_name)
        self.ui.buttonBox.button(self.ui.buttonBox.Save).setEnabled(0)
        self.ui.buttonBox.button(self.ui.buttonBox.Save).clicked.connect(self.save)
        self.ui.buttonBox.button(self.ui.buttonBox.Close).clicked.connect(self.reject)


    def read_excel(self,file_name):
        df = pd.read_excel(file_name,0,index_col=0)
        columns = df.columns
        columns = map(remove_non_ascii,columns)
        df.columns = columns
        df = df.convert_objects(convert_numeric=True)
        self.__df = df
        self.__model = DataFrameModel(df,show_index=True)
        self.ui.tableView.setModel(self.__model)
        self.ui.buttonBox.button(self.ui.buttonBox.Save).setEnabled(1)


    def get_file_name(self):
        file_name = str(QtGui.QFileDialog.getOpenFileName(self,"Select excel file",
                                                          braviz.readAndFilter.braviz_auto_dynamic_data_root(),
                                                          "Excel (*.xls *.xlsx)"))
        if file_name is not None:
            self.__file_name = file_name
            self.ui.file_name_label.setText(file_name)
            self.read_excel(file_name)


    def save(self):
        self.ui.buttonBox.button(self.ui.buttonBox.Save).setEnabled(0)
        QtGui.QApplication.instance().processEvents()
        tabular_data.add_data_frame(self.__df)


def run():
    import sys
    from braviz.utilities import configure_console_logger

    # configure_logger("build_roi")
    configure_console_logger("import_from_excel")
    app = QtGui.QApplication(sys.argv)
    log = logging.getLogger(__name__)
    log.info("started")
    logging.basicConfig(level=logging.DEBUG)
    main_window = ImportFromExcel()
    main_window.show()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise


if __name__ == '__main__':
    run()