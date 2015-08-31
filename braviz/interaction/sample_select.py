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


from __future__ import division
import os
from braviz.utilities import set_pyqt_api_2

set_pyqt_api_2()

__author__ = 'Diego'

from braviz.interaction.qt_guis.new_sample_screen import Ui_NewSampleWindow
from braviz.interaction.qt_guis.add_filter_dialog import Ui_AddFilterDialog
from braviz.interaction.qt_guis.select_subsample_dialog import Ui_SelectSubsample
from braviz.interaction.qt_guis.save_sample_dialog import Ui_SaveSample
from braviz.interaction.qt_guis.load_sub_sample_dialog import Ui_LoadSampleDialog

from braviz.interaction.qt_models import SimpleSetModel, SamplesFilterModel, SamplesSelectionModel
from braviz.readAndFilter import tabular_data as braviz_tab_data
from braviz.readAndFilter import user_data as braviz_user_data
from PyQt4 import QtGui, QtCore
import braviz.interaction.qt_dialogs as braviz_dialogs
import braviz.interaction.qt_models as braviz_models
from braviz.interaction.connection import MessageClient
from braviz.utilities import launch_sub_process
from collections import deque

import numpy as np
import sys
import logging


class SampleLoadDialog(QtGui.QDialog):
    """
    This dialog gives the user the option to select a sub_sample

    Args:
        new_and_load (bool): If true buttons labeled *load* and *new* will also be shown. This buttons
            will open a :class:`SampleCreateDialog`, where the user can further customize the sample
        server_broadcast (str): Will be passed to child SampleCreateDilogs
        server_receive (str): Will be passed to child SampleCreateDilogs
    """

    def __init__(self, new__and_load=True, server_broadcast=None, server_receive=None, parent=None, parent_name=None):
        super(SampleLoadDialog, self).__init__()
        self.model = SamplesSelectionModel()
        self.ui = Ui_LoadSampleDialog()
        self.ui.setupUi(self)
        self.ui.tableView.setModel(self.model)
        self.current_sample = None
        self.current_sample_idx = None
        self.current_sample_name = None
        self.ui.tableView.activated.connect(self.load_action)
        self.ui.tableView.clicked.connect(self.load_action)
        self.refresh_list_timer = QtCore.QTimer()
        self.refresh_list_timer.timeout.connect(self.model.reload)
        self.server_bcst = server_broadcast
        self.server_rcv = server_receive
        self._parent = parent
        self._parent_name = parent_name

        # check for new subsamples each 5 seconds
        self.refresh_list_timer.start(5000)
        self.ui.buttonBox.accepted.connect(self.load_action)

        self.ui.tableView.customContextMenuRequested.connect(
            self.show_context_menu)

        if new__and_load:
            # "New" button
            self.new_button = QtGui.QPushButton("New")
            self.ui.buttonBox.addButton(
                self.new_button, QtGui.QDialogButtonBox.ActionRole)
            self.new_button.setToolTip("Define a new sub sample")

            def launch_new_sample_sub_process():
                parent = self._parent
                if server_broadcast is not None and server_receive is not None:
                    launch_sample_create_dialog(
                        server_broadcast=server_broadcast,
                        server_receive=server_receive,
                        parent_id="-1" if parent is None else str(parent),
                        parent_name="-1" if parent_name is None else parent_name
                    )
                else:
                    launch_sample_create_dialog(
                        parent_id="-1" if parent is None else str(parent),
                        parent_name="-1" if parent_name is None else parent_name
                    )
                self.new_button.setEnabled(False)
                QtCore.QTimer.singleShot(5000, lambda: self.new_button.setEnabled(True))

            self.new_button.clicked.connect(launch_new_sample_sub_process)

            # "Open" button
            self.open_button = QtGui.QPushButton("Open")
            self.ui.buttonBox.addButton(
                self.open_button, QtGui.QDialogButtonBox.ActionRole)
            self.open_button.setToolTip("Open the subsample in the subsample editor")

            def launch_open_sample_sub_process():
                if self.current_sample_idx is None:
                    return
                if server_broadcast is not None and server_receive is not None:
                    launch_sample_create_dialog(
                        sample_idx=self.current_sample_idx,
                        server_broadcast=server_broadcast,
                        server_receive=server_receive,
                        parent_id=self._parent,
                        parent_name=self._parent_name
                    )
                else:
                    launch_sample_create_dialog(
                        sample_idx=self.current_sample_idx,
                        parent_id=self._parent,
                        parent_name=self._parent_name
                    )
                self.open_button.setEnabled(False)
                QtCore.QTimer.singleShot(5000, lambda: self.open_button.setEnabled(True))

            self.open_button.clicked.connect(launch_open_sample_sub_process)

    def load_action(self, index=None):
        if index is None:
            current = self.ui.tableView.currentIndex()
        else:
            current = index
        self.current_sample = self.model.get_sample(current)
        self.current_sample_idx = self.model.get_sample_index(current)
        self.current_sample_name = self.model.get_sample_name(current)
        log = logging.getLogger(__name__)
        log.info(self.current_sample)

    def show_context_menu(self, pos):
        global_pos = self.ui.tableView.mapToGlobal(pos)
        selection = self.ui.tableView.currentIndex()
        idx = self.model.get_sample_index(selection)
        name = self.model.get_sample_name(selection)
        remove_action = QtGui.QAction("Remove %s" % name, None)
        menu = QtGui.QMenu()
        menu.addAction(remove_action)

        def remove_item():
            log = logging.getLogger(__name__)
            log.info("removing sample %s (%d)" % (name, idx))
            braviz_user_data.delete_sample(idx)
            self.model.reload()

        remove_action.triggered.connect(remove_item)
        menu.addAction(remove_action)
        menu.exec_(global_pos)


