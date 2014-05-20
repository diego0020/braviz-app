from __future__ import division
__author__ = 'Diego'

import seaborn as sns
from PyQt4 import QtGui,QtCore
import numpy as np
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
import braviz.readAndFilter.tabular_data as braviz_tab_data

from matplotlib import pyplot as plt

class MatplotWidget1(FigureCanvas):
    box_outlier_pick_signal = QtCore.pyqtSignal(float, float, tuple)
    scatter_pick_signal = QtCore.pyqtSignal(str, tuple)

    def __init__(self, parent=None, dpi=100, initial_message=None):
        fig,ax = plt.subplots()
        #fig = Figure(figsize=(5, 5), dpi=dpi, tight_layout=True)
        #self.fig = plt.figure()
        #self.axes = plt.Axes()
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.updateGeometry()
        palette = self.palette()
        self.setContentsMargins(0,0,0,0)
        fig.set_facecolor(palette.background().color().getRgbF()[0:3])
        self.axes = ax


    def make_plot(self, data,x_name,z_name,outcome):
        sns.set_style("darkgrid")

        plt.sca(self.axes)
        plt.clf()
        ax = plt.axes()
        pg=sns.lmplot(x_name,outcome,data,hue=z_name)




        #self.axes.legend(numpoints=1, fancybox=True, fontsize="small", )
        #self.axes.get_legend().draggable(True, update="loc")
        fig = pg.fig
        fig.set_canvas(self)
        self.figure = fig
        fig = self.figure
        palette = self.palette()
        fig.set_facecolor(palette.background().color().getRgbF()[0:3])

        plt.show()
        self.draw()
        self.resize_event()
        self.draw()




if __name__ == "__main__":
    data = np.random.rand(500)
    #add outlier
    data[0]=-3
    widget = MatplotWidget1()

    widget.show()
    #widget.make_box_plot(data,"x","y","uno",(-4,2))
    data = braviz_tab_data.get_data_frame_by_name(["GENERO","UBIC3","FSIQ"])
    widget.make_plot(data,"UBIC3","GENERO","FSIQ")
    app = QtGui.QApplication([])
    app.exec_()
