from __future__ import division

import itertools
import cPickle
import logging

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import numpy as np

from braviz.interaction.qt_widgets import MatplotWidget


try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

import braviz
from braviz.interaction.qt_guis.outcome_select import Ui_SelectOutcomeDialog
from braviz.interaction.qt_guis.outcome_select_multi_plot import Ui_SelectOutcomeMPDialog
from braviz.interaction.qt_guis.nominal_details_frame import Ui_nominal_details_frame
from braviz.interaction.qt_guis.rational_details_frame import Ui_rational_details
from braviz.interaction.qt_guis.regressors_select import Ui_AddRegressorDialog
from braviz.interaction.qt_guis.interactions_dialog import Ui_InteractionsDiealog
from braviz.interaction.qt_guis.context_variables_select import Ui_ContextVariablesDialog
from braviz.interaction.qt_guis.new_variable_dialog import Ui_NewVariableDialog
from braviz.interaction.qt_guis.load_bundles_dialog import Ui_LoadBundles
from braviz.interaction.qt_guis.save_fibers_bundle import Ui_SaveBundleDialog
from braviz.interaction.qt_guis.save_logic_fibers_bundle import Ui_SaveLogicBundleDialog
from braviz.interaction.qt_guis.save_scenario_dialog import Ui_SaveScenarioDialog
from braviz.interaction.qt_guis.load_scenario_dialog import Ui_LoadScenarioDialog
from braviz.interaction.qt_guis.load_logic_bundle import Ui_LoadLogicDialog

from braviz.interaction.logic_bundle_model import LogicBundleNode,LogicBundleQtTree

import braviz.interaction.qt_models as braviz_models
from braviz.readAndFilter.tabular_data import get_data_frame_by_name, get_var_idx, get_var_name, \
    is_variable_nominal, get_labels_dict, get_data_frame_by_index, get_maximum_value, get_min_max_values_by_name, \
    get_min_max_values, is_variable_name_real, get_var_description_by_name, save_is_real_by_name, \
    save_real_meta_by_name, save_var_description_by_name, get_min_max_opt_values_by_name, register_new_variable,\
    save_real_meta, save_var_description

import braviz.readAndFilter.tabular_data as braviz_tab_data

from braviz.readAndFilter import bundles_db
import braviz.readAndFilter.user_data as braviz_user_data
import os

from itertools import izip

import seaborn as sns
__author__ = 'Diego'