class SampleCreateDialog(QtGui.QMainWindow):
    def __init__(self, parent_pid=None, parent_name = None, server_broadcast = None, server_receive = None):
        super(SampleCreateDialog, self).__init__()

        self.message_client = MessageClient(server_broadcast, server_receive)
        self.working_model = SimpleSetModel()
        self.output_model = SimpleSetModel()
        self.filters_model = SamplesFilterModel()
        self.base_sample = []
        self.base_sample_name = None
        self.history = deque(maxlen=50)
        self.parent = parent_pid
        self.parent_name = parent_name

        self.ui = None
        self.setup_ui()

        self.set_base_sample()

    def setup_ui(self):
        self.ui = Ui_NewSampleWindow()
        self.ui.setupUi(self)
        self.ui.working_set_view.setModel(self.working_model)
        self.ui.working_set_view.customContextMenuRequested.connect(
            self.get_add_one_context_menu)
        self.ui.current_view.setModel(self.output_model)
        self.ui.current_view.customContextMenuRequested.connect(
            self.get_remove_one_context_menu)
        self.ui.add_filter_button.clicked.connect(self.show_add_filter_dialog)
        self.ui.filters.setModel(self.filters_model)
        self.ui.filters.customContextMenuRequested.connect(
            self.remove_filter_context_menu)
        self.ui.add_all_button.clicked.connect(self.add_all)
        self.ui.remove_button.clicked.connect(self.substract)
        self.ui.intersect_button.clicked.connect(self.intersect)
        self.ui.clear_button.clicked.connect(self.clear)
        self.ui.undo_button.clicked.connect(self.undo_action)
        self.ui.add_subset_button.clicked.connect(self.add_subset)
        self.ui.save_button.clicked.connect(self.show_save_dialog)
        self.ui.load_button.clicked.connect(self.show_load_sample)
        self.ui.create_ind_variable.clicked.connect(
            self.create_indicator_variable)
        if self.parent is None or server_bc is None:
            self.ui.set_in_parent.setEnabled(False)
            self.ui.set_in_parent.setToolTip("Requires a Menu to be running and being called from an application")
        if self.parent_name is not None:
            self.ui.set_in_parent.setText("Set in %s"%self.parent_name)
        self.ui.send_to_all.setEnabled(server_bc is not None)
        if server_bc is None:
            self.ui.send_to_all.setToolTip("Requires the menu to be running")
        self.ui.set_in_parent.clicked.connect(self.send_to_parent)
        self.ui.send_to_all.clicked.connect(self.send_to_all)
        self.ui.comboBox.insertSeparator(self.ui.comboBox.count())
        self.ui.comboBox.addItem("Select")
        self.ui.comboBox.activated.connect(self.change_base_sample)
        self.base_sample_name = self.ui.comboBox.itemText(0)

    def change_base_sample(self):
        new_index = self.ui.comboBox.currentIndex()
        if new_index == 0:
            self.set_base_sample(None)
        elif new_index == self.ui.comboBox.count() - 1:
            d = SampleLoadDialog(False)
            if d.exec_() and d.current_sample is not None:
                self.set_base_sample(int(d.current_sample_idx))
                self.base_sample_name = d.current_sample_name
                self.ui.comboBox.insertItem(1, self.base_sample_name)
                self.ui.comboBox.setItemData(1, int(d.current_sample_idx))
                self.ui.comboBox.setCurrentIndex(1)

            else:
                i = self.ui.comboBox.findText(self.base_sample_name)
                if i >= 0:
                    self.ui.comboBox.setCurrentIndex(i)
        else:
            sample_idx = self.ui.comboBox.itemData(new_index)
            self.set_base_sample(sample_idx)

    def change_output_sample(self, new_set):
        # to make sure it is not altered afterwards
        new_set = frozenset(new_set)
        self.history.append(self.output_model.get_elements())
        if len(self.history) > 0:
            self.ui.undo_button.setEnabled(1)
        self.output_model.set_elements(new_set)
        self.ui.size_label.setText("Size : %d" % len(new_set))

    def add_all(self):
        new_set = self.working_model.get_elements().union(
            self.output_model.get_elements())
        self.change_output_sample(new_set)

    def substract(self):
        new_set = self.output_model.get_elements(
        ) - self.working_model.get_elements()
        self.change_output_sample(new_set)

    def intersect(self):
        new_set = self.output_model.get_elements().intersection(
            self.working_model.get_elements())
        self.change_output_sample(new_set)

    def add_subset(self):
        working_set = self.working_model.get_elements()
        dialog = SubSampleSelectDialog(len(working_set))
        ret = dialog.exec_()
        if ret == dialog.Accepted:
            sub_sample = np.random.choice(
                list(working_set), dialog.subsample_size, replace=False)
            new_sample = self.output_model.get_elements().union(sub_sample)
            self.change_output_sample(set(new_sample))

    def clear(self):
        new_set = set()
        self.change_output_sample(new_set)

    def undo_action(self):
        last_set = self.history.pop()
        if len(self.history) <= 0:
            self.ui.undo_button.setEnabled(0)
        self.output_model.set_elements(last_set)

    def set_base_sample(self, sample_id=None):
        if sample_id is None:
            sample = braviz_tab_data.get_subjects()
        else:
            sample = braviz_user_data.get_sample_data(sample_id)
        self.base_sample = sample
        self.update_filters()

    def update_filters(self):
        output_sample = self.filters_model.apply_filters(self.base_sample)
        output_set = set(output_sample)
        self.working_model.set_elements(output_set)

    def show_add_filter_dialog(self):
        params = {}
        dialog = AddFilterDialog(params)
        ret = dialog.exec_()
        if ret == dialog.Accepted:
            log = logging.getLogger(__name__)
            log.debug("accepted")
            filter_name = get_filter_name(params)
            filter_func = get_filter_function(params)
            self.filters_model.add_filter(filter_name, filter_func)
            self.update_filters()

    def show_save_dialog(self):
        dialog = SaveSubSampleDialog(
            self.output_model.get_elements(), self.ui.description.toPlainText())
        ret = dialog.exec_()
        if ret == dialog.Accepted:
            log = logging.getLogger(__name__)
            log.info("saving with name %s", dialog.name)
            log.info(self.output_model.get_elements())
            log.info(dialog.description)
            self.save_sample(dialog.name, dialog.description)
            self.ui.statusbar.showMessage(
                "Succesfully saved %s" % dialog.name, 10000)

    def save_sample(self, name, description):

        braviz_user_data.save_sub_sample(
            name, self.output_model.get_elements(), description)

    def show_load_sample(self):
        dialog = SampleLoadDialog(new__and_load=False)
        res = dialog.exec_()
        if res == dialog.Accepted:
            loaded_sample = dialog.current_sample
            if loaded_sample is not None:
                self.change_output_sample(loaded_sample)

    def add_one_to_sample(self, subj):
        log = logging.getLogger(__name__)
        log.info("adding %d", subj)
        new_set = self.output_model.get_elements()
        new_set.add(subj)
        self.change_output_sample(new_set)

    def get_add_one_context_menu(self, pos):
        menu = QtGui.QMenu()
        action = QtGui.QAction("Add to sample", menu)
        menu.addAction(action)
        selection = self.ui.working_set_view.currentIndex()
        if not selection.isValid():
            return
        data = self.working_model.data(selection, QtCore.Qt.DisplayRole)

        def add_to_sample():
            self.add_one_to_sample(int(data))

        action.triggered.connect(add_to_sample)
        global_pos = self.ui.working_set_view.mapToGlobal(pos)
        menu.exec_(global_pos)

    def remove_one_from_sample(self, subj):
        log = logging.getLogger(__name__)
        log.info("removing %d", subj)
        new_set = self.output_model.get_elements()
        new_set.remove(subj)
        self.change_output_sample(new_set)

    def get_remove_one_context_menu(self, pos):
        menu = QtGui.QMenu()
        action = QtGui.QAction("Remove from sample", menu)
        menu.addAction(action)
        selection = self.ui.current_view.currentIndex()
        if not selection.isValid():
            return
        data = self.output_model.data(selection, QtCore.Qt.DisplayRole)

        def remove_from_sample():
            self.remove_one_from_sample(int(data))

        action.triggered.connect(remove_from_sample)
        global_pos = self.ui.current_view.mapToGlobal(pos)
        menu.exec_(global_pos)

    def remove_filter_context_menu(self, pos):
        menu = QtGui.QMenu()
        action = QtGui.QAction("Remove filter", menu)
        menu.addAction(action)
        selection = self.ui.filters.currentIndex()
        if not selection.isValid():
            return

        def remove_filter():
            self.filters_model.remove_filter(selection)
            self.update_filters()

        action.triggered.connect(remove_filter)
        global_pos = self.ui.filters.mapToGlobal(pos)
        menu.exec_(global_pos)

    def create_indicator_variable(self):

        dialog = braviz_dialogs.NewVariableDialog()
        dialog.ui.var_type_combo.setCurrentIndex(1)
        dialog.ui.var_type_combo.setEnabled(0)
        all_subjs = braviz_tab_data.get_subjects()
        values = {}
        sample = self.output_model.get_elements()
        for s in all_subjs:
            values[s] = 1 if s in sample else 0
        dialog.values_model.set_values_dict(values)
        dialog.override_nominal_labels({0: "Out", 1: "In"})
        dialog.exec_()

    def send_to_all(self):
        msg = {"type": "sample", "sample": list(self.output_model.get_elements())}
        self.message_client.send_message(msg)

    def send_to_parent(self):
        msg = {"type": "sample", "sample": list(self.output_model.get_elements()),
               "target": self.parent}
        self.message_client.send_message(msg)

