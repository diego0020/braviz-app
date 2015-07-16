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


"""
Explore correlations between two variables
"""

from __future__ import print_function
from braviz.utilities import set_pyqt_api_2

set_pyqt_api_2()

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import matplotlib

import braviz.readAndFilter.tabular_data as tab_data
from braviz.interaction.qt_models import VarListModel
__author__ = 'Diego'

matplotlib.use("Qt4Agg")
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

from braviz.interaction.qt_guis.correlations import Ui_correlation_app
from braviz.interaction.connection import MessageClient
from interaction.qt_widgets import SampleManager

import numpy as np
import seaborn as sns
import scipy.stats
import pandas as pd
from functools import partial


class CorrelationMatrixFigure(FigureCanvas):
    SquareSelected = QtCore.pyqtSignal(pd.DataFrame)

    def __init__(self):
        self.f, self.ax = plt.subplots(figsize=(9, 9))
        plt.tight_layout()
        super(CorrelationMatrixFigure, self).__init__(self.f)
        palette = self.palette()
        self.f.set_facecolor(palette.background().color().getRgbF()[0:3])
        self.df = None
        self.full_df = None
        self.corr = None
        self.sample = tab_data.get_subjects()
        self.last_square = None;
        self.cmap = sns.blend_palette(["#00008B", "#6A5ACD", "#F0F8FF",
                                       "#FFE6F8", "#C71585", "#8B0000"], as_cmap=True)
        self.mpl_connect("motion_notify_event", self.get_tooltip_message)
        self.mpl_connect("button_press_event", self.square_clicked)
        self.on_draw()

    def on_draw(self):
        plt.sca(self.ax)
        plt.clf()
        self.ax = plt.axes()
        if self.df is None:
            self.ax.tick_params(
                'y', left='off', right='off', labelleft='off', labelright='off')
            self.ax.tick_params(
                'x', top='off', bottom='off', labelbottom='off', labeltop='off')
            message = "Select two or more variables from list"
            self.ax.text(0.5, 0.5, message, horizontalalignment='center',
                         verticalalignment='center', fontsize=16)
        else:
            self.ax.tick_params(
                'y', left='off', right='off', labelleft='on', labelright='off')
            self.ax.tick_params(
                'x', top='off', bottom='off', labelbottom='on', labeltop='off')
            plt.sca(self.ax)
            sns.corrplot(self.df, annot=False, sig_stars=True, cmap_range="full",
                         diag_names=False, sig_corr=False, cmap=self.cmap, ax=self.ax, cbar=True)
        plt.tight_layout()
        self.draw()

    def set_variables(self, vars_list):
        # print vars_list
        if self.last_square is not None:
            x_name, y_name = self.last_square
            if x_name not in vars_list or y_name not in vars_list:
                self.last_square = None;
        if len(vars_list) < 2:
            self.df = None
            self.corr = None
        else:
            self.full_df = tab_data.get_data_frame_by_name(vars_list)
            self.df = self.full_df.loc[self.sample].copy()
            self.corr = self.df.corr()
        self.on_draw()

    def get_tooltip_message(self, event):
        #QtGui.QToolTip.hideText()
        if event.inaxes == self.ax and self.df is not None:
            x_int, y_int = int(round(event.xdata)), int(round(event.ydata))
            if y_int <= x_int:
                return
            x_name, y_name = self.df.columns[x_int], self.df.columns[y_int]
            r = self.corr.loc[x_name, y_name]
            message = "%s v.s. %s: r = %.2f" % (x_name, y_name, r)
            _, height = self.get_width_height()
            point = QtCore.QPoint(event.x, height - event.y)

            g_point = self.mapToGlobal(point)
            QtGui.QToolTip.showText(g_point, message)

    def square_clicked(self, event):
        if event.inaxes == self.ax and self.df is not None:
            x_int, y_int = int(round(event.xdata)), int(round(event.ydata))
            if y_int <= x_int:
                return
            x_name, y_name = self.df.columns[x_int], self.df.columns[y_int]
            df2 = self.df[[x_name, y_name]]
            self.SquareSelected.emit(df2)
            self.last_square = x_name, y_name

    def set_sample(self, new_sample):
        self.sample = list(new_sample)
        self.df = self.full_df.loc[self.sample].copy()
        self.on_draw()
        if self.last_square is not None:
            x_name, y_name = self.last_square
            df2 = self.df[[x_name, y_name]]
            self.SquareSelected.emit(df2)


