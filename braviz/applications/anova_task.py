from __future__ import division

__author__ = 'Diego'

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from PyQt4.QtGui import QMainWindow
import numpy as np
import itertools

#load gui
from braviz.interaction.qt_guis.anova import Ui_Anova_gui
from braviz.interaction.qt_guis.outcome_select import Ui_SelectOutcomeDialog
from braviz.interaction.qt_guis.nominal_details_frame import Ui_nominal_details_frame
from braviz.interaction.qt_guis.rational_details_frame import Ui_rational_details
from braviz.interaction.qt_guis.regressors_select import Ui_AddRegressorDialog
from braviz.interaction.qt_guis.interactions_dialog import Ui_InteractionsDiealog

import braviz.interaction.r_functions

import braviz.interaction.qt_models as braviz_models
from braviz.readAndFilter.tabular_data import get_connection, get_data_frame

import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import colorbrewer

from itertools import izip

from braviz.applications import mriMultSlicer
import multiprocessing

from mpltools import style
style.use('ggplot')

#TODO: Move all database access to read and filter

class VariableSelectDialog(QtGui.QDialog):
    """Implement common features for Oucome and Regressor Dialogs"""

    def __init__(self):
        """remember to call finish_ui_setup() after setting up ui"""
        super(VariableSelectDialog, self).__init__()
        self.conn = get_connection()
        self.var_name = None
        self.details_ui = None
        self.rational = {}
        self.matplot_widget = None
        self.data = tuple()
        self.model = None


    def update_plot(self, data):
        pass

    def update_right_side(self, var_name):

        #print "lalalalala: %s"%var_name
        self.ui.var_name.setText(var_name)
        self.ui.save_button.setEnabled(True)
        self.ui.var_type_combo.setEnabled(True)
        conn = self.conn
        cur = conn.cursor()
        cur.execute("SELECT is_real from variables where var_name=?", (var_name,))
        is_real = cur.fetchone()[0]
        self.var_name = var_name
        data = get_data_frame(self.var_name)
        self.data = data
        #update scatter
        self.update_plot(data)


        #update gui
        if is_real is not None:
            pass
        else:
            #print "unknown type, assuming real"
            is_real = True
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
            item = layout.itemAt(i)
            if isinstance(item, QtGui.QWidgetItem):
                item.widget().close()
            elif isinstance(item, QtGui.QSpacerItem):
                pass
            else:
                self.clearLayout(item.layout())
            layout.removeItem(item)
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
        self.details_ui.optimum_val.setValue(int((medi - mini) / (maxi - mini)))
        self.update_optimum_real_value()


    def update_optimum_real_value(self, perc_value=None):
        if perc_value is None:
            perc_value = self.details_ui.optimum_val.value()
        real_value = perc_value / 100 * (self.rational["max"] - self.rational["min"]) + self.rational["min"]
        self.details_ui.optimum_real_value.setNum(real_value)

    def create_real_details(self):
        #print "creating real details"
        details_ui = Ui_rational_details()
        details_ui.setupUi(self.ui.details_frame)
        self.details_ui = details_ui
        self.details_ui.optimum_val.valueChanged.connect(self.update_optimum_real_value)
        #try to read values from DB
        query = "SELECT * FROM ratio_meta WHERE var_idx = (SELECT var_idx FROM variables WHERE var_name=?)"
        cur = self.conn.cursor()
        cur.execute(query, (self.var_name,))
        db_values = cur.fetchone()
        if db_values is None:
            self.guess_max_min()
        else:
            self.rational["min"] = db_values[1]
            self.rational["max"] = db_values[2]
            self.rational["opt"] = db_values[3]
        self.set_real_controls()
        self.details_ui.optimum_val.valueChanged.connect(self.update_limits_in_plot)
        self.details_ui.minimum_val.valueChanged.connect(self.update_limits_in_plot)
        self.details_ui.maximum_val.valueChanged.connect(self.update_limits_in_plot)
        QtCore.QTimer.singleShot(0, self.update_limits_in_plot)

    def create_nominal_details(self):
        var_name = self.var_name
        #print "creating details"
        if self.model is None:
            self.model = braviz_models.NominalVariablesMeta(var_name)
        else:
            self.model.update_model(var_name)
        details_ui = Ui_nominal_details_frame()
        details_ui.setupUi(self.ui.details_frame)
        details_ui.labels_names_table.setModel(self.model)
        self.details_ui = details_ui
        QtCore.QTimer.singleShot(0, self.update_limits_in_plot)

    def finish_ui_setup(self):
        target = self.ui.plot_frame
        layout = QtGui.QVBoxLayout()
        self.matplot_widget = MatplotWidget(initial_message="Double click on variables\nto see plots")
        layout.addWidget(self.matplot_widget)
        target.setLayout(layout)
        self.ui.save_button.pressed.connect(self.save_meta_data)
        self.ui.var_type_combo.currentIndexChanged.connect(self.update_details)

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
        var_type = 0  #nominal should be 1
        if self.ui.var_type_combo.currentIndex() == 0:
            var_type = 1  #real should be 1

        #save variable type
        query = "UPDATE variables SET is_real = ? WHERE var_name = ?"
        self.conn.execute(query, (var_type, self.var_name))
        self.conn.commit()


        #save other values
        if var_type == 1:
            #real
            query = """INSERT OR REPLACE INTO ratio_meta
            VALUES(
            (SELECT var_idx FROM variables WHERE var_name = ?),
            ? , ? , ? );
            """
            try:
                self.conn.execute(query,
                                  (self.var_name, self.rational["min"],
                                   self.rational["max"], self.rational["opt"])
                )
            except (KeyError, ValueError):
                pass
            else:
                self.conn.commit()
        elif var_type == 0:
            self.model.save_into_db()