def get_filter_name(params):
    if params["var_real"] is True:
        name = "%s %s %f" % (
            params["filter_var"], params["operation"], params["threshold"])
    else:
        checked_names = params["checked_names"]
        if len(checked_names) == 0:
            name = "%s in {}" % params["filter_var"]
        else:
            name = "%s in { %s }" % (
                params["filter_var"], ", ".join(params["checked_names"]))
    return name


def get_filter_function(params):
    if params["var_real"] is True:
        op = params["operation"]
        if op == "<":
            f = lambda x: x < float(params["threshold"])
        elif op == ">":
            f = lambda x: x > float(params["threshold"])
        else:
            f = lambda x: x == float(params["threshold"])
    else:
        f = lambda x: x in params["checked_labels"]
    # get data
    var_name = params["filter_var"]
    var_idx = braviz_tab_data.get_var_idx(var_name)

    def filter_func(subj):
        try:
            x = braviz_tab_data.get_var_value(var_idx, subj)
            x = float(x)
        except Exception:
            return False
        else:
            return f(x)

    return filter_func


class AddFilterDialog(braviz_dialogs.VariableSelectDialog):
    def __init__(self, params):
        super(AddFilterDialog, self).__init__()
        self.params_dict = params
        self.ui = None
        self.setup_ui()
        self.vars_list_model = braviz_models.VarListModel(checkeable=False)
        self.ui.tableView.setModel(self.vars_list_model)
        self.ui.tableView.activated.connect(self.update_right_side)
        self.nominal_model = braviz_models.NominalVariablesMeta(None)

        self.data = None
        self.data_vals = None
        self.jitter = None

        self.finish_ui_setup()

        # real details
        self.ui.th_spin.valueChanged.connect(
            self.update_limits_in_plot)

        # nominal details
        self.connect(self.nominal_model, QtCore.SIGNAL("DataChanged(QModelIndex,QModelIndex)"),
                     self.update_limits_in_plot)
        self.nominal_model.dataChanged.connect(self.update_limits_in_plot)

    def setup_ui(self):
        self.ui = Ui_AddFilterDialog()
        self.ui.setupUi(self)
        self.ui.select_button.clicked.connect(self.save_and_accept)
        self.ui.save_button.setText("Save Meta")
        self.ui.search_box.returnPressed.connect(self.filter_list)

    def update_right_side(self, var_name=None):
        curr_idx = self.ui.tableView.currentIndex()
        var_name = self.vars_list_model.data(curr_idx, QtCore.Qt.DisplayRole)
        self.ui.select_button.setEnabled(True)
        super(AddFilterDialog, self).update_right_side(var_name)

    def update_real_details(self):
        # print "creating real details"
        # try to read values from DB
        db_values = braviz_tab_data.get_min_max_opt_values_by_name(self.var_name)
        if db_values is None:
            self.guess_max_min()
        else:
            self.rational["min"] = db_values[0]
            self.rational["max"] = db_values[1]
            self.rational["opt"] = db_values[2]
        self.set_real_controls()

        self.ui.th_spin.setValue(self.rational["opt"])
        self.ui.th_spin.setMaximum(self.rational["max"])
        self.ui.operation_combo.currentIndexChanged.connect(
            self.update_limits_in_plot)
        self.update_plot(self.data)
        QtCore.QTimer.singleShot(20, self.update_limits_in_plot)

    def update_nominal_details(self):
        super(AddFilterDialog, self).update_nominal_details()
        self.nominal_model.set_checkeable(1)

    def update_limits_in_plot(self, *args):
        if self.ui.var_type_combo.currentIndex() != 0:
            self.matplot_widget.add_max_min_opt_lines(None, None, None)
            self.filter_plot()
            return
        mini = self.ui.minimum_val.value()
        maxi = self.ui.maximum_val.value()
        opti = self.ui.optimum_val.value()
        opti = mini + opti * (maxi - mini) / 100
        self.rational["max"] = maxi
        self.rational["min"] = mini
        self.rational["opt"] = opti
        self.matplot_widget.add_max_min_opt_lines(mini, opti, maxi)
        threshold = self.ui.th_spin.value()
        self.matplot_widget.add_threshold_line(threshold)
        self.filter_plot()

    def filter_plot(self):
        if self.ui.var_type_combo.currentIndex() != 0:
            unchecked_labels = self.nominal_model.get_unchecked()
            unchecked_indices = np.zeros((len(self.data_vals)), np.bool)
            for i, x in enumerate(self.data_vals):
                if x in unchecked_labels:
                    unchecked_indices[i] = 1
            unchecked_data = self.data_vals[unchecked_indices]
            unchecked_jitter = self.jitter[unchecked_indices]
            self.matplot_widget.add_grayed_scatter(
                unchecked_data, unchecked_jitter)
        else:
            th = self.ui.th_spin.value()
            operation = self.ui.operation_combo.currentText()
            if operation == "<":
                unselected = (self.data_vals >= th)
            elif operation == ">":
                unselected = (self.data_vals <= th)
            else:
                unselected = (self.data_vals != th)
            un_data = self.data_vals[unselected]
            un_jitter = self.jitter[unselected]
            self.matplot_widget.add_grayed_scatter(un_data, un_jitter)

    def update_plot(self, data, direct=True):
        np.random.seed(982356032)
        data2 = data.dropna()
        jitter = np.random.rand(len(data2))

        self.data = data2
        self.data_vals = np.squeeze(data2.get_values())
        # print self.data_vals.shape
        self.jitter = jitter

        self.matplot_widget.compute_scatter(data2.get_values(), jitter,
                                            x_lab=self.var_name, y_lab="jitter",
                                            urls=data2.index.get_values())

    def save_and_accept(self):
        if self.var_name is not None:
            self.save_meta_data()
        if self.params_dict is not None:
            self.params_dict["filter_var"] = self.var_name
            self.params_dict[
                "var_real"] = self.ui.var_type_combo.currentIndex() == 0
            if self.params_dict["var_real"]:
                self.params_dict[
                    "operation"] = self.ui.operation_combo.currentText()
                self.params_dict["threshold"] = self.ui.th_spin.value()
            else:
                self.params_dict[
                    "checked_labels"] = self.nominal_model.get_checked()

                def get_name(l):
                    label_name = self.nominal_model.names_dict.get(l)
                    if label_name is not None:
                        return label_name
                    return "Level %s" % l

                self.params_dict["checked_names"] = [get_name(l)
                                                     for l in self.params_dict["checked_labels"]]
        self.accept()

    def filter_list(self):
        mask = "%%%s%%" % self.ui.search_box.text()
        self.vars_list_model.update_list(mask)


