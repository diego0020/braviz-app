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

from __future__ import print_function
from braviz.utilities import set_pyqt_api_2
set_pyqt_api_2()

import sys
import platform
import logging
import webbrowser

from PyQt4 import QtGui
from PyQt4 import QtCore
from braviz.utilities import launch_sub_process, get_instance_id
import braviz.interaction
import braviz.interaction.qt_dialogs
import braviz.interaction.sample_select
from braviz.interaction.connection import MessageServer, create_log_message
from braviz.readAndFilter import log_db

__author__ = 'Diego'

try:
    from braviz.interaction.qt_guis.menu2_light_mac import Ui_BavizMenu as Ui_BravizMenu_short
    from braviz.interaction.qt_guis.menu2_light import Ui_BavizMenu
except ImportError as e:
    import braviz.interaction.generate_qt_guis
    braviz.interaction.generate_qt_guis.update_guis()
    print(e.message)
    print("Maybe needs to update gui, please try to load again")
    _ = raw_input("press enter to quit")
    sys.exit(0)




class BravizMenu2(QtGui.QMainWindow):

    def __init__(self):
        super(BravizMenu2, self).__init__()

        self.uid = get_instance_id()
        self.reader = None
        self.ui = None
        self.setWindowTitle("Braviz Menu")
        self.messages_server = MessageServer(local_only=True)
        print("Server Started")
        print("Broadcast address: %s" % self.messages_server.broadcast_address)
        print("Receive address: %s" % self.messages_server.receive_address)
        log_db.start_session()
        self.messages_server.message_received.connect(self.receive_messages)
        args = [sys.executable, "-m", "braviz.applications.braviz_web_server", "0",
                self.messages_server.broadcast_address, self.messages_server.receive_address]
        self.web_server = launch_sub_process(args)
        args = [sys.executable, "-m", "braviz.applications.log_concentrator",
                self.messages_server.broadcast_address]
        self.log_server = launch_sub_process(args)
        self.child_pid_to_proc = dict()
        self.child_running_applications = dict()
        self.waiting_for_scenario = dict()
        self.setup_gui()

    def setup_gui(self):
        screen_heigth = QtGui.QApplication.desktop().height()
        if platform.system() != "Darwin":
            self.ui = Ui_BavizMenu()
        else:
            self.ui = Ui_BravizMenu_short()
        #self.ui = Ui_BavizMenu()
        self.ui.setupUi(self)
        self.connect_application_launcher("anova", self.ui.anova)
        self.connect_application_launcher("correlations", self.ui.correlations)
        self.connect_application_launcher("linear_model", self.ui.linear_model)
        self.connect_application_launcher(
            "logic_bundles", self.ui.logic_bundles)
        self.connect_application_launcher("build_roi", self.ui.roi_builder)
        self.connect_application_launcher(
            "sample_overview", self.ui.sample_overview)
        self.connect_application_launcher(
            "subject_overview", self.ui.subject_overview)
        self.connect_application_launcher(
            "fmri_explorer", self.ui.fmri_explorer)
        self.connect_application_launcher("measure", self.ui.measure_app)
        self.connect_application_launcher("excel", self.ui.excel)
        self.connect_application_launcher("export", self.ui.export_2)
        self.ui.parallel_coordinates.clicked.connect(self.open_parallel_coordinates)

        self.connect_application_launcher("check_reg", self.ui.check_reg)

        # self.connect_application_launcher("braviz_menu_classic",
        # self.ui.braviz_menu_classic))
        self.ui.variables.clicked.connect(
            self.launch_variable_management_dialog)
        self.ui.scenarios.clicked.connect(self.launch_scenarios_dialog)
        self.ui.samples.clicked.connect(self.launch_samples_dialog)
        self.ui.help_button.clicked.connect(self.open_help)

        import braviz.readAndFilter.config_file

        config = braviz.readAndFilter.config_file.get_config(__file__)
        project = config.get_project_name()
        self.ui.label.setText(
            "Welcome to Braviz<small><br>%s</small>" % project)

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
            self.log_action("Launched %s"%app)
            proc = launch_sub_process(args)
            pid = proc.pid
            self.child_pid_to_proc[pid] = proc
            button.setEnabled(False)
            QtCore.QTimer.singleShot(3000, restore_icon)

        button.clicked.connect(launch_app)

    def log_action(self,description):
        state = {}
        msg = create_log_message(description, state, "braviz_menu2", self.uid)
        self.messages_server.send_message(msg)

    def launch_variable_management_dialog(self):
        dialog = braviz.interaction.qt_dialogs.OutcomeSelectDialog(None)
        dialog.setWindowTitle("Variables")
        dialog.ui.select_button.setText("Done")
        self.log_action("Opened variables dialog")
        dialog.exec_()

    def launch_samples_dialog(self):
        self.log_action("Opened samples dialog")
        dialog = braviz.interaction.sample_select.SampleLoadDialog(
            new__and_load=True,
            server_broadcast=self.messages_server.broadcast_address,
            server_receive=self.messages_server.receive_address,
            parent=None
        )
        dialog.exec_()
        return

    def launch_scenarios_dialog(self):
        self.log_action("Opened scenarios dialog")
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
            args = [interpreter, "-m", "braviz.applications.%s" %
                    app, str(scn_id)]
            launch_sub_process(args)

    def open_help(self):
        self.log_action("Opened help in web browser")
        url = "http://diego0020.github.io/braviz"
        webbrowser.open(url, 2)

    def open_parallel_coordinates(self):
        self.log_action("Opened parallel coordinates in web browser")
        port = braviz.readAndFilter.config_file.get_apps_config().get("Braviz","server_port")
        url = "http://localhost:{}/parallel".format(port)
        webbrowser.open(url, 2)

    def receive_messages(self, msg):
        # for testing
        print("RECEIVED: %s" % msg)
        if msg["type"] == "ready":
            self.handle_ready_message(msg)
        elif msg["type"] == "reload":
            self.handle_reload_message(msg)


    def handle_reload_message(self, msg):
        target = msg["target"]
        # Check if target is open
        proc = self.child_running_applications.get(target)
        if proc is not None:
            # maybe running
            status = proc.poll()
            if status is None:
                # still running
                return
            # Application has ended
            del self.child_running_applications[target]

        scenario = msg["scenario"]
        scenario_meta = scenario["meta"]
        application_script = scenario_meta["application"]
        args = [sys.executable, "-m", "braviz.applications.%s"%application_script,
                "0", self.messages_server.broadcast_address, self.messages_server.receive_address]
        self.log_action("Restoring session of %s"%application_script)

        new_proc = launch_sub_process(args)
        new_pid = new_proc.pid
        self.child_pid_to_proc[new_pid]=new_proc
        self.waiting_for_scenario[new_pid]=scenario

    def handle_ready_message(self,msg):
        app_pid = msg["source_pid"]
        app_uid = msg["source_id"]
        proc = self.child_pid_to_proc[app_pid]
        self.child_running_applications[app_uid] = proc
        maybe_scn = self.waiting_for_scenario.get(app_pid)
        if maybe_scn is not None:
            crafted_message = {
                "type" : "reload",
                "target" : app_uid,
                "scenario" : maybe_scn
            }
            self.messages_server.send_message(crafted_message)

    def toggle_connection(self, on):
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
    check_db.verify_log_db()

    app = QtGui.QApplication(sys.argv)

    main_window = BravizMenu2()
    main_window.show()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise
    # kill web server
    log.info("Terminating web server")
    main_window.web_server.terminate()

    # kill log server
    log.info("Terminating log server")
    main_window.log_server.terminate()

if __name__ == '__main__':
    import traceback
    import braviz.interaction.generate_qt_guis

    braviz.interaction.generate_qt_guis.update_guis()
    try:
        run()
    except Exception as e:
        print("ERROR")
        traceback.print_exc()
    _ = raw_input("Press enter to close window")