class VariableSelectDialog(QtGui.QDialog):
    """Implement common features for Oucome and Regressor Dialogs"""

    def __init__(self,sample = None):
        """remember to call finish_ui_setup() after setting up ui"""
        super(VariableSelectDialog, self).__init__()
        self.var_name = None
        self.details_ui = None
        self.rational = {}
        self.matplot_widget = None
        self.data = tuple()
        self.nominal_model = None
        if sample is None:
            self.sample = braviz_tab_data.get_subjects()
        else:
            self.sample = sorted(map(int,sample))
            log = logging.getLogger(__name__)
            log.info("got custom sample")
            log.info(self.sample)


    def update_plot(self, data):
        pass

    def update_right_side(self, var_name):
        try:
            self.ui.var_name.setText(var_name)
        except TypeError:
            #if nothing is selected
            return
        self.ui.save_button.setEnabled(True)
        self.ui.var_type_combo.setEnabled(True)
        is_real = is_variable_name_real(var_name)
        self.var_name = var_name
        data = get_data_frame_by_name(self.var_name)
        data.dropna(inplace=True)
        self.data = data.loc[self.sample]
        #update scatter
        self.update_plot(self.data)
        var_description = get_var_description_by_name(var_name)
        self.ui.var_description.setPlainText(var_description)
        self.ui.var_description.setEnabled(True)

        #update gui
        if is_real:
            self.ui.var_type_combo.setCurrentIndex(0)
            self.update_details(0)
        else:
            self.ui.var_type_combo.setCurrentIndex(1)
            self.update_details(1)

    def update_details(self, index):
        #is_real=self.ui.var_type_combo.currentIndex()
        #print index
        #print "===="
        self.clear_details_frame()
        if index == 0:
            QtCore.QTimer.singleShot(0, self.create_real_details)
        else:
            QtCore.QTimer.singleShot(0, self.create_nominal_details)

    def clear_details_frame(self, layout=None):
        if layout is None:
            layout = self.ui.details_frame.layout()
        if layout is None:
            return
        for i in reversed(xrange(layout.count())):
            item = layout.takeAt(i)
            if isinstance(item, QtGui.QWidgetItem):
                item.widget().deleteLater()
            elif isinstance(item, QtGui.QSpacerItem):
                pass
            else:
                self.clearLayout(item.layout())

        layout.deleteLater()

    def guess_max_min(self):
        data = self.data
        mini = data.min()[0]
        maxi = data.max(skipna=True)[0]
        medi = data.median()[0]
        self.rational["max"] = maxi
        self.rational["min"] = mini
        self.rational["opt"] = medi

    def set_real_controls(self):
        maxi = self.rational["max"]
        mini = self.rational["min"]
        medi = self.rational["opt"]
        self.details_ui.maximum_val.setValue(maxi)
        self.details_ui.minimum_val.setValue(mini)
        self.details_ui.minimum_val.setMinimum(min(mini*10,-100))
        self.details_ui.maximum_val.setMinimum(min(mini*10,-100))

        self.details_ui.minimum_val.setMaximum(max(maxi*10,1000))
        self.details_ui.maximum_val.setMaximum(max(maxi*10,1000))
        try:
            self.details_ui.optimum_val.setValue(int((medi - mini) / (maxi - mini)*100))
        except Exception:
            self.details_ui.optimum_val.setValue(0)
        self.update_optimum_real_value()

    def update_optimum_real_value(self, perc_value=None):
        if perc_value is None:
            perc_value = self.details_ui.optimum_val.value()
        real_value = perc_value / 100 * (self.rational["max"] - self.rational["min"]) + self.rational["min"]
        self.details_ui.optimum_real_value.setNum(real_value)

    def create_real_details(self):
        log = logging.getLogger(__name__)
        log.info("creating real details")
        details_ui = Ui_rational_details()
        details_ui.setupUi(self.ui.details_frame)
        self.details_ui = details_ui
        self.details_ui.optimum_val.valueChanged.connect(self.update_optimum_real_value)
        #try to read values from DB
        db_values = get_min_max_opt_values_by_name(self.var_name)
        if db_values is None:
            self.guess_max_min()
        else:
            self.rational["min"] = db_values[0]
            self.rational["max"] = db_values[1]
            self.rational["opt"] = db_values[2]
        self.set_real_controls()
        self.details_ui.optimum_val.valueChanged.connect(self.update_limits_in_plot)
        self.details_ui.minimum_val.valueChanged.connect(self.update_limits_in_plot)
        self.details_ui.maximum_val.valueChanged.connect(self.update_limits_in_plot)
        QtCore.QTimer.singleShot(0, self.update_limits_in_plot)

    def create_nominal_details(self):
        var_name = self.var_name
        log = logging.getLogger(__name__)
        log.info("creating nominal details")
        if self.nominal_model is None:
            self.nominal_model = braviz_models.NominalVariablesMeta(var_name)
        else:
            self.nominal_model.update_model(var_name)
        details_ui = Ui_nominal_details_frame()
        details_ui.setupUi(self.ui.details_frame)
        details_ui.labels_names_table.setModel(self.nominal_model)
        self.details_ui = details_ui
        QtCore.QTimer.singleShot(0, self.update_limits_in_plot)

    def finish_ui_setup(self):
        target = self.ui.plot_frame
        layout = QtGui.QVBoxLayout()
        self.matplot_widget = MatplotWidget(initial_message="Double click on variables\nto see plots")
        layout.addWidget(self.matplot_widget)
        target.setLayout(layout)
        self.ui.save_button.clicked.connect(self.save_meta_data)
        self.ui.var_type_combo.currentIndexChanged.connect(self.update_details)
        self.matplot_widget.scatter_pick_signal.connect(self.show_plot_tooltip)
        self.ui.tableView.customContextMenuRequested.connect(self.show_delete_menu)

    def update_limits_in_plot(self, *args):
        if self.ui.var_type_combo.currentIndex() != 0:
            self.matplot_widget.add_max_min_opt_lines(None, None, None)
            return
        if self.details_ui is None:
            return
        mini = self.details_ui.minimum_val.value()
        maxi = self.details_ui.maximum_val.value()
        opti = self.details_ui.optimum_val.value()
        opti = mini + opti * (maxi - mini) / 100
        self.rational["max"] = maxi
        self.rational["min"] = mini
        self.rational["opt"] = opti
        self.matplot_widget.add_max_min_opt_lines(mini, opti, maxi)

    def save_meta_data(self):
        var_type = 0  # nominal should be 1
        if self.ui.var_type_combo.currentIndex() == 0:
            var_type = 1  # real should be 1

        #save variable type
        save_is_real_by_name(self.var_name, var_type)

        #save description
        desc_text = self.ui.var_description.toPlainText()
        save_var_description_by_name(self.var_name, str(desc_text))


        #save other values
        if var_type == 1:
            #real
            save_real_meta_by_name(self.var_name, self.rational["min"],
                                   self.rational["max"], self.rational["opt"])
        elif var_type == 0:
            self.nominal_model.save_into_db()

    def show_plot_tooltip(self,subj,position):
        message = "Subject: %s" % subj
        QtGui.QToolTip.showText(self.matplot_widget.mapToGlobal(QtCore.QPoint(*position)), message, self.matplot_widget)

    def show_delete_menu(self,pos):
        print "showing menu"
        menu = QtGui.QMenu()
        mod = self.ui.tableView.model()
        cur_idx=self.ui.tableView.currentIndex()
        idx2 = mod.index(cur_idx.row(),0)
        var_name = mod.data(idx2,QtCore.Qt.DisplayRole)
        def delete_var():
            confirm = QtGui.QMessageBox.question(self,
                "Confirm delete variable","Are you sure you want to delete \n%s ?\nThis is not reversible"%var_name,
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.Cancel,QtGui.QMessageBox.Cancel)
            if confirm == QtGui.QMessageBox.Yes:
                print "deleting"
                var_idx = braviz_tab_data.get_var_idx(var_name)
                if var_idx is not None:
                    braviz_tab_data.recursive_delete_variable(var_idx)
                mod.update_list(None)
            else:
                "cancelled"
        action = QtGui.QAction("Delete %s"%var_name,menu)
        menu.addAction(action)
        action.triggered.connect(delete_var)
        global_pos = self.ui.tableView.mapToGlobal(pos)
        menu.exec_(global_pos)


class OutcomeSelectDialog(VariableSelectDialog):
    def __init__(self, params_dict, multiple=False,sample=None):
        super(OutcomeSelectDialog, self).__init__(sample)
        self.ui = Ui_SelectOutcomeDialog()
        self.ui.setupUi(self)
        self.finish_ui_setup()

        self.params_dict = params_dict

        self.vars_list_model = braviz_models.VarListModel(checkeable=multiple)
        self.ui.tableView.setModel(self.vars_list_model)
        self.ui.tableView.clicked.connect(self.update_right_side)
        self.ui.tableView.activated.connect(self.update_right_side)

        self.ui.select_button.clicked.connect(self.select_and_return)
        self.ui.search_box.returnPressed.connect(self.filter_list)


    def update_right_side(self, var_name=None):
        curr_idx = self.ui.tableView.currentIndex()
        var_name = self.vars_list_model.data(curr_idx, QtCore.Qt.DisplayRole)
        self.ui.select_button.setEnabled(True)
        super(OutcomeSelectDialog, self).update_right_side(var_name)


    def update_plot(self, data):
        data2=data.dropna()
        self.matplot_widget.compute_scatter(data2.get_values(),
                                            x_lab=self.var_name, y_lab="jitter",urls=data2.index.get_values())


    def select_and_return(self, *args):
        if self.var_name is not None:
            self.save_meta_data()
        if self.params_dict is not None:
            self.params_dict["selected_outcome"] = self.var_name
        self.accept()

    def filter_list(self):
        mask = "%%%s%%"%self.ui.search_box.text()
        self.vars_list_model.update_list(mask)



class GenericVariableSelectDialog(OutcomeSelectDialog):
    """
    Derived from Outcome Select Dialog,
    """

    def __init__(self, params, multiple=False, initial_selection_names=None, initial_selection_idx=None,sample=None):
        OutcomeSelectDialog.__init__(self, params, multiple=multiple,sample=sample)
        self.multiple = multiple
        self.setWindowTitle("Select Variables")
        self.ui.select_button.setText("Accept Selection")
        self.ui.select_button.setEnabled(True)
        if initial_selection_idx is not None:
            self.vars_list_model.select_items(initial_selection_idx)
        elif initial_selection_names is not None:
            self.vars_list_model.select_items_by_name(initial_selection_names)


    def select_and_return(self, *args):
        if self.multiple is True:
            selected_names = self.vars_list_model.checked_set
            self.params_dict["checked"] = [get_var_idx(name) for name in selected_names]
        OutcomeSelectDialog.select_and_return(self, *args)