class SubSampleSelectDialog(QtGui.QDialog):
    def __init__(self, original_length):
        super(SubSampleSelectDialog, self).__init__()
        self.subsample_size = 0
        dialog_ui = Ui_SelectSubsample()
        dialog_ui.setupUi(self)
        dialog_ui.spinBox.valueChanged.connect(self.update_value)
        dialog_ui.spinBox.setMaximum(original_length)
        dialog_ui.spinBox.setMinimum(0)
        self.ui = dialog_ui
        self.full_length = original_length

    def update_value(self, value):
        self.subsample_size = value
        self.ui.label_2.setText(
            "%.2f %%" % (int(value) / self.full_length * 100))


class SaveSubSampleDialog(QtGui.QDialog):
    def __init__(self, contents, description):
        super(SaveSubSampleDialog, self).__init__()
        self.ui = Ui_SaveSample()
        self.ui.setupUi(self)
        self.ui.sample_description.setPlainText(description)
        self.ui.sample_contents.setPlainText(
            ", ".join(map(str, sorted(contents))))
        self.accepted.connect(self.before_exiting)
        self.name = ""
        self.description = description

    def before_exiting(self):
        self.name = self.ui.sample_name.text()
        self.description = self.ui.sample_description.toPlainText()


def launch_sample_create_dialog(sample_idx = None, server_broadcast = None, server_receive = None, parent_id = None,
                                parent_name = None,
                                sample = None):
    args = [sys.executable, __file__, "-1" if sample_idx is None else str(sample_idx),
            "-1" if server_broadcast is None else server_broadcast, "-1" if server_receive is None else server_receive,
            "-1" if parent_id is None else str(parent_id),
            "-1" if parent_name is None else parent_name]
    if sample is not None:
        args += [str(x) for x in sample]
    launch_sub_process(args)


