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


__author__ = 'Diego'

import subprocess
import sys
import logging

from PyQt4 import QtGui
from PyQt4 import QtCore


try:
    from braviz.interaction.qt_guis.menu2_light import Ui_BavizMenu
    import braviz.interaction.qt_dialogs
    import braviz.applications.qt_sample_select_dialog
except ImportError as e:
    import braviz.interaction.generate_qt_guis

    braviz.interaction.generate_qt_guis.update_guis()
    print e.message
    print "Maybe needs to update gui, please try to load again"
    dummy_in = raw_input("press enter to quit")


class BravizMenu2(QtGui.QMainWindow):
    def __init__(self):
        super(BravizMenu2, self).__init__()
        from braviz.interaction.connection import MessageServer

        self.reader = None

        self.ui = None
        self.setWindowTitle("Braviz Menu")
        self.messages_server = MessageServer(local_only=True)
        print "Server Started"
        print "Broadcast address: %s" % self.messages_server.broadcast_address
        print "Receive address: %s" % self.messages_server.receive_address

        self.messages_server.message_received.connect(self.print_messages)
        self.setup_gui()

    def setup_gui(self):
        self.ui = Ui_BavizMenu()
        self.ui.setupUi(self)
        self.connect_application_launcher("anova", self.ui.anova)
        self.connect_application_launcher("correlations", self.ui.correlations)
        self.connect_application_launcher("linear_model", self.ui.linear_model)
        self.connect_application_launcher("logic_bundles", self.ui.logic_bundles)
        self.connect_application_launcher("build_roi", self.ui.roi_builder)
        self.connect_application_launcher("sample_overview", self.ui.sample_overview)
        self.connect_application_launcher("subject_overview", self.ui.subject_overview)
        self.connect_application_launcher("fmri_explorer", self.ui.fmri_explorer)
        self.connect_application_launcher("measure", self.ui.measure_app)
        self.connect_application_launcher("excel", self.ui.excel)
        self.connect_application_launcher("export", self.ui.export_2)
        self.connect_application_launcher("parallel_coordinates", self.ui.parallel_coordinates)
        self.connect_application_launcher("check_reg", self.ui.check_reg)

        # self.connect_application_launcher("braviz_menu_classic", self.ui.braviz_menu_classic))
        self.ui.variables.clicked.connect(self.launch_variable_management_dialog)
        self.ui.scenarios.clicked.connect(self.launch_scenarios_dialog)
        self.ui.samples.clicked.connect(self.launch_samples_dialog)
        self.ui.help_button.clicked.connect(self.open_help)

        import braviz.readAndFilter.config_file

        config = braviz.readAndFilter.config_file.get_config(__file__)
        project = config.get_project_name()
        self.ui.label.setText("Welcome to Braviz<small><br><br>%s</small>" % project)

        self.ui.network_button.toggled.connect(self.toggle_connection)


    __applications = {
        "subject_overview": "subject_overview",
        "sample_overview": "sample_overview",
        "anova": "anova_task",
        "braviz_menu_classic": "braviz_menu",
        "correlations": "correlations",
        "linear_model": "lm_task",
        "logic_bundles": "logic_bundles",
        "build_roi": "build_roi",
        "excel": "import_from_excel",
        "export": "export_vars",
        "fmri_explorer": "fmri_explorer",
        "measure": "measure_task",
        "parallel_coordinates": "parallel_coordinates_app",
        "check_reg": "check_reg_app"
    }

    def connect_application_launcher(self, app, button):
        interpreter = sys.executable
        module = self.__applications[app]
        # python -m <module> scenario=0 <broadcast_address> <receive_address>
        args = [interpreter, "-m", "braviz.applications.%s" % module, "0",
                self.messages_server.broadcast_address, self.messages_server.receive_address]

        def restore_icon():
            button.setEnabled(True)

        def launch_app():
            subprocess.Popen(args)
            button.setEnabled(False)
            QtCore.QTimer.singleShot(3000, restore_icon)

        button.clicked.connect(launch_app)


    def launch_variable_management_dialog(self):
        dialog = braviz.interaction.qt_dialogs.OutcomeSelectDialog(None)
        dialog.setWindowTitle("Variables")
        dialog.ui.select_button.setText("Done")
        dialog.exec_()

    def launch_samples_dialog(self):
        dialog = braviz.applications.qt_sample_select_dialog.SampleLoadDialog()
        ret = dialog.exec_()
        if ret == dialog.Accepted:
            idx = dialog.current_sample_idx
            interpreter = sys.executable
            args = [interpreter, "-m", "braviz.applications.qt_sample_select_dialog", str(idx)]
            subprocess.Popen(args)

    def launch_scenarios_dialog(self):
        if self.reader is None:
            self.reader = braviz.readAndFilter.BravizAutoReader()
        params = {}
        dialog = braviz.interaction.qt_dialogs.LoadScenarioDialog(None, params)
        ret = dialog.exec_()
        if ret == QtGui.QDialog.Accepted and "meta" in params:
            log = logging.getLogger(__name__)
            log.info(params)
            app = params["meta"]["application"]
            scn_id = params["meta"]["scn_id"]
            interpreter = sys.executable
            args = [interpreter, "-m", "braviz.applications.%s" % app, str(scn_id)]
            subprocess.Popen(args)

    def open_help(self):
        import webbrowser

        url = "http://diego0020.github.io/braviz"
        webbrowser.open(url, 2)

    def print_messages(self, msg):
        # for testing
        print "RECEIVED: %s" % msg

    def toggle_connection(self,on):
        if on:
            self.messages_server.pause = False
        else:
            self.messages_server.pause = True

def run():
    import sys
    from braviz.utilities import configure_logger_from_conf
    from braviz.readAndFilter import check_db

    configure_logger_from_conf("menu2")
    log = logging.getLogger(__name__)

    # verify database
    check_db.verify_db_completeness()

    app = QtGui.QApplication(sys.argv)
    main_window = BravizMenu2()
    main_window.show()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise


if __name__ == '__main__':
    import traceback
    import braviz.interaction.generate_qt_guis

    braviz.interaction.generate_qt_guis.update_guis()
    try:
        run()
    except Exception as e:
        print "ERROR"
        traceback.print_exc()

    dummy_input = raw_input("Press enter to close window")