class MultiPlotOutcomeSelectDialog(OutcomeSelectDialog):
    def __init__(self, params_dict, multiple=False,sample=None,available_plots=None):
        VariableSelectDialog.__init__(self)
        self.ui = Ui_SelectOutcomeMPDialog()
        self.ui.setupUi(self)
        if available_plots is not None:
            for k in available_plots.iterkeys():
                self.ui.plot_type.addItem(k)
        self.available_plots = available_plots
        self.finish_ui_setup()

        self.params_dict = params_dict

        self.vars_list_model = braviz_models.VarListModel(checkeable=multiple)
        self.ui.tableView.setModel(self.vars_list_model)
        self.ui.tableView.clicked.connect(self.update_right_side)
        self.ui.tableView.activated.connect(self.update_right_side)

        self.ui.select_button.clicked.connect(self.select_and_return)
        self.ui.search_box.returnPressed.connect(self.filter_list)
        self.ui.plot_type.activated.connect(self.update_plot)

    def update_plot(self, data=None):
        if type(data) == int:
            data = self.data

        default_plot = ("scatter",None)
        if self.available_plots is None:
            plot_type = default_plot
        else:
            plot_str = str(self.ui.plot_type.currentText())
            plot_type = self.available_plots.get(plot_str,default_plot)
        print plot_type
        if plot_type[0]=="scatter":
            if plot_type[1] is None:
                data=data.dropna()
                self.matplot_widget.compute_scatter(data,x_lab=self.var_name,y_lab="jitter",urls=data.index)
                self.matplot_widget.limits_vertical = True
            else:
                x = plot_type[1]
                y = self.var_name
                data = braviz_tab_data.get_data_frame_by_name([x,y])
                data = data.loc[self.sample]
                data.dropna(inplace=True)
                self.matplot_widget.compute_scatter(data[x],data[y],x_lab=x,y_lab=y,urls=data.index)
                self.matplot_widget.limits_vertical = False
        elif plot_type[0]=="box":
            x = plot_type[1]
            y = self.var_name
            data = braviz_tab_data.get_data_frame_by_name([y,x])
            data = data.loc[self.sample]
            data.dropna(inplace=True)
            label_nums = set(data[x])
            labels_dict = braviz_tab_data.get_names_label_dict(x)
            data_list = []
            ticks = []
            for i in label_nums:
                data_col = data[y][data[x] == i]
                data_list.append(data_col.get_values())
                ticks.append(labels_dict.get(i, str(i)))
            #print data_list
            self.matplot_widget.make_box_plot(data_list, x, y, ticks)
            self.matplot_widget.limits_vertical = False
        elif plot_type[0]=="interaction":
            factors = plot_type[1].split("*")
            self.matplot_widget.limits_vertical = False
            self.two_factors_plot(factors)
        QtCore.QTimer.singleShot(10,self.update_limits_in_plot)

    def two_factors_plot(self, factors_list):
        #copied from anova application... not a good practice
        nominal_factors = []
        real_factors = []
        #classify factors
        for f in factors_list:
            is_real = braviz_tab_data.is_variable_name_real(f)
            if is_real == 0:
                nominal_factors.append(f)
            else:
                real_factors.append(f)
        if len(real_factors) == 1:

            top_labels_dict = braviz_tab_data.get_names_label_dict(nominal_factors[0])
            colors = sns.color_palette("Dark2",len(top_labels_dict))
            #print top_labels_strings
            colors_dict = dict(izip(top_labels_dict.iterkeys(), colors))
            plot_color = colors_dict
            #Get Data
            data = get_data_frame_by_name([real_factors[0], nominal_factors[0], self.var_name])
            data = data.loc[self.sample]
            data.dropna(inplace=True)
            self.plot_data_frame = data

            datax = []
            datay = []
            colors = []
            labels = []
            urls = []
            for k, v in top_labels_dict.iteritems():
                if k is None:
                    continue
                if v is None:
                    v="?"
                labels.append(v)
                colors.append(colors_dict[k])
                datay.append(data[self.var_name][data[nominal_factors[0]] == k].get_values())
                datax.append(data[real_factors[0]][data[nominal_factors[0]] == k].get_values())
                urls.append(data[self.var_name][data[nominal_factors[0]] == k].index.get_values())
            #print datax
            self.matplot_widget.compute_scatter(datax, datay, real_factors[0], self.var_name, colors, labels, urls=urls)


        elif len(real_factors) == 2:
            log = logging.getLogger(__name__)
            log.warning("Not yet implemented")
            self.matplot_widget.initial_text("Not yet implemented")
        else:
            #get data
            data = get_data_frame_by_name(nominal_factors + [self.var_name])
            data = data.loc[self.sample]
            data.dropna(inplace=True)
            #find number of levels for nominal
            nlevels = {}
            for f in nominal_factors:
                nlevels[f] = len(data[f].unique())
            #print nlevels
            nominal_factors.sort(key=nlevels.get, reverse=True)
            #print nominal_factors

            levels_second_factor = set(data[nominal_factors[1]].get_values())
            levels_first_factor = set(data[nominal_factors[0]].get_values())
            data_lists_top = []
            for i in levels_second_factor:
                data_list = []
                for j in levels_first_factor:
                    data_col = data[self.var_name][(data[nominal_factors[1]] == i) &
                                                           (data[nominal_factors[0]] == j)].get_values()
                    data_list.append(data_col)
                data_lists_top.append(data_list)

            self.matplot_widget.make_linked_box_plot(data, self.var_name, nominal_factors[0], nominal_factors[1])
class SelectOneVariableWithFilter(OutcomeSelectDialog):
    """
    Derived from Outcome Select Dialog,
    """
    def __init__(self, params, accept_nominal=True, accept_real=True,sample=None):
        OutcomeSelectDialog.__init__(self, params, multiple=False,sample=sample)
        self.setWindowTitle("Select Variable")
        self.accept_real = accept_real
        self.accept_nominal = accept_nominal

    def check_selecion(self):
        is_current_variable_real=(self.ui.var_type_combo.currentIndex() == 0)
        if (is_current_variable_real and self.accept_real) or (not is_current_variable_real and self.accept_nominal):
            self.ui.select_button.setEnabled(True)
        else:
            self.ui.select_button.setEnabled(False)

    def update_details(self, index):
        super(SelectOneVariableWithFilter,self).update_details(index)
        self.check_selecion()