class OutcomeSelectDialog(VariableSelectDialog):
    def __init__(self, params_dict):
        super(OutcomeSelectDialog, self).__init__()
        self.ui = Ui_SelectOutcomeDialog()
        self.ui.setupUi(self)
        self.finish_ui_setup()

        self.params_dict = params_dict

        self.vars_list_model = braviz_models.VarListModel()
        self.ui.tableView.setModel(self.vars_list_model)
        self.ui.tableView.activated.connect(self.update_right_side)

        self.ui.select_button.pressed.connect(self.select_and_return)

    def update_right_side(self, var_name=None):
        curr_idx = self.ui.tableView.currentIndex()
        var_name = self.vars_list_model.data(curr_idx, QtCore.Qt.DisplayRole)
        self.ui.select_button.setEnabled(True)
        super(OutcomeSelectDialog, self).update_right_side(var_name)

    def update_plot(self, data):
        self.matplot_widget.compute_scatter(data.get_values(),
                                            x_lab=self.var_name, y_lab="jitter")


    def select_and_return(self, *args):
        self.save_meta_data()
        self.params_dict["selected_outcome"] = self.var_name
        self.done(self.Accepted)


class MatplotWidget(FigureCanvas):
    box_outlier_pick_signal = QtCore.pyqtSignal(float, float, tuple)
    scatter_pick_signal = QtCore.pyqtSignal(str, tuple)
    #TODO: instead of using blit create a @wrapper to save last render command to restore after drawing subjects

    def __init__(self, parent=None, dpi=100, initial_message=None):
        fig = Figure(figsize=(5, 5), dpi=dpi, tight_layout=True)
        self.fig = fig
        self.axes = fig.add_subplot(111)
        #self.axes.hold(False)
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.updateGeometry()
        palette = self.palette()
        fig.set_facecolor(palette.background().color().getRgbF()[0:3])
        self.initial_text(initial_message)
        self.back_fig = self.copy_from_bbox(self.axes.bbox)
        self.xlim = self.axes.get_xlim()
        #self.mpl_connect("button_press_event",self.generate_tooltip_event)
        self.mpl_connect("pick_event", self.generate_tooltip_event)
        self.setMouseTracking(True)
        self.mpl_connect('motion_notify_event', self.mouse_move_event_handler)
        self.x_order=None


    def initial_text(self, message):
        if message is None:
            message = "Welcome"
        self.axes.text(0.5, 0.5, message, horizontalalignment='center',
                       verticalalignment='center', fontsize=12)
        #Remove tick marks
        self.axes.tick_params('y', left='off',right='off', labelleft='off', labelright='off')
        self.axes.tick_params('x', top='off', bottom='off', labelbottom='off', labeltop='off')
        #Remove axes border
        for child in self.axes.get_children():
            if isinstance(child, matplotlib.spines.Spine):
                child.set_visible(False)
        #remove minor tick lines
        for line in self.axes.xaxis.get_ticklines(minor=True) + self.axes.yaxis.get_ticklines(minor=True):
            line.set_markersize(0)
        self.draw()
        self.x_order=None


    def compute_scatter(self, data, data2=None, x_lab=None, y_lab=None, colors=None, labels=None, urls=None):
        self.axes.clear()
        self.axes.tick_params('x', bottom='on', labelbottom='on', labeltop='off')
        self.axes.yaxis.set_label_position("right")
        if data2 is None:
            data2 = np.random.rand(len(data))
            self.axes.tick_params('y', left='off', labelleft='off', labelright='off')
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

        self.draw()
        self.back_fig = self.copy_from_bbox(self.axes.bbox)
        self.xlim = self.axes.get_xlim()
        self.x_order=None

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

    def make_box_plot(self, data, xlabel, ylabel, xticks_labels, ylims):

        #Sort data and labels according to median
        x_permutation=range(len(data))
        if xticks_labels is None:
            xticks_labels=range(len(data))
        data_labels=zip(data,xticks_labels,x_permutation)
        data_labels.sort(key=lambda x:np.median(x[0]))
        data,xticks_labels,x_permutation=zip(*data_labels)
        self.axes.clear()
        self.axes.tick_params('x', bottom='on', labelbottom='on', labeltop='off')
        self.axes.tick_params('y', left='off', labelleft='off', labelright='on', right="on")
        self.axes.yaxis.set_label_position("right")
        self.axes.set_ylim(auto=True)
        artists_dict = self.axes.boxplot(data, sym='gD')
        for a in artists_dict["fliers"]:
            a.set_picker(5)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
        if xticks_labels is not None:
            self.axes.get_xaxis().set_ticklabels(xticks_labels)
        yspan = ylims[1] - ylims[0]
        self.axes.set_ylim(ylims[0] - 0.1 * yspan, ylims[1] + 0.1 * yspan)

        self.draw()
        self.back_fig = self.copy_from_bbox(self.axes.bbox)
        self.x_order=x_permutation

    def make_linked_box_plot(self, data, xlabel, ylabel, xticks_labels, colors, top_labels, ylims):
        self.axes.clear()
        self.axes.tick_params('x', bottom='on', labelbottom='on', labeltop='off')
        self.axes.tick_params('y', left='off', labelleft='off', labelright='on', right="on")
        self.axes.yaxis.set_label_position("right")
        self.axes.set_ylim(auto=True)
        x_permutation=range(len(data[0]))
        data_join=[list(itertools.chain.from_iterable(l)) for l in zip(*data)]
        data_order=zip(data_join,x_permutation)
        data_order.sort(key=lambda x:np.median(x[0]))
        _,x_permutation=zip(*data_order)

        # self.x_order=x_permutation # at the end of method for consistency
        #sort data
        for k,l in enumerate(data):
            data[k]=[l[i] for i in x_permutation]
        xticks_labels=[xticks_labels[i] for i in x_permutation]

        for d_list, col, lbl in izip(data, colors, top_labels):
            artists_dict = self.axes.boxplot(d_list, sym='D', patch_artist=False)
            linex = []
            liney = []
            for b in artists_dict["boxes"]:
                b.set_visible(False)
            for m in artists_dict["medians"]:
                x = m.get_xdata()
                m.set_visible(False)
                xm = np.mean(x)
                ym = m.get_ydata()[0]
                linex.append(xm)
                liney.append(ym)
            for w in artists_dict["whiskers"]:
                w.set_alpha(0.5)
                w.set_c(col)
            for c in artists_dict["caps"]:
                c.set_c(col)
            for f in artists_dict["fliers"]:
                f.set_c(col)
                f.set_picker(5)

            #print zip(linex,liney)
            #print col
            self.axes.plot(linex, liney, 's-', markerfacecolor=col, color=col, label=lbl)

        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
        self.axes.get_xaxis().set_ticklabels(xticks_labels)
        self.axes.legend(numpoints=1, fancybox=True, fontsize="small", )
        self.axes.get_legend().draggable(True, update="loc")
        yspan = ylims[1] - ylims[0]
        self.axes.set_ylim(ylims[0] - 0.1 * yspan, ylims[1] + 0.1 * yspan)
        self.draw()
        self.back_fig = self.copy_from_bbox(self.axes.bbox)
        self.x_order=x_permutation

    def make_histogram(self, data, xlabel):
        self.axes.clear()
        self.axes.tick_params('x', bottom='on', labelbottom='on', labeltop='off')
        self.axes.tick_params('y', left='off', labelleft='off', labelright='on', right="on")
        self.axes.yaxis.set_label_position("right")
        self.axes.set_ylim(auto=True)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel("Frequency")
        self.axes.hist(data, color="#2ca25f",bins=20)
        self.draw()
        self.back_fig = self.copy_from_bbox(self.axes.bbox)
        self.x_order=None

    def add_subject_points(self, x_coords, y_coords, color=None, urls=None):
        #print "adding subjects"
        self.restore_region(self.back_fig)
        if self.x_order is not None:
            #labels go from 1 to n; permutation is from 0 to n-1
            x_coords=map(lambda k:self.x_order.index(int(k)-1)+1,x_coords)
        if color is None:
            color = "black"
        collection = self.axes.scatter(x_coords, y_coords, marker="o", s=120, edgecolors=color, urls=urls, picker=5)
        collection.set_facecolor('none')

        self.axes.draw_artist(collection)
        #for a in collection:
        #    self.axes.draw_artist(a)
        self.blit(self.axes.bbox)

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
            x,y=dx[ind],dy[ind]
            # correct x position from reordering
            if self.x_order is not None:
                x=self.x_order[int(x-1)]+1
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
    def __init__(self, outcome_var, regressors_model):
        super(RegressorSelectDialog, self).__init__()
        self.outcome_var = outcome_var
        self.ui = Ui_AddRegressorDialog()
        self.ui.setupUi(self)
        self.vars_model = braviz_models.VarAndGiniModel(outcome_var)
        self.ui.tableView.setModel(self.vars_model)
        self.finish_ui_setup()
        self.ui.tableView.activated.connect(self.update_right_side)
        self.ui.add_button.pressed.connect(self.add_regressor)
        self.regressors_table_model = regressors_model
        self.ui.current_regressors_table.setModel(self.regressors_table_model)
        self.ui.current_regressors_table.customContextMenuRequested.connect(self.show_context_menu)
        self.ui.done_button.pressed.connect(self.finish_close)

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
        #print selected_item


    def update_plot(self, data):
        regressor_data = data
        if self.outcome_var is not None:
            outcome_data = get_data_frame(self.outcome_var)
            self.matplot_widget.compute_scatter(regressor_data.get_values(), outcome_data.get_values(),
                                                x_lab=self.var_name, y_lab=self.outcome_var,
                                                urls=data.index.get_values())
        else:
            self.matplot_widget.compute_scatter(data.get_values())


    def finish_close(self):
        self.done(self.Accepted)


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
        self.ui.add_single_button.pressed.connect(self.add_single_term)
        self.ui.add_all_button.pressed.connect(self.add_all_combinations)

    def add_single_term(self):
        selected_indexes = self.ui.reg_view.selectedIndexes()
        selected_row_numbers = set(i.row() for i in selected_indexes)
        print selected_row_numbers
        self.full_model.add_interactor(selected_row_numbers)

    def add_all_combinations(self):
        rows = range(self.only_regs_model.rowCount())
        for r in xrange(2, len(rows) + 1):
            for i in itertools.combinations(rows, r):
                self.full_model.add_interactor(i)