class RegFigure(FigureCanvas):
    hidden_points_change = QtCore.pyqtSignal(int)

    def __init__(self, message_client):
        self.f, self.ax = plt.subplots(figsize=(9, 9))
        super(RegFigure, self).__init__(self.f)
        palette = self.palette()
        self.f.set_facecolor(palette.background().color().getRgbF()[0:3])
        self.draw_initial_message()
        self.mpl_connect("motion_notify_event", self.motion_to_pick)
        self.mpl_connect("pick_event", self.handle_pick_event)
        self.hidden_subjs = set()
        self.df = None
        self.df2 = None
        self.dfh = None
        self.scatter_h_artist = None
        self.limits = None
        self._message_client = message_client

    def clear_hidden_subjects(self):
        self.hidden_subjs.clear()
        if self.df is not None:
            self.re_draw_reg()
        self.hidden_points_change.emit(len(self.hidden_subjs))

    def draw_initial_message(self):
        self.ax.clear()
        self.ax.tick_params(
            'y', left='off', right='off', labelleft='off', labelright='off')
        self.ax.tick_params(
            'x', top='off', bottom='off', labelbottom='off', labeltop='off')
        message = "Click in the correlation matrix"
        self.ax.text(0.5, 0.5, message, horizontalalignment='center',
                     verticalalignment='center', fontsize=16)
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        plt.sca(self.ax)
        plt.tight_layout()
        self.draw()

    def draw_reg(self, df):
        assert df.shape[1] == 2
        # print df
        self.ax.clear()
        self.ax.tick_params(
            'y', left='on', right='off', labelleft='off', labelright='on')
        self.ax.tick_params(
            'x', top='off', bottom='on', labelbottom='on', labeltop='off')
        plt.sca(self.ax)
        df = df.dropna()
        self.df = df.copy()
        plt.tight_layout()
        self.limits = None
        self.ax.set_xlim(auto=True)
        self.ax.set_ylim(auto=True)
        self.re_draw_reg()

    def re_draw_reg(self):
        self.ax.clear()
        i2 = [i for i in self.df.index if i not in self.hidden_subjs]
        df2 = self.df.loc[i2]
        self.df2 = df2
        y_name, x_name = df2.columns
        x_vals = df2[x_name].get_values()
        y_vals = df2[y_name].get_values()
        sns.regplot(
            x_name, y_name, df2, ax=self.ax, scatter_kws={"picker": 5, })
        mat = np.column_stack((x_vals, y_vals))
        mat = mat[np.all(np.isfinite(mat), 1), ]
        m, b, r, p, e = scipy.stats.linregress(mat)
        plot_title = "r=%.2f       p=%.5g" % (r, p)
        self.ax.set_title(plot_title)
        # print e
        self.ax.set_title(plot_title)

        if self.limits is not None:
            xl, yl = self.limits
            self.ax.set_xlim(xl[0], xl[1], auto=False)
            self.ax.set_ylim(yl[0], yl[1], auto=False)
        else:
            self.limits = (self.ax.get_xlim(), self.ax.get_ylim())
        ih = [i for i in self.df.index if i in self.hidden_subjs]
        dfh = self.df.loc[ih]
        self.dfh = dfh
        current_color = matplotlib.rcParams["axes.color_cycle"][0]
        self.scatter_h_artist = self.ax.scatter(dfh[x_name].get_values(), dfh[y_name].get_values(),
                                                edgecolors=current_color, facecolors="None", urls=ih, picker=2)
        plt.tight_layout()
        self.draw()

    def motion_to_pick(self, event):
        self.ax.pick(event)

    def handle_pick_event(self, event):
        #QtGui.QToolTip.hideText()
        mouse_event = event.mouseevent
        if isinstance(event.artist, matplotlib.collections.PathCollection):
            event_index = event.ind
            message_pieces = []
            # if the pick involves different subjects
            if event.artist == self.scatter_h_artist:
                dfp = self.dfh
            else:
                dfp = self.df2
            for i in event_index:
                datum = dfp.iloc[[i]]
                message = "Subject %s\n%s : %g\n%s : %g" %\
                    (datum.index[0],
                     datum.columns[0], datum.iloc[0, 0],
                     datum.columns[1], datum.iloc[0, 1],)
                message_pieces.append(message)
            big_message = "\n\n".join(message_pieces)
            _, height = self.get_width_height()
            point = QtCore.QPoint(
                event.mouseevent.x, height - event.mouseevent.y)
            g_point = self.mapToGlobal(point)
            QtGui.QToolTip.showText(g_point, big_message)
            if mouse_event.button == 1:
                if len(event_index) == 1:
                    name = datum.index[0]
                    if event.artist == self.scatter_h_artist:
                        print("recovering %s" % name)
                        self.hidden_subjs.remove(name)
                    else:
                        print("hiding %s" % name)
                        self.hidden_subjs.add(name)
                    self.hidden_points_change.emit(len(self.hidden_subjs))
                    self.re_draw_reg()
            elif mouse_event.button == 3 and mouse_event.name == 'button_press_event':
                context_menu = QtGui.QMenu()
                for i in event_index[:10]:
                    subj = dfp.index[i]
                    action = QtGui.QAction("Show %s in other viewers"%subj, context_menu)
                    action.triggered.connect(partial(self.send_subject_message,subj))
                    context_menu.addAction(action)
                context_menu.exec_(g_point)

    def send_subject_message(self, subj):
        self._message_client.send_message({"subject": subj})
        self.highlight_subject(subj)

    def selection_changed(self, selection):
        if self.df is None:
            return
        sel_set = set(selection)
        current_vars = set(self.df.columns)
        if not current_vars <= sel_set:
            # current vars are not contained in current selection
            self.df = None
            self.draw_initial_message()

    def highlight_subject(self, subj):
        if self.df is None:
            return
        self.re_draw_reg()
        try:
            subj_data = self.df.loc[int(subj)]
        except KeyError:
            return
        y,x = subj_data[0], subj_data[1]
        plt.scatter([x],[y],marker="o",s=300, linewidths=4, edgecolors="black", c="none")
        self.draw()
        print("highlighting %s"%subj)