class RegressorSelectDialog(VariableSelectDialog):
    def __init__(self, outcome_var, regressors_model,sample=None):
        super(RegressorSelectDialog, self).__init__(sample=sample)
        self.outcome_var = outcome_var
        self.ui = Ui_AddRegressorDialog()
        self.ui.setupUi(self)
        self.vars_model = braviz_models.VarAndGiniModel(outcome_var)
        self.ui.tableView.setModel(self.vars_model)
        self.finish_ui_setup()
        self.ui.tableView.clicked.connect(self.update_right_side)
        self.ui.tableView.activated.connect(self.update_right_side)
        self.ui.add_button.clicked.connect(self.add_regressor)
        self.regressors_table_model = regressors_model
        self.ui.current_regressors_table.setModel(self.regressors_table_model)
        self.ui.current_regressors_table.customContextMenuRequested.connect(self.show_context_menu)
        self.ui.done_button.clicked.connect(self.finish_close)
        self.ui.search_box.returnPressed.connect(self.filter_list)

    def update_right_side(self, name=None):
        curr_idx = self.ui.tableView.currentIndex()
        idx2 = self.vars_model.index(curr_idx.row(), 0)
        var_name = self.vars_model.data(idx2, QtCore.Qt.DisplayRole)
        self.ui.add_button.setEnabled(True)
        super(RegressorSelectDialog, self).update_right_side(var_name)

    def add_regressor(self):
        self.regressors_table_model.add_regressor(self.var_name)

    def show_context_menu(self, pos):
        global_pos = self.ui.current_regressors_table.mapToGlobal(pos)
        selection = self.ui.current_regressors_table.currentIndex()
        remove_action = QtGui.QAction("Remove", None)
        menu = QtGui.QMenu()
        menu.addAction(remove_action)

        def remove_item(*args):
            self.regressors_table_model.removeRows(selection.row(), 1)

        remove_action.triggered.connect(remove_item)
        menu.addAction(remove_action)
        selected_item = menu.exec_(global_pos)
        # print selected_item

    def update_plot(self, data):
        regressor_data = data
        if self.outcome_var is not None:
            if self.outcome_var in regressor_data.columns:
                both_data = regressor_data
            else:
                outcome_data = get_data_frame_by_name(self.outcome_var)
                both_data=regressor_data.join(outcome_data)
            both_data.dropna(inplace=True)

            self.matplot_widget.compute_scatter(both_data.iloc[:,0].get_values(), both_data.iloc[:,1].get_values(),
                                                x_lab=self.var_name, y_lab=self.outcome_var,
                                                urls=both_data.index.get_values())
        else:
            data2=data.dropna()
            self.matplot_widget.compute_scatter(data2.get_values(),urls=data2.index.get_values())

    def finish_close(self):
        self.done(self.Accepted)

    def filter_list(self):
        mask = "%%%s%%"%self.ui.search_box.text()
        self.vars_model.update_list(mask)


class InteractionSelectDialog(QtGui.QDialog):
    def __init__(self, regressors_model):
        super(InteractionSelectDialog, self).__init__()
        self.full_model = regressors_model
        regressors = regressors_model.get_regressors()
        self.only_regs_model = braviz_models.AnovaRegressorsModel(regressors)

        self.ui = Ui_InteractionsDiealog()
        self.ui.setupUi(self)
        self.ui.reg_view.setModel(self.only_regs_model)
        self.full_model.show_regressors(False)
        self.ui.full_view.setModel(self.full_model)
        self.ui.add_single_button.clicked.connect(self.add_single_term)
        self.ui.add_all_button.clicked.connect(self.add_all_combinations)

    def add_single_term(self):
        selected_indexes = self.ui.reg_view.selectedIndexes()
        selected_row_numbers = set(i.row() for i in selected_indexes)
        log = logging.getLogger(__name__)
        log.info(selected_row_numbers)
        self.full_model.add_interactor(selected_row_numbers)

    def add_all_combinations(self):
        rows = range(self.only_regs_model.rowCount())
        for r in xrange(2, len(rows) + 1):
            for i in itertools.combinations(rows, r):
                self.full_model.add_interactor(i)


