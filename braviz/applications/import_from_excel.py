##############################################################################
#    Braviz, Brain Data interactive visualization                            #
#    Copyright (C) 2014  Diego Angulo                                        #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU Lesser General Public License as          #
#    published by  the Free Software Foundation, either version 3 of the     #
#    License, or (at your option) any later version.                         #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU Lesser General Public License for more details.                     #
#                                                                            #
#    You should have received a copy of the GNU Lesser General Public License#
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.   #
##############################################################################


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
        self.__df2 = None
        self.__file_name = None
        self.__model = None


    def setup_gui(self):
        self.ui = Ui_import_from_excel()
        self.ui.setupUi(self)
        self.ui.select_file_button.clicked.connect(self.get_file_name)
        self.ui.buttonBox.button(self.ui.buttonBox.Save).setEnabled(0)
        self.ui.buttonBox.button(self.ui.buttonBox.Save).clicked.connect(self.save)
        self.ui.buttonBox.button(self.ui.buttonBox.Close).clicked.connect(self.reject)
        self.ui.omitExistent.clicked.connect(self.update_model)

    def update_model(self):
        if self.__df is None:
            return
        cols = self.__df.columns
        if self.ui.omitExistent.isChecked():
            cols2 = filter(lambda x: not tabular_data.does_variable_name_exists(x),cols)
            df = self.__df[cols2]
        else:
            cols2 = [mingle_name(n) for n in cols]
            df = self.__df.copy()
            df.columns = cols2
        self.__model = DataFrameModel(df, index_as_column=False)
        self.ui.tableView.setModel(self.__model)
        self.ui.buttonBox.button(self.ui.buttonBox.Save).setEnabled(1)
        self.__df2 = df


    def read_excel(self,file_name):
        df = pd.read_excel(file_name,0,index_col=0,na_values=["#NULL!"])
        columns = df.columns
        columns = map(remove_non_ascii,columns)
        df.columns = columns
        df = df.convert_objects(convert_numeric=True)

        self.__df = df



    def get_file_name(self):
        file_name = str(QtGui.QFileDialog.getOpenFileName(self,"Select excel file",
                                                          braviz.readAndFilter.braviz_auto_dynamic_data_root(),
                                                          "Excel (*.xls *.xlsx)"))
        if file_name is not None:
            self.__file_name = file_name
            self.ui.file_name_label.setText(file_name)
            self.read_excel(file_name)
            self.update_model()


    def save(self):
        self.ui.buttonBox.button(self.ui.buttonBox.Save).setEnabled(0)
        QtGui.QApplication.instance().processEvents()
        tabular_data.add_data_frame(self.__df2)

def mingle_name(n):
    if tabular_data.does_variable_name_exists(n):
        n += "2"
        return mingle_name(n)
    return n

def run():
    import sys
    from braviz.utilities import configure_logger_from_conf

    # configure_logger("build_roi")
    configure_logger_from_conf("import_from_excel")
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