class CorrelationsApp(QtGui.QMainWindow):

    def __init__(self, server_broadcast = None, server_receive = None):
        super(CorrelationsApp, self).__init__()
        self.ui = None
        self._message_client = MessageClient(server_broadcast, server_receive)
        self._message_client.message_received.connect(self.receive_message)
        self.sample_manager = SampleManager(parent=self, message_client=self._message_client)
        self.cor_mat = CorrelationMatrixFigure()
        self.reg_plot = RegFigure(self._message_client)
        self.vars_model = VarListModel(checkeable=True)
        self.setup_ui()

    def setup_ui(self):
        self.ui = Ui_correlation_app()
        self.ui.setupUi(self)
        self.ui.variables_list.setModel(self.vars_model)

        self.ui.cor_layout = QtGui.QHBoxLayout()
        self.ui.cor_mat_frame.setLayout(self.ui.cor_layout)
        self.ui.cor_layout.addWidget(self.cor_mat)
        self.vars_model.CheckedChanged.connect(self.cor_mat.set_variables)
        self.vars_model.CheckedChanged.connect(self.reg_plot.selection_changed)

        self.ui.reg_layout = QtGui.QHBoxLayout()
        self.ui.reg_frame.setLayout(self.ui.reg_layout)
        self.ui.reg_layout.addWidget(self.reg_plot)
        self.ui.restore_points.clicked.connect(self.reg_plot.clear_hidden_subjects)
        self.reg_plot.hidden_points_change.connect(lambda i: self.ui.ignored_label.setText(str(i)))

        self.ui.actionSave_Matrix.triggered.connect(self.save_matrix)
        self.ui.actionSave_Scatter.triggered.connect(self.save_reg)
        self.ui.search_box.returnPressed.connect(self.filter_list)
        self.cor_mat.SquareSelected.connect(self.reg_plot.draw_reg)

        #sample
        self.ui.actionLoad_sample.triggered.connect(self.sample_manager.load_sample)
        self.ui.actionModify_sample.triggered.connect(self.sample_manager.modify_sample)
        self.ui.actionSend_sample.triggered.connect(self.sample_manager.send_sample)
        self.ui.actionRestore_sample.triggered.connect(self.reg_plot.clear_hidden_subjects)
        self.sample_manager.configure_sample_policy_menu(self.ui.menuAccept_samples)

    def receive_message(self, msg):
        subj = msg.get("subject")
        if subj is not None:
            self.reg_plot.highlight_subject(subj)
        if "sample" in msg:
            self.handle_sample_message(msg)

    def filter_list(self):
        mask = "%%%s%%" % self.ui.search_box.text()
        self.vars_model.update_list(mask)


    def update_sample(self, new_sample):
        self.reg_plot.clear_hidden_subjects()
        self.cor_mat.set_sample(new_sample)


    def save_matrix(self):
        filename = unicode(QtGui.QFileDialog.getSaveFileName(self,
                                                             "Save Matrix", ".", "PDF (*.pdf);;PNG (*.png);;svg (*.svg)"))
        self.cor_mat.f.savefig(filename)

    def save_reg(self):
        filename = unicode(QtGui.QFileDialog.getSaveFileName(self,
                                                             "Save Scatter", ".", "PDF (*.pdf);;PNG (*.png);;svg (*.svg)"))
        self.reg_plot.f.savefig(filename)

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication([])
    if len(sys.argv) >= 4:
        scenario = sys.argv[1]
        server_broadcast, server_receive = sys.argv[2], sys.argv[3]
    else:
        server_broadcast, server_receive = None, None
    main_window = CorrelationsApp(server_broadcast, server_receive)
    main_window.show()
    app.exec_()