class NewVariableDialog(QtGui.QDialog):
    def __init__(self):
        super(NewVariableDialog, self).__init__()
        self.ui = Ui_NewVariableDialog()
        self.ui.setupUi(self)
        self.ui.var_type_combo.currentIndexChanged.connect(self.create_meta_data_frame)
        self.details_ui = None
        self.nominal_model = None
        #self.clear_details_frame():
        initial_nominal = 0
        self.create_real_details()
        self.ui.var_type_combo.setCurrentIndex(initial_nominal)
        #self.create_meta_data_frame(initial_nominal)
        self.values_model = braviz_models.NewVariableValues()
        self.ui.values_table.setModel(self.values_model)
        self.ui.var_name_input.editingFinished.connect(self.activate_save_button)
        self.ui.save_button.clicked.connect(self.save_new_variable)

    def create_meta_data_frame(self, is_nominal):
        self.clear_details_frame()
        if is_nominal == 0:
            #real
            QtCore.QTimer.singleShot(0, self.create_real_details)
        else:
            QtCore.QTimer.singleShot(0, self.create_nominal_details)

    def create_real_details(self):
        #print "creating real details"
        details_ui = Ui_rational_details()
        details_ui.setupUi(self.ui.details_frame)
        self.details_ui = details_ui
        self.details_ui.optimum_val.valueChanged.connect(self.update_optimum_real_value)
        #try to read values from DB
        self.details_ui.maximum_val.setValue(100)
        self.details_ui.minimum_val.setValue(0)
        self.details_ui.optimum_val.setValue(50)
        self.update_optimum_real_value()

    def create_nominal_details(self):
        #print "creating details"
        if self.nominal_model is None:
            self.nominal_model = braviz_models.NominalVariablesMeta(None)
        else:
            self.nominal_model.update_model(None)
        details_ui = Ui_nominal_details_frame()
        details_ui.setupUi(self.ui.details_frame)

        details_ui.labels_names_table.setModel(self.nominal_model)
        add_label_button = QtGui.QPushButton("Add Label")
        details_ui.verticalLayout.addWidget(add_label_button)
        add_label_button.clicked.connect(self.nominal_model.add_label)
        self.details_ui = details_ui


    def clear_details_frame(self, layout=None):
        if layout is None:
            layout = self.ui.details_frame.layout()
        if layout is None:
            return
        for i in reversed(xrange(layout.count())):
            item = layout.takeAt(i)
            if isinstance(item, QtGui.QWidgetItem):
                item.widget().deleteLater()
            elif isinstance(item, QtGui.QSpacerItem):
                pass
            else:
                self.clearLayout(item.layout())

        layout.deleteLater()

    def update_optimum_real_value(self, perc_value=None):
        maxi = self.details_ui.maximum_val.value()
        mini = self.details_ui.minimum_val.value()
        if perc_value is None:
            perc_value = self.details_ui.optimum_val.value()
        real_value = perc_value / 100 * (maxi - mini) + mini
        self.details_ui.optimum_real_value.setNum(real_value)

    def activate_save_button(self):
        if len(str(self.ui.var_name_input.text()))>0:
            self.ui.save_button.setEnabled(True)

    def save_new_variable(self):
        #create new variable
        var_name = str(self.ui.var_name_input.text())
        is_real = 1-self.ui.var_type_combo.currentIndex()
        var_idx = register_new_variable(var_name,is_real)
        #add meta data
        if is_real:
            mini=self.details_ui.minimum_val.value()
            maxi=self.details_ui.maximum_val.value()
            opti=self.details_ui.optimum_val.value()
            opti = mini + opti * (maxi - mini) / 100
            save_real_meta(var_idx,mini,maxi,opti)
        else:
            self.nominal_model.save_into_db(var_idx)
        #description
        desc=str(self.ui.var_description.toPlainText())
        save_var_description(var_idx,desc)
        #values
        self.values_model.save_into_db(var_idx)
        self.accept()


class ContextVariablesSelectDialog(VariableSelectDialog):
    def __init__(self, variables_list=None, current_subject=None, editables_dict=None,sample=None):
        super(ContextVariablesSelectDialog, self).__init__(sample=sample)
        if variables_list is None:
            variables_list = []
        self.__variable_lists_id = id(variables_list)
        self.current_subject = current_subject
        self.ui = Ui_ContextVariablesDialog()
        self.ui.setupUi(self)
        self.vars_model = braviz_models.VarListModel(checkeable=False)
        self.ui.tableView.setModel(self.vars_model)
        self.finish_ui_setup()
        self.ui.tableView.clicked.connect(self.update_right_side)
        self.ui.tableView.activated.connect(self.update_right_side)
        self.ui.add_button.clicked.connect(self.add_variable)
        self.current_variables_model = braviz_models.ContextVariablesModel(context_vars_list=variables_list,
                                                                           editable_dict=editables_dict)
        self.ui.current_variables.setModel(self.current_variables_model)
        self.ui.current_variables.customContextMenuRequested.connect(self.show_context_menu)
        self.ui.done_button.clicked.connect(self.finish_close)
        self.ui.current_variables.clicked.connect(self.update_right_side2)

        self.ui.create_varible_button.clicked.connect(self.launch_new_variable_dialog)
        self.ui.search_box.returnPressed.connect(self.filter_list)
        self.jitter = None
        self.variable_list = variables_list


    def update_right_side(self, curr_idx=None):
        idx2 = self.vars_model.index(curr_idx.row(), 0)
        var_name = self.vars_model.data(idx2, QtCore.Qt.DisplayRole)
        self.ui.add_button.setEnabled(True)
        super(ContextVariablesSelectDialog, self).update_right_side(var_name)

    def update_right_side2(self, idx):
        var_name_idx = self.current_variables_model.index(idx.row(), 0)
        var_name = self.current_variables_model.data(var_name_idx, QtCore.Qt.DisplayRole)
        super(ContextVariablesSelectDialog, self).update_right_side(var_name)

    def add_variable(self):
        var_idx = get_var_idx(self.var_name)
        self.current_variables_model.add_variable(var_idx)

    def show_context_menu(self, pos):
        global_pos = self.ui.current_variables.mapToGlobal(pos)
        selection = self.ui.current_variables.currentIndex()
        remove_action = QtGui.QAction("Remove", None)
        menu = QtGui.QMenu()
        menu.addAction(remove_action)

        def remove_item(*args):
            self.current_variables_model.removeRows(selection.row(), 1)

        remove_action.triggered.connect(remove_item)
        menu.addAction(remove_action)
        menu.exec_(global_pos)


    def update_plot(self, data):
        data=data.dropna()
        self.jitter = np.random.random(len(data))
        data_values = data.get_values()
        xlimits = get_min_max_values_by_name(self.var_name)
        self.matplot_widget.compute_scatter(data_values, self.jitter, x_lab=self.var_name, xlims=xlimits,
                                            urls=data.index.get_values())
        if self.current_subject is not None:
            try:
                subj_index = data.index.get_loc(int(self.current_subject))
                self.matplot_widget.add_subject_points((data_values[subj_index]), (self.jitter[subj_index],),
                                                   urls=(self.current_subject,))
            except KeyError:
                pass


    def finish_close(self):
        new_list = self.current_variables_model.get_variables()
        while len(self.variable_list) > 0:
            self.variable_list.pop()
        self.variable_list.extend(new_list)
        assert id(self.variable_list) == self.__variable_lists_id
        self.done(self.Accepted)

    def launch_new_variable_dialog(self):
        new_variable_dialog = NewVariableDialog()
        r=new_variable_dialog.exec_()
        if r == QtGui.QDialog.Accepted:
            self.vars_model.update_list()


    def filter_list(self):
        mask = "%%%s%%"%self.ui.search_box.text()
        self.vars_model.update_list(mask)