class SampleManager(QtCore.QObject):
    """
    Reusable component for handling sample messages and sample changes in a BRAVIZ application
    """
    sample_changed = QtCore.pyqtSignal(frozenset)

    def __init__(self,parent_application, application_name, message_client=None, initial_sample=None):
        assert isinstance(parent_application,QtGui.QWidget)
        super(SampleManager, self).__init__(parent_application)
        if initial_sample is None:
            self._sample = set()
        else:
            self._sample = set(initial_sample)

        self.__parent_name = application_name
        self._sample_policy = "ask"
        self._message_client = message_client
        self._menu_actions = {}
        self.__accept_dialog = None
        self.__last_sample = None

    @property
    def current_sample(self):
        return frozenset(self._sample)

    @current_sample.setter
    def current_sample(self, new_sample):
        self._sample = set(new_sample)
        self.sample_changed.emit(frozenset(self._sample))

    @property
    def sample_policy(self):
        return self._sample_policy

    @sample_policy.setter
    def sample_policy(self, new_policy):
        self._update_sample_policy_menu(new_policy)

    def _update_sample_policy_menu(self, new_policy):
        if new_policy in {"ask", "never", "always"}:
            self._sample_policy = new_policy
        else:
            raise ValueError("Valid sample policies are 'ask', 'always' and 'never'")

        for k, v in self._menu_actions.iteritems():
            if k == new_policy:
                v.setChecked(True)
            else:
                v.setChecked(False)

        self.sample_message_policy = new_policy

    def load_sample(self):
        s_bc = None
        s_rcv = None
        if self._message_client is not None:
            s_bc = self._message_client.server_broadcast
            s_rcv = self._message_client.server_receive

        dialog = SampleLoadDialog(
            new__and_load=True,
            server_broadcast=s_bc,
            server_receive=s_rcv,
            parent=os.getpid(),
            parent_name=self.__parent_name)
        res = dialog.exec_()
        if res == dialog.Accepted:
            new_sample = dialog.current_sample
            self.current_sample = new_sample

    def modify_sample(self):
        s_bc = None
        s_rcv = None
        if self._message_client is not None:
            s_bc = self._message_client.server_broadcast
            s_rcv = self._message_client.server_receive

        launch_sample_create_dialog(
            server_broadcast=s_bc,
            server_receive=s_rcv,
            parent_id=os.getpid(),
            sample=self.current_sample,
            parent_name = self.__parent_name
        )

    def send_sample(self):
        if self._message_client is None:
            log = logging.getLogger(__name__)
            log.warning("Can't send message, no server found")
            return
        msg = {"type": "sample", "sample": list(self._sample)}
        self._message_client.send_message(msg)

    def send_custom_sample(self, custom_sample):
        if self._message_client is None:
            log = logging.getLogger(__name__)
            log.warning("Can't send message, no server found")
            return
        msg = {"type": "sample", "sample": list(custom_sample)}
        self._message_client.send_message(msg)

    def configure_sample_policy_menu(self, parent_menu):
        assert isinstance(parent_menu, QtGui.QMenu)
        self._menu_actions["ask"] = QtGui.QAction("Ask", parent_menu)
        self._menu_actions["never"] = QtGui.QAction("Never", parent_menu)
        self._menu_actions["always"] = QtGui.QAction("Always", parent_menu)

        self._menu_actions["ask"].triggered.connect(lambda: self._update_sample_policy_menu("ask"))
        self._menu_actions["never"].triggered.connect(lambda: self._update_sample_policy_menu("never"))
        self._menu_actions["always"].triggered.connect(lambda: self._update_sample_policy_menu("always"))

        for a in self._menu_actions.itervalues():
            a.setCheckable(True)

        for k in ["ask", "never", "always"]:
            parent_menu.addAction(self._menu_actions[k])

        self._update_sample_policy_menu(self.sample_policy)

    def process_sample_message(self, msg):
        sample = msg.get("sample", tuple())
        target = msg.get("target")
        if target is not None:
            accept_now = target == os.getpid()
        else:
            accept_now = self._accept_samples(sample)
        if accept_now:
            self.current_sample = sample

    def _accept_samples(self, sample):
        if self.sample_policy == "ask":
            # The sample change is delayed until the dialog resolves
            self._show_accept_dialog(sample)
            return False
        elif self.sample_policy == "always":
            return True
        else:
            return False

    def _show_accept_dialog(self, sample):
        self.__last_sample = sample
        message = "Sample Received\nSize = %d\nAccept?"%len(sample)
        if self.__accept_dialog is None:

            self.__accept_dialog = QtGui.QMessageBox(QtGui.QMessageBox.Question,
                "Sample Received", message,
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No | QtGui.QMessageBox.YesToAll | QtGui.QMessageBox.NoToAll,
                self.parent())
            self.__accept_dialog.setDefaultButton(QtGui.QMessageBox.Yes)
            self.__accept_dialog.setWindowModality(QtCore.Qt.ApplicationModal)
            self.__accept_dialog.finished.connect(self._resolve_accept_dialog)
            self.__accept_dialog.show()
        else:
            self.__accept_dialog.setText(message)

    def _resolve_accept_dialog(self, answer):
        set_sample = None
        if answer == QtGui.QMessageBox.Yes:
            set_sample = True
        elif answer == QtGui.QMessageBox.YesToAll:
            self.sample_policy = "always"
            set_sample = True
        elif answer == QtGui.QMessageBox.No:
            set_sample = False
        elif answer == QtGui.QMessageBox.NoToAll:
            self.sample_policy = "never"
            set_sample = False
        self.__accept_dialog = None
        if set_sample:
            self.current_sample = self.__last_sample


