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

__author__ = 'Diego'

from braviz.interaction.qt_guis.new_sample_screen import Ui_NewSampleWindow
from braviz.interaction.qt_guis.add_filter_dialog import Ui_AddFilterDialog
from braviz.interaction.qt_guis.rational_details_frame_filtering import Ui_rational_details
from braviz.interaction.qt_guis.select_subsample_dialog import Ui_SelectSubsample
from braviz.interaction.qt_guis.save_sample_dialog import Ui_SaveSample
from braviz.interaction.qt_guis.load_sub_sample_dialog import Ui_LoadSampleDialog

from braviz.interaction.qt_models import SimpleSetModel, SamplesFilterModel, SamplesSelectionModel
from braviz.readAndFilter import tabular_data as braviz_tab_data
from braviz.readAndFilter import user_data as braviz_user_data
from PyQt4 import QtGui, QtCore
from braviz.interaction.qt_dialogs import VariableSelectDialog, NewVariableDialog
import braviz.interaction.qt_models as braviz_models
import subprocess

import numpy as np
import sys
import logging


class SampleLoadDialog(QtGui.QDialog):

    def __init__(self, new_button=True):
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
        self.ui.tableView.customContextMenuRequested.connect(
            self.show_context_menu)
        if new_button:
            self.new_button = QtGui.QPushButton("New")
            self.ui.buttonBox.addButton(
                self.new_button, QtGui.QDialogButtonBox.ActionRole)
            self.new_sample_app = None
            self.check_state_timer = None
            self.ui.buttonBox.accepted.connect(self.load_action)

            def refresh_list_and_re_enamble_new():
                return_value = self.new_sample_app.poll()
                if return_value is not None:
                    self.new_button.setEnabled(1)
                    self.model.reload()
                    self.check_state_timer.stop()

            def launch_new_sample_sub_process():
                self.new_button.setEnabled(0)
                executable = sys.executable
                self.new_sample_app = subprocess.Popen([executable, __file__])
                self.check_state_timer = QtCore.QTimer(self)
                self.check_state_timer.timeout.connect(
                    refresh_list_and_re_enamble_new)
                self.check_state_timer.start(1000)

            self.new_button.clicked.connect(launch_new_sample_sub_process)

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


class SampleCreateDilog(QtGui.QMainWindow):

    def __init__(self):
        super(SampleCreateDilog, self).__init__()

        self.working_model = SimpleSetModel()
        self.output_model = SimpleSetModel()
        self.filters_model = SamplesFilterModel()
        self.base_sample = []
        self.base_sample_name = None
        self.history = []

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
                self.set_base_sample(d.current_sample_idx)
                self.base_sample_name = d.current_sample_name
                self.ui.comboBox.insertItem(1, self.base_sample_name)
                self.ui.comboBox.setItemData(1, int(d.current_sample_idx))
                self.ui.comboBox.setCurrentIndex(1)

            else:
                i = self.ui.comboBox.findText(self.base_sample_name)
                if i >= 0:
                    self.ui.comboBox.setCurrentIndex(i)
        else:
            sample_idx = self.ui.comboBox.itemData(new_index).toInt()[0]
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
        dialog = SampleLoadDialog(new_button=False)
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

        dialog = NewVariableDialog()
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


class AddFilterDialog(VariableSelectDialog):

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

        #real details
        self.ui.th_spin.valueChanged.connect(
            self.update_limits_in_plot)

        #nominal details
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


if __name__ == "__main__":
    from braviz.utilities import configure_logger_from_conf

    configure_logger_from_conf("sample_creation")
    app = QtGui.QApplication([])
    main_window = SampleCreateDilog()
    main_window.show()
    if len(sys.argv) >= 2:
        sample_id = int(sys.argv[1])
        sample = braviz_user_data.get_sample_data(sample_id)
        main_window.change_output_sample(sample)
    main_window.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    try:
        sys.exit(app.exec_())
    except Exception as e:
        log = logging.getLogger(__name__)
        log.exception(e)