class ContextVariablesPanel(QtGui.QGroupBox):
    def __init__(self, parent, title="Context", initial_variable_idxs=(11, 6, 17, 1), initial_subject=None,app=None,
                 sample = None):
        super(ContextVariablesPanel, self).__init__(parent)
        self.setTitle(title)
        self.setToolTip("Right click to select context variables, and to make them editable")
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.layout = QtGui.QHBoxLayout(self)
        self.setLayout(self.layout)
        self.app = app
        self.sample = sample
        if self.sample is None:
            self.sample = braviz_tab_data.get_subjects()

        self.layout.setContentsMargins(7, 2, 7, 2)
        self.customContextMenuRequested.connect(self.create_context_menu)

        size_policy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Maximum)
        #size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(1)
        self.setSizePolicy(size_policy)
        #self.setMaximumSize(QtCore.QSize(16777215, 56))
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setObjectName(_fromUtf8("context_frame"))
        #self.setFrameStyle(self.NoFrame)

        #internal variables
        self.__context_variable_codes = None
        self.__context_variable_names = None
        self.__is_nominal = None
        self.__labels_dict = None
        self.__context_labels = None
        self.__values_widgets = None
        self.__internal_df = None
        self.__curent_subject = None
        self.__editables_dict = None
        self.__save_changes_button = None
        self.set_variables(initial_variable_idxs)
        if initial_subject is not None:
            self.set_subject(initial_subject)

    def set_variables(self, variables, editables=None):
        self.__context_variable_codes = list(variables)
        self.__context_variable_names = dict((idx, get_var_name(idx)) for idx in self.__context_variable_codes)
        self.__is_nominal = dict((idx, is_variable_nominal(idx)) for idx in self.__context_variable_codes)
        self.__labels_dict = dict((idx, get_labels_dict(idx)) for idx in self.__context_variable_codes if
                                  self.__is_nominal[idx])
        self.__internal_df = get_data_frame_by_index(self.__context_variable_codes)
        self.__values_widgets = []
        if editables is None:
            self.__editables_dict = dict((idx, False) for idx in variables)
        else:
            self.__editables_dict = editables
        self.reset_internal_widgets()

    def get_variables(self):
        return self.__context_variable_codes

    def get_editables(self):
        return self.__editables_dict.iteritems()

    def reset_internal_widgets(self):
        #clear layout
        self.__save_changes_button = None
        for i in xrange(self.layout.count() - 1, -1, -1):
            w = self.layout.takeAt(i)
            wgt = w.widget()
            if wgt is not None:
                wgt.deleteLater()

        self.__context_labels = []
        self.__values_widgets = []

        first = True
        any_editable = False
        for idx in self.__context_variable_codes:
            #add separator
            if not first:
                self.layout.addStretch()
            else:
                first = False
            #add label
            label = QtGui.QLabel("%s : " % self.__context_variable_names[idx])
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.__context_labels.append(label)
            self.layout.addWidget(label)
            #add value
            if self.__editables_dict.get(idx) is True:
                value_widget = self.get_editable_widget(idx)
                any_editable = True
            else:
                value_widget = self.get_read_only_widget(idx)
            self.layout.addWidget(value_widget)
            self.__values_widgets.append(value_widget)
        if any_editable is True:
            self.__save_changes_button = QtGui.QPushButton("Save")
            self.__save_changes_button.setEnabled(False)
            self.__save_changes_button.clicked.connect(self.save_changes_into_db)
            self.layout.addWidget(self.__save_changes_button)
        return

    def get_read_only_widget(self, idx):
        value_widget = QtGui.QLabel("XXXXXXX")
        value_widget.setFrameShape(QtGui.QFrame.Box)
        value_widget.setFrameShadow(QtGui.QFrame.Raised)
        #value_widget.setContentsMargins(7,7,7,7)
        value_widget.setMargin(7)
        value_widget.setAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setPointSize(11)
        value_widget.setFont(font)
        value_widget.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        value_widget.setCursor(QtCore.Qt.IBeamCursor)
        #calculate maximum width
        if is_variable_nominal(idx):
            lens = [(x,len(x)) for x in self.__labels_dict[idx].itervalues() if x is not None]
            if len (lens)==0:
                longest="<Unknown>"
            else:
                longest = max(lens,key=lambda x:x[1])[0]
            value_widget.setText(longest)
            longest_size = value_widget.sizeHint()
            value_widget.setFixedWidth(longest_size.width())
            value_widget.setFixedHeight(longest_size.height())
        else:
            max_value = get_maximum_value(idx)
            if max_value is None:
                max_value = 1000
            value_widget.setText("%.2f" % max_value)
            longest_size = value_widget.sizeHint()
            value_widget.setFixedWidth(longest_size.width())
            value_widget.setFixedHeight(longest_size.height())
        return value_widget

    def get_editable_widget(self, idx):
        if self.__is_nominal.get(idx) is True:
            value_widget = QtGui.QComboBox()
            for i, lbl in self.__labels_dict[idx].iteritems():
                if not np.isnan(float(i)):
                    value_widget.addItem(lbl, i)
            value_widget.insertSeparator(value_widget.count())
            value_widget.addItem("<Unknown>",float("nan"))
            value_widget.currentIndexChanged.connect(self.enable_save_changes)
        else:
            value_widget = QtGui.QDoubleSpinBox()
            minim, maxim = get_min_max_values(idx)
            value_widget.setMaximum(10 * maxim)
            value_widget.setMinimum(-10 * maxim)
            value_widget.setSingleStep((maxim - minim) / 20)
            value_widget.valueChanged.connect(self.enable_save_changes)
        font = QtGui.QFont()
        font.setPointSize(11)
        value_widget.setFont(font)
        return value_widget

    def set_subject(self, subject_id):
        values = self.__internal_df.loc[int(subject_id)]
        for i, idx in enumerate(self.__context_variable_codes):
            try:
                value = values[self.__context_variable_names[idx]]
            except KeyError:
                value = float("nan")
            #print self.__context_variable_names[idx], value
            value_widget = self.__values_widgets[i]
            if self.__is_nominal[idx]:

                if isinstance(value_widget, QtGui.QLabel):
                    label = self.__labels_dict[idx].get(value, "?")
                    if label is None:
                        label = "?"
                    value_widget.setText(label)
                elif isinstance(value_widget, QtGui.QComboBox):
                    label = self.__labels_dict[idx].get(value, "<Unknown>")
                    index = value_widget.findText(label)
                    value_widget.setCurrentIndex(index)
            else:
                if isinstance(value_widget, QtGui.QLabel):
                    value_widget.setText("%s" % value)
                elif isinstance(value_widget, QtGui.QDoubleSpinBox):
                    value_widget.setValue(value)
        self.__curent_subject = subject_id
        if self.__save_changes_button is not None:
            self.__save_changes_button.setEnabled(False)

    def create_context_menu(self, pos):
        global_pos = self.mapToGlobal(pos)
        change_action = QtGui.QAction("Change Variables", None)
        menu = QtGui.QMenu()
        menu.addAction(change_action)

        def change_variables(*args):
            context_change_dialog = ContextVariablesSelectDialog(current_subject=self.__curent_subject,
                                                                 variables_list=self.__context_variable_codes,
                                                                 editables_dict=self.__editables_dict,
                                                                 sample = self.sample)
            context_change_dialog.exec_()
            self.set_variables(self.__context_variable_codes, self.__editables_dict)
            self.set_subject(self.__curent_subject)

        change_action.triggered.connect(change_variables)
        menu.addAction(change_action)
        menu.exec_(global_pos)

    def enable_save_changes(self, *args):
        if self.__save_changes_button is None:
            return
        self.__save_changes_button.setEnabled(True)

    def save_changes_into_db(self):

        for i,idx in enumerate(self.__context_variable_codes):
            if self.__editables_dict[idx] is True:
                value_widget = self.__values_widgets[i]
                if isinstance(value_widget,QtGui.QDoubleSpinBox):
                    value = float(value_widget.value())
                elif isinstance(value_widget,QtGui.QComboBox):
                    value=value_widget.itemData(value_widget.currentIndex())
                    value=value.toDouble()[0]
                    if np.isnan(float(value)):
                        value = None
                    else:
                        value=int(value)
                #update value
                braviz_tab_data.updata_variable_value(int(idx),self.__curent_subject,value)
                #update internal
                var_name = self.__context_variable_names[idx]
                self.__internal_df[var_name][int(self.__curent_subject)]=value
                #check if scenarios exists for this variable
                if braviz_user_data.count_variable_scenarios(int(idx)) == 0:
                    #save scenario
                    name = "<AUTO_%s>"%self.__context_variable_names[idx]
                    desc = "Created automatically when saving values for variable %s"%self.__context_variable_names[idx]
                    data = self.app.get_state_dict()
                    app = data["meta"]["application"]
                    data_s = cPickle.dumps(data,2)
                    scn_idx=braviz_user_data.save_scenario(app,name,desc,data_s)
                    #link
                    braviz_user_data.link_var_scenario(int(idx),scn_idx)
                    #save screenshot
                    self.app.save_screenshot(scn_idx)

        self.__save_changes_button.setEnabled(0)
        #print idx_value_tuples

    def set_sample(self,new_sample):
        self.sample = list(new_sample)

