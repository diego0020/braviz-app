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


from __future__ import division, print_function
from braviz.utilities import set_pyqt_api_2
set_pyqt_api_2()


import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

from braviz.interaction.qt_guis.parallel_coordinates import Ui_parallel_coordinates
from braviz.interaction.qt_models import VarListModel
from braviz.interaction.qt_dialogs import SelectOneVariableWithFilter
from braviz.applications.sample_select import SampleLoadDialog
from braviz.readAndFilter.config_file import get_config

import braviz.readAndFilter.tabular_data as braviz_tab_data
from braviz.utilities import launch_sub_process

import logging

__author__ = 'da.angulo39'


class ParallelCoordinatesApp(QtGui.QMainWindow):

    def __init__(self, scenario, broadcast, receive):

        super(ParallelCoordinatesApp, self).__init__()
        self.ui = None
        self.url = None
        self.broadcast = broadcast
        self.receive = receive

        config = get_config(__file__)
        def_vars = config.get_default_variables()
        def_var_codes = map(def_vars.get, ("nom2", "ratio1", "ratio2"))
        def_var_codes = map(braviz_tab_data.get_var_idx, def_var_codes)
        def_var_codes = filter(lambda x: x is not None, def_var_codes)
        self.cathegorical_var = braviz_tab_data.get_var_idx(def_vars["nom1"])

        self.attributes = def_var_codes
        self.sample_id = None
        self.vars_model = VarListModel(checkeable=True)
        self.vars_model.select_items(self.attributes)
        self.server_process = None

        self.generate_url()
        self.setup_ui()

    def setup_ui(self):
        self.ui = Ui_parallel_coordinates()
        self.ui.setupUi(self)

        self.ui.vars_list.setModel(self.vars_model)
        self.vars_model.CheckedChanged.connect(self.vars_changed)
        self.ui.search_box.returnPressed.connect(self.filter_list)

        self.ui.cathegory_combo.addItem(
            braviz_tab_data.get_var_name(self.cathegorical_var))
        self.ui.cathegory_combo.insertSeparator(
            self.ui.cathegory_combo.count())
        self.ui.cathegory_combo.addItem("<Select cathegory>")
        self.ui.cathegory_combo.activated.connect(self.change_cathegory)
        self.ui.cathegory_combo.setCurrentIndex(0)
        self.ui.webView.loadFinished.connect(self.start_web_server)
        self.ui.actionSelect_Sample.triggered.connect(self.set_sample)
        self.ui.clear_button.clicked.connect(self.clear_selection)

        web_view = self.ui.webView
        set=web_view.settings()
        set.setAttribute(set.DeveloperExtrasEnabled,True)

        self.refresh_web_view()

    def refresh_web_view(self):
        self.ui.webView.load(QtCore.QUrl(self.url))
        link = 'open in web browser: <a href="%s">%s</a>' % (
            self.url, self.url)
        self.ui.url_label.setText(link)

    def generate_url(self):
        all_vars = [self.cathegorical_var] + self.attributes
        str_vars = ",".join(map(str, all_vars))
        url = "http://127.0.0.1:8100/parallel?vars=%s" % str_vars
        if self.sample_id is not None:
            url += "&sample=%s" % self.sample_id
        self.url = url
        return url

    def vars_changed(self):
        self.attributes = [
            braviz_tab_data.get_var_idx(v) for v in sorted(self.vars_model.checked_set)]
        self.generate_url()
        self.refresh_web_view()

    def filter_list(self):
        mask = "%%%s%%" % self.ui.search_box.text()
        self.vars_model.update_list(mask)

    def resizeEvent(self, *args, **kwargs):
        # super(ParallelCoordinatesApp,self).resizeEvent(*args,**kwargs)
        self.refresh_web_view()

    def change_cathegory(self):
        if self.ui.cathegory_combo.currentIndex() == self.ui.cathegory_combo.count() - 1:
            # print "dispatching dialog"
            params = {}
            dialog = SelectOneVariableWithFilter(
                params, accept_real=False, accept_nominal=True)
            selection = dialog.exec_()
            logger = logging.getLogger(__name__)
            logger.info("Cathegories selection %s", params)
            if selection > 0:
                var = params["selected_outcome"]
                self.ui.cathegory_combo.insertItem(0, var)
                self.ui.cathegory_combo.setCurrentIndex(0)
            else:
                return
        else:
            var = self.ui.cathegory_combo.itemText(
                self.ui.cathegory_combo.currentIndex())
        self.cathegorical_var = braviz_tab_data.get_var_idx(var)
        self.generate_url()
        self.refresh_web_view()

    def start_web_server(self, ok):
        # test if already started
        if not ok:
            if self.server_process is None:
                interpreter = sys.executable
                if self.broadcast is not None and self.receive is not None:
                    args = [interpreter, "-m", "braviz.applications.braviz_web_server",
                            "0", self.broadcast, self.receive]
                else:
                    args = [
                        interpreter, "-m", "braviz.applications.braviz_web_server"]
                launch_sub_process(args)
            else:
                ret = self.server_process.poll()
                if ret is not None:
                    log=logging.getLogger(__name__)
                    log.warning("server has died, restarting")
                    self.server_process = None
            QtCore.QTimer.singleShot(2000, self.refresh_web_view)

    def set_sample(self):
        dialog = SampleLoadDialog()
        res = dialog.exec_()
        if res == dialog.Accepted:
            new_sample = dialog.current_sample_idx
            self.sample_id = new_sample
        self.generate_url()
        self.refresh_web_view()

    def clear_selection(self):
        self.vars_model.clear_selection()


if __name__ == "__main__":
    import sys

    scenario = None
    broadcast = None
    receive = None
    if len(sys.argv) > 1:
        scenario = sys.argv[1]
    if len(sys.argv) > 3:
        broadcast = sys.argv[2]
        receive = sys.argv[3]

    app = QtGui.QApplication([])
    main_window = ParallelCoordinatesApp(scenario, broadcast, receive)
    main_window.show()
    app.exec_()
    if main_window.server_process is not None:
        log = logging.getLogger(__name__)
        log.info("terminating server")
        main_window.server_process.terminate()
