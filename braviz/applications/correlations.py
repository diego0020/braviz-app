"""
Exploring correlations between two variables
"""
__author__ = 'Diego'

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import matplotlib

import braviz.readAndFilter.tabular_data as tab_data
from braviz.interaction.qt_models import VarListModel


matplotlib.use("Qt4Agg")
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

from braviz.interaction.qt_guis.correlations import Ui_correlation_app
from braviz.interaction import qt_sample_select_dialog

import numpy as np
import seaborn as sns
import scipy.stats
import pandas as pd

class CorrelationMatrixFigure(FigureCanvas):
    SquareSelected = QtCore.pyqtSignal(pd.DataFrame)

    def __init__(self):
        self.f, self.ax = plt.subplots(figsize=(9, 9))
        plt.tight_layout()
        super(CorrelationMatrixFigure, self).__init__(self.f)
        palette = self.palette()
        self.f.set_facecolor(palette.background().color().getRgbF()[0:3])
        self.df = None
        self.corr = None
        self.sample = tab_data.get_subjects()
        self.cmap = sns.blend_palette(["#00008B", "#6A5ACD", "#F0F8FF",
                                       "#FFE6F8", "#C71585", "#8B0000"], as_cmap=True)
        self.mpl_connect("motion_notify_event", self.get_tooltip_message)
        self.mpl_connect("button_press_event",self.square_clicked)
        self.on_draw()

    def on_draw(self):
        plt.sca(self.ax)
        plt.clf()
        self.ax = plt.axes()
        if self.df is None:
            message = "Select two or more variables from list"
            self.ax.text(0.5, 0.5, message, horizontalalignment='center',
                         verticalalignment='center', fontsize=16)
        else:
            plt.sca(self.ax)
            sns.corrplot(self.df, annot=False, sig_stars=True, cmap_range="full",
                         diag_names=False, sig_corr=False, cmap=self.cmap, ax=self.ax, cbar=True)
        plt.tight_layout()
        self.draw()

    def set_variables(self, vars_list):
        #print vars_list
        if len(vars_list) < 2:
            self.df = None
            self.corr = None
        else:
            self.df = tab_data.get_data_frame_by_name(vars_list)
            self.df = self.df.loc[self.sample].copy()
            self.corr = self.df.corr()
        self.on_draw()

    def get_tooltip_message(self, event):
        QtGui.QToolTip.hideText()
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

    def square_clicked(self,event):
        if event.inaxes == self.ax and self.df is not None:
            x_int , y_int = int(round(event.xdata)) , int(round(event.ydata))
            if y_int<=x_int:
                return
            x_name,y_name = self.df.columns[x_int],self.df.columns[y_int]
            df2 = self.df[[x_name,y_name]]
            self.SquareSelected.emit(df2)
    def set_sample(self,new_sample):
        self.sample = list(new_sample)
        self.df = self.df.loc[self.sample].copy()
        self.on_draw()


class RegFigure(FigureCanvas):
    def __init__(self):
        self.f, self.ax = plt.subplots(figsize=(9, 9))
        super(RegFigure, self).__init__(self.f)
        palette = self.palette()
        self.f.set_facecolor(palette.background().color().getRgbF()[0:3])
        self.draw_initial_message()
        self.mpl_connect("motion_notify_event",self.motion_to_pick)
        self.mpl_connect("pick_event",self.draw_tooltip)
        self.df = None


    def draw_initial_message(self):
        self.ax.clear()
        message = "Click in the correlation matrix"
        self.ax.text(0.5, 0.5, message, horizontalalignment='center',
                     verticalalignment='center', fontsize=16)
        self.ax.set_xlim(0,1)
        self.ax.set_ylim(0,1)
        plt.sca(self.ax)
        plt.tight_layout()
        self.draw()
    def draw_reg(self,df):
        assert df.shape[1] == 2
        #print df
        self.ax.clear()
        plt.sca(self.ax)
        y_name,x_name = df.columns
        x_vals=df[x_name].get_values()
        y_vals=df[y_name].get_values()
        plt.sca(self.ax)
        df = df.dropna()
        self.df = df.copy()
        sns.regplot(y_name,x_name,df,ax=self.ax,scatter_kws={"picker":5,})
        mat = np.column_stack((x_vals,y_vals))
        mat = mat[np.all(np.isfinite(mat),1),]
        m,b,r,p,e = scipy.stats.linregress(mat)
        #print e
        plot_title = "r=%.2f\np=%.5g"%(r,p)
        self.ax.set_title(plot_title)
        plt.tight_layout()
        self.draw()

    def motion_to_pick(self,event):
        self.ax.pick(event)

    def draw_tooltip(self,event):
        QtGui.QToolTip.hideText()
        if isinstance(event.artist,matplotlib.collections.PathCollection):
            index = event.ind
            datum = self.df.iloc[index]
            message = "Subject %s\n%s : %g\n%s : %g"%\
                      (datum.index[0],
                       datum.columns[0],datum.iloc[0,0],
                       datum.columns[1],datum.iloc[0,1],)
            _,height = self.get_width_height()
            point = QtCore.QPoint(event.mouseevent.x,height-event.mouseevent.y)
            g_point = self.mapToGlobal(point)
            QtGui.QToolTip.showText(g_point,message)


class CorrelationsApp(QtGui.QMainWindow):
    def __init__(self):
        super(CorrelationsApp, self).__init__()
        self.ui = None
        self.cor_mat = CorrelationMatrixFigure()
        self.reg_plot = RegFigure()
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

        self.ui.reg_layout = QtGui.QHBoxLayout()
        self.ui.reg_frame.setLayout(self.ui.reg_layout)
        self.ui.reg_layout.addWidget(self.reg_plot)

        self.ui.actionChange_Sample.triggered.connect(self.set_sample)
        self.ui.actionSave_Matrix.triggered.connect(self.save_matrix)
        self.ui.actionSave_Scatter.triggered.connect(self.save_reg)
        self.cor_mat.SquareSelected.connect(self.reg_plot.draw_reg)

    def set_sample(self):
        dialog = qt_sample_select_dialog.SampleLoadDialog()
        res = dialog.exec_()
        if res == dialog.Accepted:
            new_sample = dialog.current_sample
            self.cor_mat.set_sample(new_sample)
            self.reg_plot.draw_initial_message()

    def save_matrix(self):
        filename = unicode(QtGui.QFileDialog.getSaveFileName(self,
                                                             "Save Matrix",".","PDF (*.pdf);;PNG (*.png);;svg (*.svg)"))
        self.cor_mat.f.savefig(filename)
    def save_reg(self):
        filename = unicode(QtGui.QFileDialog.getSaveFileName(self,
                                                             "Save Scatter",".","PDF (*.pdf);;PNG (*.png);;svg (*.svg)"))
        self.reg_plot.f.savefig(filename)

if __name__ == "__main__":
    app = QtGui.QApplication([])
    main_window = CorrelationsApp()
    main_window.show()
    app.exec_()
