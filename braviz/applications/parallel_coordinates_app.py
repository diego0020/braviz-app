from __future__ import division


import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore


from braviz.interaction.qt_guis.parallel_coordinates import Ui_parallel_coordinates
from braviz.interaction.qt_models import VarListModel
from braviz.interaction.qt_dialogs import SelectOneVariableWithFilter

from braviz.readAndFilter.tabular_data import get_connection, get_data_frame_by_name
import braviz.readAndFilter.tabular_data as braviz_tab_data
import subprocess
import sys

import logging

__author__ = 'da.angulo39'

class ParallelCoordinatesApp(QtGui.QMainWindow):
    def __init__(self):
        super(ParallelCoordinatesApp, self).__init__()
        self.ui = None
        self.url="http://127.0.0.1:8100/?vars=2014,1002,1003,1004,1005"

        self.cathegorical_var=2014
        self.attributes=[1002,1003,1004,1005]
        self.vars_model = VarListModel(checkeable=True)
        self.vars_model.select_items(self.attributes)

        self.generate_url()
        self.setup_ui()



    def setup_ui(self):
        self.ui = Ui_parallel_coordinates()
        self.ui.setupUi(self)

        self.ui.vars_list.setModel(self.vars_model)
        self.vars_model.CheckedChanged.connect(self.vars_changed)
        self.ui.search_box.returnPressed.connect(self.filter_list)

        self.ui.cathegory_combo.addItem(braviz_tab_data.get_var_name(self.cathegorical_var))
        self.ui.cathegory_combo.insertSeparator(self.ui.cathegory_combo.count())
        self.ui.cathegory_combo.addItem("<Select cathegory>")
        self.ui.cathegory_combo.activated.connect(self.change_cathegory)
        self.ui.cathegory_combo.setCurrentIndex(0)
        self.ui.webView.loadFinished.connect(self.start_web_server)

        self.refresh_web_view()


    def refresh_web_view(self):
        self.ui.webView.load(QtCore.QUrl(self.url))
        link = 'open in web browser: <a href="%s">%s</a>'%(self.url,self.url)
        self.ui.url_label.setText(link)

    def generate_url(self):
        all_vars=[self.cathegorical_var]+self.attributes
        str_vars = ",".join(map(str,all_vars))
        url = "http://127.0.0.1:8100/?vars=%s"%str_vars
        self.url=url
        return url

    def vars_changed(self):
        self.attributes = [braviz_tab_data.get_var_idx(v) for v in self.vars_model.checked_set]
        self.generate_url()
        self.refresh_web_view()

    def filter_list(self):
        mask = "%%%s%%"%self.ui.search_box.text()
        self.vars_model.update_list(mask)

    def resizeEvent(self, *args, **kwargs):
        #super(ParallelCoordinatesApp,self).resizeEvent(*args,**kwargs)
        self.refresh_web_view()

    def change_cathegory(self):
        if self.ui.cathegory_combo.currentIndex() == self.ui.cathegory_combo.count() - 1:
            #print "dispatching dialog"
            params = {}
            dialog = SelectOneVariableWithFilter(params,accept_real=False,accept_nominal=True)
            selection = dialog.exec_()
            logger = logging.getLogger(__name__)
            logger.info("Cathegories selection %s",params)
            if selection > 0:
                var = params["selected_outcome"]
                self.ui.cathegory_combo.insertItem(0,var)
                self.ui.cathegory_combo.setCurrentIndex(0)
            else:
                return
        else:
            var = self.ui.cathegory_combo.itemText(self.ui.cathegory_combo.currentIndex())
        print var
        self.cathegorical_var=braviz_tab_data.get_var_idx(var)
        self.generate_url()
        self.refresh_web_view()

    def start_web_server(self,ok):
        #test if already started
        if not ok:
            interpreter = sys.executable
            args = [interpreter,"-m","braviz.applications.braviz_web_server"]
            subprocess.Popen(args)
            QtCore.QTimer.singleShot(2000,self.refresh_web_view)

if __name__ == "__main__":
    app = QtGui.QApplication([])
    main_window = ParallelCoordinatesApp()
    main_window.show()
    app.exec_()