class AnovaApp(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.outcome_var_name = None
        self.anova = None
        self.regressors_model = braviz_models.AnovaRegressorsModel()
        self.result_model = braviz_models.AnovaResultsModel()
        self.sample_model = braviz_models.sampleTree()
        self.plot = None
        self.plot_data_frame = None
        self.plot_x_var = None
        self.plot_z_var = None
        self.plot_color = None
        self.last_viewed_subject = None
        self.mri_viewer_pipe = None
        self.mri_viewer_process = None
        self.poll_timer = None
        self.ui = None
        self.setup_gui()


    def setup_gui(self):
        self.ui = Ui_Anova_gui()
        self.ui.setupUi(self)
        self.ui.outcome_sel.insertSeparator(1)
        self.ui.outcome_sel.setCurrentIndex(2)
        #self.ui.outcome_sel.currentIndexChanged.connect(self.dispatch_outcome_select)
        self.ui.outcome_sel.activated.connect(self.dispatch_outcome_select)
        self.ui.add_regressor_button.pressed.connect(self.launch_add_regressor_dialog)
        self.ui.reg_table.setModel(self.regressors_model)
        self.ui.reg_table.customContextMenuRequested.connect(self.launch_regressors_context_menu)
        self.ui.add_interaction_button.pressed.connect(self.dispatch_interactions_dialog)
        self.ui.calculate_button.pressed.connect(self.calculate_anova)
        self.ui.results_table.setModel(self.result_model)

        self.ui.matplot_layout = QtGui.QVBoxLayout()
        self.plot = MatplotWidget(initial_message="Welcome\n\nSelect Outcome and add Regressors to start")
        self.ui.matplot_layout.addWidget(self.plot)
        self.ui.plot_frame.setLayout(self.ui.matplot_layout)
        self.plot.box_outlier_pick_signal.connect(self.handle_box_outlier_pick)
        self.plot.scatter_pick_signal.connect(self.handle_scatter_pick)
        self.plot.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.plot.customContextMenuRequested.connect(self.subject_details_from_plot)
        self.ui.results_table.activated.connect(self.update_main_plot_from_results)
        self.ui.reg_table.activated.connect(self.update_main_plot_from_regressors)

        self.ui.sample_tree.setModel(self.sample_model)
        self.ui.sample_tree.activated.connect(self.add_subjects_to_plot)
        self.ui.sample_tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.sample_tree.customContextMenuRequested.connect(self.subject_details_from_tree)
        self.poll_timer = QtCore.QTimer(self)
        self.poll_timer.timeout.connect(self.poll_messages_from_mri_viewer)



    def dispatch_outcome_select(self):

        #print "outcome select %s / %s"%(self.ui.outcome_sel.currentIndex(),self.ui.outcome_sel.count()-1)
        if self.ui.outcome_sel.currentIndex() == self.ui.outcome_sel.count() - 1:
            #print "dispatching dialog"
            params = {}
            dialog = OutcomeSelectDialog(params)
            selection = dialog.exec_()
            if selection > 0:
                self.set_outcome_var_type(params["selected_outcome"])
            else:
                self.set_outcome_var_type(None)
        else:
            self.set_outcome_var_type(self.ui.outcome_sel.itemText(self.ui.outcome_sel.currentIndex()))

    def dispatch_interactions_dialog(self):
        interaction_dialog = InteractionSelectDialog(self.regressors_model)
        interaction_dialog.exec_()
        self.regressors_model.show_regressors(True)
        try:
            ints = self.regressors_model.get_interactions()[-1]
        except (KeyError, IndexError):
            return
        if type(ints) == str or type(ints) == unicode:
            self.update_main_plot(ints)
        elif len(ints) > 0:
            self.update_main_plot(ints[-1])

    def set_outcome_var_type(self, new_bar):
        if new_bar is None:
            var_type_text = "Type"
            self.ui.outcome_type.setText(var_type_text)
            self.outcome_var_name = None
            #self.ui.outcome_sel.setCurrentIndex(self.ui.outcome_sel.count()-1)
            return
        new_bar = unicode(new_bar)
        if new_bar == self.outcome_var_name:
            return
        print "succesfully selected %s" % new_bar
        index = self.ui.outcome_sel.findText(new_bar)
        if index < 0:
            self.ui.outcome_sel.setCurrentIndex(index)
            self.ui.outcome_sel.insertItem(0, new_bar)
            index = 0
            pass
        self.outcome_var_name = new_bar
        self.ui.outcome_sel.setCurrentIndex(index)
        conn = get_connection()
        try:
            var_is_real = conn.execute("SELECT is_real FROM variables WHERE var_name = ? ;", (new_bar,)).fetchone()[0]
        except TypeError:
            var_type_text = "Type"
        else:
            var_type_text = "Real" if var_is_real else "Nominal"
        self.ui.outcome_type.setText(var_type_text)
        self.check_if_ready()

    def launch_add_regressor_dialog(self):
        reg_dialog = RegressorSelectDialog(self.outcome_var_name, self.regressors_model)
        result = reg_dialog.exec_()
        if self.regressors_model.rowCount() > 0:
            regn = self.regressors_model.get_regressors()[-1]
            self.update_main_plot(regn)
        self.check_if_ready()

    def check_if_ready(self):
        if (self.outcome_var_name is not None) and (self.regressors_model.rowCount() > 0):
            self.ui.calculate_button.setEnabled(True)
        else:
            self.ui.calculate_button.setEnabled(False)

    def launch_regressors_context_menu(self, pos):
        global_pos = self.ui.reg_table.mapToGlobal(pos)
        selection = self.ui.reg_table.currentIndex()
        remove_action = QtGui.QAction("Remove", None)
        menu = QtGui.QMenu()
        menu.addAction(remove_action)

        def remove_item(*args):
            self.regressors_model.removeRows(selection.row(), 1)

        remove_action.triggered.connect(remove_item)
        menu.addAction(remove_action)
        selected_item = menu.exec_(global_pos)

    def update_sample_info(self):
        #TODO: Allow choosing different sub-samples
        pass

    def calculate_anova(self):

        try:
            self.anova = braviz.interaction.r_functions.calculate_anova(self.outcome_var_name,
                                                                        self.regressors_model.get_data_frame(),
                                                                        self.regressors_model.get_interactors_dict())
        except Exception as e:
            msg = QtGui.QMessageBox()
            msg.setText(str(e.message))
            msg.setIcon(msg.Warning)
            msg.setWindowTitle("Anova Error")
            msg.exec_()
            #raise
        else:
            self.result_model = braviz_models.AnovaResultsModel(*self.anova)
            self.ui.results_table.setModel(self.result_model)
            self.update_main_plot("Residuals")

    def update_main_plot_from_results(self, index):
        row = index.row()
        var_name_index = self.result_model.index(row, 0)
        var_name = unicode(self.result_model.data(var_name_index, QtCore.Qt.DisplayRole))
        self.update_main_plot(var_name)

    def update_main_plot_from_regressors(self, index):
        row = index.row()
        var_name_index = self.regressors_model.index(row, 0)
        var_name = unicode(self.regressors_model.data(var_name_index, QtCore.Qt.DisplayRole))
        self.update_main_plot(var_name)

    def update_main_plot(self, var_name):
        self.plot_x_var = None
        self.plot_data_frame = None
        self.plot_z_var = None
        self.plot_color = None
        if self.outcome_var_name is None:
            return
        if var_name == "Residuals":
            residuals = self.result_model.residuals
            self.plot.make_histogram(residuals, "Residuals")
            pass
        elif var_name == "(Intercept)":
            data = get_data_frame(self.outcome_var_name)
            self.plot_data_frame = data
            data_values = data[self.outcome_var_name].get_values()

            conn = get_connection()
            #get outcome min and max values
            cur = conn.execute("SELECT min_val, max_val FROM ratio_meta NATURAL JOIN variables WHERE var_name=?",
                               (self.outcome_var_name,))
            ylims = cur.fetchone()
            self.plot.make_box_plot(data_values, "(Intercept)", self.outcome_var_name,
                                    None, ylims)
            self.plot.add_intercept_line(self.result_model.intercept)

            pass
        else:
            if ":" in var_name:
                factors = var_name.split(":")
                self.two_factors_plot(factors[:2])
            elif "*" in var_name:
                factors = var_name.split("*")
                self.two_factors_plot(factors[:2])
            else:
                self.one_reg_plot(var_name)

    def two_factors_plot(self, factors_list):
        nominal_factors = []
        real_factors = []
        conn = get_connection()
        #classify factors
        for f in factors_list:
            is_real = conn.execute("SELECT is_real FROM variables WHERE var_name=?", (f,))
            is_real = is_real.fetchone()[0]
            if is_real == 0:
                nominal_factors.append(f)
            else:
                real_factors.append(f)
        #print nominal_factors
        #print real_factors
        if len(real_factors) == 1:

            labels = conn.execute(
                "SELECT nom_meta.label, nom_meta.name FROM variables NATURAL JOIN nom_meta WHERE var_name = ?",
                (nominal_factors[0],))
            top_labels_dict = dict(labels.fetchall())
            colors = colorbrewer.Dark2[max(len(top_labels_dict), 3)]
            #print top_labels_strings
            if len(top_labels_dict) == 2:
                colors = colors[:2]
            colors = [map(lambda x: x / 255, c) for c in colors]
            colors_dict = dict(izip(top_labels_dict.iterkeys(), colors))
            self.plot_color = colors_dict
            self.plot_z_var = nominal_factors[0]
            #Get Data
            data = get_data_frame([real_factors[0], nominal_factors[0], self.outcome_var_name])
            self.plot_data_frame = data
            datax = []
            datay = []
            colors = []
            labels = []
            urls = []
            for k, v in top_labels_dict.iteritems():
                labels.append(v)
                colors.append(colors_dict[k])
                datay.append(data[self.outcome_var_name][data[nominal_factors[0]] == k].get_values())
                datax.append(data[real_factors[0]][data[nominal_factors[0]] == k].get_values())
                urls.append(data[self.outcome_var_name][data[nominal_factors[0]] == k].index.get_values())
            #print datax
            self.plot_x_var = real_factors[0]

            self.plot.compute_scatter(datax, datay, real_factors[0], self.outcome_var_name, colors, labels, urls=urls)


        elif len(real_factors) == 2:
            print "Not yet implemented"
        else:
            #find number of levels for nominal
            nlevels = {}
            for f in nominal_factors:
                n = conn.execute("SELECT count(*) FROM variables NATURAL JOIN nom_meta WHERE var_name=?", (f,))
                nlevels[f] = n.fetchone()[0]
            #print nlevels
            nominal_factors.sort(key=nlevels.get, reverse=True)
            #print nominal_factors
            data = get_data_frame(nominal_factors + [self.outcome_var_name])
            self.plot_data_frame = data
            levels_second_factor = set(data[nominal_factors[1]].get_values())
            levels_first_factor = set(data[nominal_factors[0]].get_values())
            data_lists_top = []
            for i in levels_second_factor:
                data_list = []
                for j in levels_first_factor:
                    data_col = data[self.outcome_var_name][(data[nominal_factors[1]] == i) &
                                                           (data[nominal_factors[0]] == j)].get_values()
                    data_list.append(data_col)
                data_lists_top.append(data_list)
            #print data_lists_top
            labels = conn.execute(
                "SELECT nom_meta.label, nom_meta.name FROM variables NATURAL JOIN nom_meta WHERE var_name = ?",
                (nominal_factors[0],))
            labels_dict = dict(labels.fetchall())
            labels_strings = [labels_dict[i] for i in levels_first_factor]
            labels = conn.execute(
                "SELECT nom_meta.label, nom_meta.name FROM variables NATURAL JOIN nom_meta WHERE var_name = ?",
                (nominal_factors[1],))
            top_labels_dict = dict(labels.fetchall())
            top_labels_strings = [top_labels_dict[i] for i in levels_second_factor]
            colors = colorbrewer.Dark2[max(len(levels_second_factor), 3)]
            #print top_labels_strings
            if len(levels_second_factor) == 2:
                colors = colors[:2]
            colors = [map(lambda x: x / 255, c) for c in colors]
            self.plot_color = dict(izip(levels_second_factor, colors))
            self.plot_z_var = nominal_factors[1]
            #print colors
            #get ylims
            cur = conn.execute("SELECT min_val , max_val FROM variables NATURAL JOIN ratio_meta WHERE var_name=?",
                               (self.outcome_var_name,))
            miny, maxy = cur.fetchone()
            if miny is None or maxy is None:
                raise Exception("Incosistency in DB")

            self.plot_x_var = nominal_factors[0]
            self.plot.make_linked_box_plot(data_lists_top, nominal_factors[0], self.outcome_var_name, labels_strings,
                                           colors, top_labels_strings, ylims=(miny, maxy))


    def one_reg_plot(self, var_name):
        #find if variable is nominal
        conn = get_connection()
        is_reg_real = conn.execute("SELECT is_real FROM variables WHERE var_name=?", (var_name,))
        is_reg_real = is_reg_real.fetchone()[0]
        #get outcome min and max values
        cur = conn.execute("SELECT min_val, max_val FROM ratio_meta NATURAL JOIN variables WHERE var_name=?",
                           (self.outcome_var_name,))
        #TODO This has to be updatede when implementing logistic regression
        miny, maxy = cur.fetchone()
        self.plot_x_var = var_name
        if is_reg_real == 0:
            #is nominal
            #create whisker plot
            labels = conn.execute(
                "SELECT nom_meta.label, nom_meta.name FROM variables NATURAL JOIN nom_meta WHERE var_name = ?",
                (var_name,))
            labels_dict = dict(labels.fetchall())
            #print labels_dict
            #get data from
            data = get_data_frame([self.outcome_var_name, var_name])
            self.plot_data_frame = data
            label_nums = set(data[var_name])
            data_list = []
            ticks = []
            for i in label_nums:
                data_col = data[self.outcome_var_name][data[var_name] == i]
                data_list.append(data_col.get_values())
                ticks.append(labels_dict.get(i, str(i)))
            #print data_list
            self.plot.make_box_plot(data_list, var_name, self.outcome_var_name, ticks, (miny, maxy))

        else:
            #is real
            #create scatter plot
            data = get_data_frame([self.outcome_var_name, var_name])
            self.plot_data_frame = data
            self.plot.compute_scatter(data[var_name].get_values(),
                                      data[self.outcome_var_name].get_values(),
                                      var_name,
                                      self.outcome_var_name, urls=data.index.get_values())

    def add_subjects_to_plot(self, index=None,subject_ids=None):
        #find selected subjects
        if subject_ids is None:
            selection = self.ui.sample_tree.currentIndex()
            leafs = self.sample_model.get_leafs(selection)
            subject_ids = map(int, leafs)

        #get data
        #print subject_ids
        if self.plot_data_frame is None:
            return
        y_data = self.plot_data_frame[self.outcome_var_name][subject_ids].get_values()
        subject_ids = self.plot_data_frame[self.outcome_var_name][subject_ids].index.get_values()
        if self.plot_x_var is None:
            x_data = np.ones(y_data.shape)
        else:
            x_data = self.plot_data_frame[self.plot_x_var][subject_ids].get_values()
        colors = None
        if self.plot_z_var is not None and self.plot_color is not None:
            z_data = self.plot_data_frame[self.plot_z_var][subject_ids].get_values()
            colors = [self.plot_color[i] for i in z_data]
        self.plot.add_subject_points(x_data, y_data, colors, urls=subject_ids)

    def poll_messages_from_mri_viewer(self):
        #print "polling"
        if self.mri_viewer_process is None or (not self.mri_viewer_process.is_alive()):
            #stop timer
            self.poll_timer.stop()
        if self.mri_viewer_pipe.poll():
            message = self.mri_viewer_pipe.recv()
            subj = message.get('subject')
            if subj is not None:
                print "showing subject %s"%subj
                self.add_subjects_to_plot(subject_ids=[int(subj)])


    def handle_box_outlier_pick(self, x, y, position):
        #print "received signal"
        #print x_l,y_l
        if self.plot_data_frame is not None:
            #identify subject
            df = self.plot_data_frame
            subj = df[(df[self.plot_x_var] == x) & (df[self.outcome_var_name] == y)].index
            #print subj[0]
            message = "Outlier: %s" % subj[0]
            self.last_viewed_subject = subj[0]
            QtCore.QTimer.singleShot(2000, self.clear_last_viewed_subject)
            QtGui.QToolTip.showText(self.plot.mapToGlobal(QtCore.QPoint(*position)), message, self.plot)

    def handle_scatter_pick(self, subj, position):
        message = "Subject: %s" % subj
        QtGui.QToolTip.showText(self.plot.mapToGlobal(QtCore.QPoint(*position)), message, self.plot)
        self.last_viewed_subject = subj
        QtCore.QTimer.singleShot(2000, self.clear_last_viewed_subject)

    def create_view_details_context_menu(self, global_pos, subject=None):
        #TODO: Open images of a given subject
        if subject is None:
            subject = self.last_viewed_subject
            if subject is None:
                return

        def show_MRI(*args):
            print "launching MRI viewer"
            self.change_subject_in_mri_viewer(subject)

        launch_mri_action = QtGui.QAction("Show subject %s MRI" % subject, None)
        menu = QtGui.QMenu("Subject %s" % subject)
        menu.addAction(launch_mri_action)
        launch_mri_action.triggered.connect(show_MRI)
        menu.addAction(launch_mri_action)
        menu.exec_(global_pos)

    def subject_details_from_plot(self, pos):
        #print "context menu"
        #print pos
        global_pos = self.plot.mapToGlobal(pos)
        self.create_view_details_context_menu(global_pos)

    def subject_details_from_tree(self, pos):
        global_pos = self.ui.sample_tree.mapToGlobal(pos)
        selection = self.ui.sample_tree.currentIndex()
        selection = self.sample_model.index(selection.row(), 0, selection.parent())
        #check if it is a leaf
        if self.sample_model.hasChildren(selection) is True:
            return
        else:
            #print "this is a leaf"
            subject = self.sample_model.data(selection, QtCore.Qt.DisplayRole)
            #print subject
            self.create_view_details_context_menu(global_pos, subject)

    def clear_last_viewed_subject(self):
        self.last_viewed_subject = None

    def launch_mri_viewer(self):
        print "creating new mri viewer"
        self.mri_viewer_pipe, pipe_mri_side = multiprocessing.Pipe()
        self.mri_viewer_process = multiprocessing.Process(target=mriMultSlicer.launch_new, args=(pipe_mri_side,))
        self.mri_viewer_process.start()
        self.poll_timer.start(200)

    def change_subject_in_mri_viewer(self, subj):
        if (self.mri_viewer_process is None) or (not self.mri_viewer_process.is_alive()):
            self.launch_mri_viewer()
        if self.mri_viewer_pipe is not None:
            self.mri_viewer_pipe.send({'subject': str(subj), 'lift': True})

    def closeEvent(self, *args, **kwargs):
        if self.mri_viewer_process is not None:
            self.mri_viewer_process.terminate()
        print "ciao"


if __name__ == '__main__':
    import sys

    app = QtGui.QApplication(sys.argv)
    main_window = AnovaApp()
    main_window.show()
    app.exec_()
