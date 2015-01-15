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
from braviz.interaction.qt_dialogs import GenericVariableSelectDialog
from PyQt4 import QtGui, QtCore
import logging
from braviz.readAndFilter import tabular_data
__author__ = 'Diego'

class ExportVariables(GenericVariableSelectDialog):
    def __init__(self):
        params = {}
        super(ExportVariables,self).__init__(params,multiple=True)
        self.ui.select_button.setText("Export Selected")

    def select_and_return(self, *args):
        file_name = str(QtGui.QFileDialog.getSaveFileName(self,"Create output file",
                                                          braviz.readAndFilter.braviz_auto_dynamic_data_root(),
                                                          "Comma Separated (*.csv)"))
        if file_name is not None:
            selected_names = self.vars_list_model.checked_set
            df = tabular_data.get_data_frame_by_name(selected_names)
            df.to_csv(file_name)



    def save(self):
        self.ui.buttonBox.button(self.ui.buttonBox.Save).setEnabled(0)
        QtGui.QApplication.instance().processEvents()
        tabular_data.add_data_frame(self.__df2)


def run():
    import sys
    from braviz.utilities import configure_logger_from_conf

    # configure_logger("build_roi")
    configure_logger_from_conf("export_data")
    app = QtGui.QApplication(sys.argv)
    log = logging.getLogger(__name__)
    log.info("started")
    logging.basicConfig(level=logging.DEBUG)
    main_window = ExportVariables()
    main_window.show()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise


if __name__ == '__main__':
    run()