class BundleSelectionDialog(QtGui.QDialog):
    def __init__(self,selected,names_dict):
        super(BundleSelectionDialog,self).__init__()
        self.ui = None
        self.bundles_list_model=braviz_models.BundlesSelectionList()
        self.bundles_list_model.select_many_ids(selected)
        self.load_ui()
        self.selection=selected
        self.names_dict=names_dict

    def load_ui(self):
        self.ui = Ui_LoadBundles()
        self.ui.setupUi(self)
        self.ui.all_bundles_list_view.setModel(self.bundles_list_model)
        self.ui.buttonBox.accepted.connect(self.ok_handle)

    def ok_handle(self):
        new_select = set(self.bundles_list_model.get_selected())
        self.selection.clear()
        self.selection.update(new_select)
        self.names_dict.update(self.bundles_list_model.names_dict)


class SaveFibersBundleDialog(QtGui.QDialog):
    def __init__(self,operation,checkpoints_list,operation_is_and):
        super(SaveFibersBundleDialog,self).__init__()
        self.ui = Ui_SaveBundleDialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.button(QtGui.QDialogButtonBox.Save).setEnabled(False)
        self.ui.buttonBox.button(QtGui.QDialogButtonBox.Ok).setEnabled(False)
        self.ui.lineEdit.textChanged.connect(self.check_name)
        self.ui.error_message.setText("")
        self.ui.save_succesful.setText("")
        self.ui.operation_label.setText(operation)
        self._checkpoints = tuple(checkpoints_list)
        self.ui.structures_list.setPlainText(", ".join(self._checkpoints))
        self.ui.buttonBox.button(QtGui.QDialogButtonBox.Save).clicked.connect(self.accept_save)
        self.ui.buttonBox.button(QtGui.QDialogButtonBox.Ok).clicked.connect(self.accept)
        self._and= operation_is_and



    def check_name(self):
        name = str(self.ui.lineEdit.text())
        if len(name)<2:
            self.ui.buttonBox.button(QtGui.QDialogButtonBox.Save).setEnabled(False)
            return
        if bundles_db.check_if_name_exists(name) is True:
            self.ui.error_message.setText("A bundle with this name already exists")
            self.ui.buttonBox.button(QtGui.QDialogButtonBox.Save).setEnabled(False)
        else:
            self.ui.buttonBox.button(QtGui.QDialogButtonBox.Save).setEnabled(True)
            self.ui.error_message.setText("")

    def accept_save(self):
        log = logging.getLogger(__name__)
        log.info("saving")
        name = str(self.ui.lineEdit.text())
        log.info(str(self.ui.lineEdit.text()))
        op =  "and" if self._and else "or"
        log.info(op)
        log.info(self._checkpoints)
        try :
            bundles_db.save_checkpoints_bundle(name, self._and,self._checkpoints)
        except:
            log.error("problem saving into database")
            raise
        self.ui.save_succesful.setText("Save succesful")
        self.ui.buttonBox.button(QtGui.QDialogButtonBox.Ok).setEnabled(True)
        self.ui.buttonBox.button(QtGui.QDialogButtonBox.Save).setEnabled(False)
        self.ui.buttonBox.button(QtGui.QDialogButtonBox.Cancel).setEnabled(False)
        self.ui.lineEdit.setEnabled(False)

