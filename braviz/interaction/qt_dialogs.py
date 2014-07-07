from __future__ import division

__author__ = 'Diego'
from functools import wraps
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import numpy as np
import itertools
import cPickle
import logging

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

import braviz
from braviz.interaction.qt_guis.outcome_select import Ui_SelectOutcomeDialog
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
import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import os

from itertools import izip

import seaborn as sns


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
            self.sample = sorted(list(sample))
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
        self.details_ui.optimum_val.setValue(int((medi - mini) / (maxi - mini)*100))
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

    def update_limits_in_plot(self, *args):
        if self.ui.var_type_combo.currentIndex() != 0:
            self.matplot_widget.add_max_min_opt_lines(None, None, None)
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
        self.matplot_widget.compute_scatter(data.get_values(),
                                            x_lab=self.var_name, y_lab="jitter",urls=data.index.get_values())


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



class MatplotWidget(FigureCanvas):
    box_outlier_pick_signal = QtCore.pyqtSignal(float, float, tuple)
    scatter_pick_signal = QtCore.pyqtSignal(str, tuple)
    #TODO: instead of using blit create a @wrapper to save last render command to restore after drawing subjects

    def __init__(self, parent=None, dpi=100, initial_message=None):
        fig = Figure(figsize=(5, 5), dpi=dpi, tight_layout=True)
        self.fig = fig
        self.axes = fig.add_subplot(111)
        self.axes2 = None
        #self.axes.hold(False)
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.updateGeometry()
        palette = self.palette()
        self.setContentsMargins(0,0,0,0)
        fig.set_facecolor(palette.background().color().getRgbF()[0:3])
        self.initial_text(initial_message)
        self.back_fig = self.copy_from_bbox(self.axes.bbox)
        self.xlim = self.axes.get_xlim()
        #self.mpl_connect("button_press_event",self.generate_tooltip_event)
        self.mpl_connect("pick_event", self.generate_tooltip_event)
        self.setMouseTracking(True)
        self.mpl_connect('motion_notify_event', self.mouse_move_event_handler)
        self.x_order = None
        self.fliers_x_dict = None

        self.last_plot_function = None
        self.last_plot_arguments = None
        self.last_plot_kw_arguments = None


    def repeatatable_plot(func):
        @wraps(func)
        def saved_plot_func(*args, **kwargs):
            self = args[0]
            self.last_plot_function = func
            self.last_plot_arguments = args
            self.last_plot_kw_arguments = kwargs
            return func(*args, **kwargs)

        return saved_plot_func

    def initial_text(self, message):
        if message is None:
            message = "Welcome"

        sns.set_style("dark")
        self.fig.clear()
        self.axes=self.fig.add_subplot(111)
        self.axes.text(0.5, 0.5, message, horizontalalignment='center',
                       verticalalignment='center', fontsize=12)
        #Remove tick marks
        self.axes.tick_params('y', left='off', right='off', labelleft='off', labelright='off')
        self.axes.tick_params('x', top='off', bottom='off', labelbottom='off', labeltop='off')
        #Remove axes border
        for child in self.axes.get_children():
            if isinstance(child, matplotlib.spines.Spine):
                child.set_visible(False)
        #remove minor tick lines
        for line in self.axes.xaxis.get_ticklines(minor=True) + self.axes.yaxis.get_ticklines(minor=True):
            line.set_markersize(0)
        self.draw()
        self.x_order = None

    @repeatatable_plot
    def compute_scatter(self, data, data2=None, x_lab=None, y_lab=None, colors=None, labels=None, urls=None,
                        xlims=None):
        sns.set_style("darkgrid")
        self.fig.clear()
        self.axes=self.fig.add_subplot(1,1,1)
        self.axes.clear()
        self.axes.tick_params('x', bottom='on', labelbottom='on', labeltop='off',top="off")

        self.axes.yaxis.set_label_position("right")
        #print "urls:" ,urls
        if data2 is None:
            np.random.seed(982356032)
            data2 = np.random.rand(len(data))
            self.axes.tick_params('y', left='off', labelleft='off', labelright='off',right="off")
        else:
            self.axes.tick_params('y', right='on', labelright='on', left='off', labelleft='off')
        if x_lab is not None:
            self.axes.set_xlabel(x_lab)
        if y_lab is not None:
            self.axes.set_ylabel(y_lab)

        if colors is None:
            colors = "#2ca25f"
            self.axes.scatter(data, data2, color=colors, picker=5, urls=urls)
        else:
            for c, d, d2, lbl, url in zip(colors, data, data2, labels, urls):
                self.axes.scatter(d, d2, color=c, label=lbl, picker=5, urls=url)
            self.axes.legend(numpoints=1, fancybox=True, fontsize="small", )
            self.axes.get_legend().draggable(True, update="loc")

        if xlims is not None:
            width = xlims[1] - xlims[0]
            if width == 0:
                xlims2=(xlims[0]-0.5,xlims[0]+0.5)
            else:
                xlims2 = (xlims[0] - width / 10, xlims[1] + width / 10,)
            self.axes.set_xlim(xlims2, auto=False)
        else:
            self.axes.set_xlim(auto=True)
        self.draw()
        self.xlim = self.axes.get_xlim()
        self.x_order = None
        self.back_fig = self.copy_from_bbox(self.axes.bbox)


    def redraw_last_plot(self):
        if self.last_plot_function is None:
            return
        else:
            self.last_plot_function(*self.last_plot_arguments, **self.last_plot_kw_arguments)

    def add_max_min_opt_lines(self, mini, opti, maxi):

        self.restore_region(self.back_fig)
        if mini is None:
            self.blit(self.axes.bbox)
            return
        opt_line = self.axes.axvline(opti, color="#8da0cb")
        min_line = self.axes.axvline(mini, color="#fc8d62")
        max_line = self.axes.axvline(maxi, color="#fc8d62")
        self.axes.set_xlim(self.xlim)
        self.axes.draw_artist(min_line)
        self.axes.draw_artist(max_line)
        self.axes.draw_artist(opt_line)
        self.blit(self.axes.bbox)

    def add_threshold_line(self,thr):
        thr_line = self.axes.axvline(thr, color="#000000")
        self.axes.draw_artist(thr_line)
        self.blit(self.axes.bbox)

    def add_grayed_scatter(self,data,data2):
        colors = "#BBBBBB"
        patches = self.axes.scatter(data, data2, color=colors,)
        self.axes.draw_artist(patches)
        self.blit(self.axes.bbox)


    @repeatatable_plot
    def make_box_plot(self, data, xlabel, ylabel, xticks_labels, ylims, intercet=None):
        sns.set_style("darkgrid")
        self.fig.clear()
        self.axes=self.fig.add_subplot(1,1,1)
        #Sort data and labels according to median
        x_permutation = range(len(data))
        if xticks_labels is None:
                xticks_labels = range(len(data))
        data_labels = zip(data, xticks_labels, x_permutation)
        data_labels.sort(key=lambda x: np.median(x[0]))
        data, xticks_labels, x_permutation = zip(*data_labels)
        self.axes.clear()
        self.axes.tick_params('x', bottom='on', labelbottom='on', labeltop='off', top="off")
        self.axes.tick_params('y', left='off', labelleft='off', labelright='on', right="on")
        self.axes.yaxis.set_label_position("right")
        self.axes.set_ylim(auto=True)
        #artists_dict = self.axes.boxplot(data, sym='gD')

        sns.boxplot(data,ax=self.axes,fliersize=10,names=xticks_labels,color="skyblue",widths=0.5)
        #find fliers
        for ls in self.axes.get_lines():
            if ls.get_markersize() == 10:
                ls.set_picker(5)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)

        #if xticks_labels is not None:
        #    self.axes.get_xaxis().set_ticklabels(xticks_labels)
        yspan = ylims[1] - ylims[0]
        self.axes.set_ylim(ylims[0] - 0.1 * yspan, ylims[1] + 0.1 * yspan)

        self.draw()
        if intercet is not None:
            self.add_intercept_line(intercet)
        self.back_fig = self.copy_from_bbox(self.axes.bbox)
        self.x_order = x_permutation

    @repeatatable_plot
    def make_linked_box_plot(self, data, outcome, x_name, z_name,ylims):
        sns.set_style("darkgrid")
        self.fig.clear()
        self.axes=self.fig.add_subplot(1,1,1)
        #self.axes.tick_params('x', bottom='on', labelbottom='on', labeltop='off', top="off")
        #self.axes.tick_params('y', left='off', labelleft='off', labelright='on', right="on")
        #self.axes.yaxis.set_label_position("right")
        #self.axes.set_ylim(auto=True)

        x_levels = list(data[x_name].unique())
        z_levels = list(data[z_name].unique())
        x_labels = braviz_tab_data.get_names_label_dict(x_name)
        z_labels = braviz_tab_data.get_names_label_dict(z_name)

        palette = sns.color_palette("deep")
        z_colors = dict(izip(z_levels,palette))

        #reorder
        x_levels.sort(reverse=False,key=lambda l:np.median(data[outcome][data[x_name]==l]))
        z_levels.sort(reverse=False,key=lambda l:np.median(data[outcome][data[z_name]==l]))

        log = logging.getLogger(__name__)
        if log.isEnabledFor(logging.DEBUG):
            for i in x_levels:
                log.debug("%s %s",i, np.median(data[outcome][data[x_name]==i]))

        box_width = 0.75
        box_pad = 0.15
        group_pad = 0.5
        group_width = len(z_levels)*box_width + box_pad*(len(z_levels)-1)

        #print "levels"
        labels = []
        colors = []
        values = []
        positions = []
        positions_dict={}
        fliers_x_dict={}

        for ix,iz in itertools.product(xrange(len(x_levels)),xrange(len(z_levels))):
            x = x_levels[ix]
            z = z_levels[iz]
            x_lab = x_labels[x]
            z_lab = z_labels[z]
            labels.append("\n".join((x_lab,z_lab)))
            colors.append(z_colors[z])
            vals = data[outcome][(data[x_name]==x) & (data[z_name]==z)]
            values.append(vals)
            pos = box_width/2 + (group_width+group_pad)*ix + (box_width+box_pad)*iz
            positions.append(pos)
            positions_dict[(x,z)]=pos
            fliers_x_dict[float(pos)]=(x,z)

        sns.boxplot(values,ax=self.axes,names=labels,color=colors,fliersize=10,widths=box_width,positions=positions)

        #find outliers
        for ls in self.axes.get_lines():
            if ls.get_markersize()==10:
                ls.set_picker(5)

        self.axes.set_ylabel(outcome)
        yspan = ylims[1] - ylims[0]
        self.axes.set_ylim(ylims[0] - 0.1 * yspan, ylims[1] + 0.1 * yspan)
        self.draw()
        self.back_fig = self.copy_from_bbox(self.axes.bbox)

        self.x_order = positions_dict
        self.fliers_x_dict = fliers_x_dict

    @repeatatable_plot
    def make_diagnostics(self, residuals,fitted):
        import matplotlib.gridspec as gridspec
        gs = gridspec.GridSpec(1,2,width_ratios=(2,1))
        sns.set_style("darkgrid")
        self.fig.clear()
        self.axes=self.fig.add_subplot(gs[1])
        self.axes.clear()
        self.axes.tick_params('x', bottom='on', labelbottom='on', labeltop='off',top='off')
        self.axes.tick_params('y', left='off', labelleft='off', labelright='off', right="off")
        self.axes.yaxis.set_label_position("right")
        self.axes.set_ylim(auto=True)
        #self.axes.set_ylabel("Residuals")
        self.axes.set_xlabel("Frequency")
        self.axes.hist(residuals, color="#2ca25f", bins=20,orientation = "horizontal")

        self.axes2 = self.fig.add_subplot(gs[0],sharey=self.axes)
        self.axes2.scatter(fitted,residuals,s=20,color="#2ca25f")
        self.axes2.tick_params('x', bottom='on', labelbottom='on', labeltop='off',top='off')
        self.axes2.tick_params('y', left='on', labelleft='on', labelright='off', right="off")
        self.axes2.set_ylabel("Residuals")
        self.axes2.set_xlabel("Fitted")
        self.axes2.yaxis.set_label_position("left")
        self.axes2.axhline(color='k')
        self.draw()
        self.back_fig = self.copy_from_bbox(self.axes.bbox)
        self.x_order = None

    def add_subject_points(self, x_coords, y_coords,z_coords=None, color=None, urls=None):
        #print "adding subjects"
        #self.restore_region(self.back_fig)
        self.redraw_last_plot()
        if self.x_order is not None:
            #labels go from 1 to n; permutation is from 0 to n-1
            if isinstance(self.x_order,dict):
                x_coords = map(self.x_order.get , izip(x_coords,z_coords))
            else:
                assert 0 not in x_coords
                x_coords = map(lambda k: self.x_order.index(int(k - 1)) + 1, x_coords)
        if color is None:
            color = "black"
        collection = self.axes.scatter(x_coords, y_coords, marker="o", s=120, edgecolors=color, urls=urls, picker=5,zorder=10)
        collection.set_facecolor('none')

        self.axes.draw_artist(collection)
        #self.blit(self.axes.bbox)
        self.draw()
        self.back_fig = self.copy_from_bbox(self.axes.bbox)

    def add_intercept_line(self, ycoord):
        self.axes.axhline(ycoord)
        self.draw()
        self.back_fig = self.copy_from_bbox(self.axes.bbox)

    def generate_tooltip_event(self, e):
        #print type(e.artist)
        if type(e.artist) == matplotlib.lines.Line2D:
            dx, dy = e.artist.get_data()
            #print e.ind
            ind = e.ind
            if hasattr(ind, "__iter__"):
                ind = ind[0]
            x, y = dx[ind], dy[ind]
            # correct x position from reordering
            if self.x_order is not None:
                if isinstance(self.x_order,dict):
                    x,_ = self.fliers_x_dict[x]
                else:
                    x = self.x_order[int(x - 1)] + 1
            self.box_outlier_pick_signal.emit(x, y, (e.mouseevent.x, self.height() - e.mouseevent.y))
        elif type(e.artist) == matplotlib.collections.PathCollection:
            if e.artist.get_urls()[0] is None:
                return
            ind = e.ind
            if hasattr(ind, "__iter__"):
                ind = ind[0]

            subj = str(e.artist.get_urls()[ind])
            self.scatter_pick_signal.emit(subj, (e.mouseevent.x, self.height() - e.mouseevent.y))

        else:
            return

    def mouse_move_event_handler(self, event):
        #to avoid interference with draggable legend
        #self.pick(event)
        legend = self.axes.get_legend()
        if (legend is not None) and (legend.legendPatch.contains(event)[0] == 1):
            pass
            #print "in legend"
        else:
            self.pick(event)


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
            outcome_data = get_data_frame_by_name(self.outcome_var)
            both_data=regressor_data.join(outcome_data)
            both_data.dropna(inplace=True)

            self.matplot_widget.compute_scatter(both_data.iloc[:,0].get_values(), both_data.iloc[:,1].get_values(),
                                                x_lab=self.var_name, y_lab=self.outcome_var,
                                                urls=both_data.index.get_values())
        else:
            self.matplot_widget.compute_scatter(data.get_values(),urls=data.index.get_values())

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
        self.rational = {}
        self.create_meta_data_frame(0)
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
            longest = max(self.__labels_dict[idx].itervalues(), key=len)
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
            data_root = self.reader.getDynDataRoot()
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