if __name__ == "__main__":
    # args <-1|sample_idx> <-1|server_broadcast_address> <-1|server_receive_address> <-1|parent_pid> <-1|parent_name> [S0, S1, .... Sn]
    from braviz.utilities import configure_logger_from_conf
    configure_logger_from_conf("sample_creation")
    log = logging.getLogger(__name__)
    log.info(sys.argv)
    app = QtGui.QApplication([])
    parent = None
    parent_name = None
    server_bc = None
    server_rcv = None

    print(sys.argv)
    if len(sys.argv) >= 6:
            parent_name = sys.argv[5]
            if parent_name == "-1":
                parent_name = None
    if len(sys.argv) >= 5:
        try:
            parent = int(sys.argv[4])
        except ValueError:
            parent = None
        if parent < 0:
            parent = None
    if len(sys.argv) >= 4:
        server_rcv = sys.argv[3]
        server_bc = sys.argv[2]
        if ":" not in server_rcv:
            server_rcv = None
        if ":" not in server_bc:
            server_bc = None
    main_window = SampleCreateDialog(parent, parent_name, server_bc, server_rcv)
    main_window.show()
    if len(sys.argv) >= 2:
        try:
            sample_id = int(sys.argv[1])
        except ValueError:
            pass
        else:
            if sample_id > 0:
                sample = braviz_user_data.get_sample_data(sample_id)
                main_window.change_output_sample(sample)
    if len(sys.argv) > 6:
        sample = [int(x) for x in sys.argv[6:]]
        main_window.change_output_sample(sample)
    main_window.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    try:
        sys.exit(app.exec_())
    except Exception as e:
        log = logging.getLogger(__name__)
        log.exception(e)