class SaveLogicFibersBundleDialog(QtGui.QDialog):
    def __init__(self,tree_model):
        super(SaveLogicFibersBundleDialog,self).__init__()
        self.__tree_model = tree_model
        self.ui = Ui_SaveLogicBundleDialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.button(QtGui.QDialogButtonBox.Save).setEnabled(False)
        self.ui.buttonBox.button(QtGui.QDialogButtonBox.Ok).setEnabled(False)
        self.ui.lineEdit.textChanged.connect(self.check_name)
        self.ui.error_message.setText("")
        self.ui.save_succesful.setText("")
        self.ui.treeView.setModel(tree_model)
        self.ui.treeView.expandAll()
        self.ui.buttonBox.button(QtGui.QDialogButtonBox.Save).clicked.connect(self.accept_save)
        self.ui.buttonBox.button(QtGui.QDialogButtonBox.Ok).clicked.connect(self.accept)

    def check_name(self):
        name = str(self.ui.lineEdit.text())
        if len(name)<2:
            self.ui.buttonBox.button(QtGui.QDialogButtonBox.Save).setEnabled(False)
            return
        if bundles_db.check_if_name_exists(name) is True:
            self.ui.error_message.setText("A bundle with this name already exists")
            self.ui.buttonBox.button(QtGui.QDialogButtonBox.Save).setEnabled(False)
        else:
            self.ui.buttonBox.button(QtGui.QDialogButtonBox.Save).setEnabled(True)
            self.ui.error_message.setText("")

    def accept_save(self):
        log = logging.getLogger(__name__)
        log.info("saving")
        name = str(self.ui.lineEdit.text())
        log.info(str(self.ui.lineEdit.text()))
        tree_dict = self.__tree_model.root.to_dict()
        log.info(tree_dict)
        try :
            bundles_db.save_logic_bundle(name,tree_dict)
        except:
            log.error("problem saving into database")
            raise
        self.ui.save_succesful.setText("Save succesful")
        self.ui.buttonBox.button(QtGui.QDialogButtonBox.Ok).setEnabled(True)
        self.ui.buttonBox.button(QtGui.QDialogButtonBox.Save).setEnabled(False)
        self.ui.buttonBox.button(QtGui.QDialogButtonBox.Cancel).setEnabled(False)
        self.ui.lineEdit.setEnabled(False)

class SaveScenarioDialog(QtGui.QDialog):
    def __init__(self,app_name,state,params=None):
        super(SaveScenarioDialog,self).__init__()
        self.app_name = app_name
        self.data = cPickle.dumps(state,2)
        if params is None:
            params = dict()
        self.params=params
        self.ui = None
        self.init_gui()


    def init_gui(self):
        self.ui = Ui_SaveScenarioDialog()
        self.ui.setupUi(self)
        self.ui.app_name.setText(self.app_name)
        self.ui.save_button=QtGui.QPushButton("Save")
        self.ui.save_button.clicked.connect(self.save_into_db)
        self.ui.buttonBox.addButton(self.ui.save_button,QtGui.QDialogButtonBox.ActionRole)
        self.ui.buttonBox.addButton(QtGui.QDialogButtonBox.Cancel)
        self.ui.succesful_message.setText("")



    def save_into_db(self):
        scenario_name = str(self.ui.scenario_name.text())
        if len(scenario_name)==0:
            scenario_name = "<Unnamed>"
        description = unicode(self.ui.scn_description.toPlainText())
        scn_id=braviz_user_data.save_scenario(self.app_name,scenario_name , description, self.data)
        self.params["scn_id"]=scn_id
        self.ui.succesful_message.setText("Save completed succesfully")
        self.ui.buttonBox.clear()
        self.ui.buttonBox.addButton(QtGui.QDialogButtonBox.Ok)



class LoadScenarioDialog(QtGui.QDialog):
    def __init__(self,app_name,out_dict=None,reader=None):
        super(LoadScenarioDialog,self).__init__()
        if out_dict is None:
            out_dict = {}
        self.out_dict = out_dict
        self.model = braviz_models.ScenariosTableModel(app_name)
        self.reader = reader
        self.current_row = None
        self.ui = None
        self.init_ui()

    def init_ui(self):
        self.ui = Ui_LoadScenarioDialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.button(QtGui.QDialogButtonBox.Ok).setEnabled(0)
        self.ui.scenarios_table.setModel(self.model)
        self.ui.scenarios_table.clicked.connect(self.select_scenario)
        self.ui.scenarios_table.activated.connect(self.select_scenario)
        self.ui.buttonBox.button(QtGui.QDialogButtonBox.Ok).clicked.connect(self.load_data)

    def select_scenario(self,index):
        row = index.row()
        self.current_row = row
        self.ui.buttonBox.button(QtGui.QDialogButtonBox.Ok).setEnabled(1)
        #load picture
        index = self.model.data(index,QtCore.Qt.UserRole)
        self.ui.screen_shot_label.setText("<No screenshot available>"%index)
        self.ui.screen_shot_label.setScaledContents(False)
        if self.reader is None:
            data_root = braviz.readAndFilter.braviz_auto_dynamic_data_root()
        else:
            data_root = self.reader.get_dyn_data_root()
        image_file = os.path.join(data_root,"braviz_data","scenarios","scenario_%d.png"%index)
        if os.path.isfile(image_file):
            image = QtGui.QImage(image_file)
            scaled_image = image.scaledToWidth(300,)
            self.ui.screen_shot_label.setPixmap(QtGui.QPixmap.fromImage(scaled_image))


    def load_data(self):
        scn_id = int(self.model.get_index(self.current_row))
        data = braviz_user_data.get_scenario_data(scn_id)
        parameters_dict=cPickle.loads(str(data))
        parameters_dict["meta"]["scn_id"] = scn_id
        self.out_dict.update(parameters_dict)
        self.accept()

class LoadLogicBundle(QtGui.QDialog):
    def __init__(self):
        super(LoadLogicBundle,self).__init__()
        self.__tree_root = LogicBundleNode(None,0,LogicBundleNode.LOGIC,"AND")
        self.__tree_model = LogicBundleQtTree(self.__tree_root)
        self.__bundles = bundles_db.get_bundles_list(bundle_type=10)
        self.__bundles_model = braviz_models.SimpleSetModel()
        self.__bundles_model.set_elements(self.__bundles)
        self.ui = Ui_LoadLogicDialog()
        self.ui.setupUi(self)
        self.ui.treeView.setModel(self.__tree_model)
        self.ui.listView.setModel(self.__bundles_model)
        self.ui.listView.clicked.connect(self.update_tree)
        self.ui.listView.activated.connect(self.update_tree)
        self.current_data = None
        self.accepted.connect(self.before_accepting)


    def update_tree(self,index):
        name = str(self.__bundles_model.data(index,QtCore.Qt.DisplayRole))
        data = bundles_db.get_logic_bundle_dict(bundle_name=name)
        self.current_data = data
        self.__tree_root = LogicBundleNode.from_dict(data)
        self.__tree_model.set_root(self.__tree_root)
        self.ui.treeView.expandAll()

    def before_accepting(self):
        index = self.ui.listView.currentIndex()
        self.update_tree(index)

