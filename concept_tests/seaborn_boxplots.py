__author__ = 'Diego'

import seaborn as sns
from PyQt4 import QtGui,QtCore
import matplotlib
import numpy as np
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class MatplotWidget(FigureCanvas):
    box_outlier_pick_signal = QtCore.pyqtSignal(float, float, tuple)
    scatter_pick_signal = QtCore.pyqtSignal(str, tuple)

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
        self.xlim = self.axes.get_xlim()
        #self.mpl_connect("button_press_event",self.generate_tooltip_event)
        self.mpl_connect("pick_event", self.generate_tooltip_event)
        self.setMouseTracking(True)
        self.mpl_connect('motion_notify_event', self.mouse_move_event_handler)
        self.x_order = None

    def make_box_plot(self, data, xlabel, ylabel, xticks_labels, ylims, intercet=None):
        self.fig.clear()
        self.axes=self.fig.add_subplot(1,1,1)
        #Sort data and labels according to median
        self.axes.clear()
        self.axes.tick_params('x', bottom='on', labelbottom='on', labeltop='off', top="off")
        self.axes.tick_params('y', left='off', labelleft='off', labelright='on', right="on")
        self.axes.yaxis.set_label_position("right")
        self.axes.set_ylim(ylims)
        #artists_dict = self.axes.boxplot(data, sym='gD')
        sns.boxplot(data,ax=self.axes,fliersize=20)
        #find fliers
        for ls in self.axes.get_lines():
            if ls.get_markersize()==20:
                ls.set_picker(5)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)

        self.draw()


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


if __name__ == "__main__":
    data = np.random.rand(500)
    #add outlier
    data[0]=-3
    widget = MatplotWidget()
    def handle_box_outlier_pick(x, y, position):
        print "received signal"
        print x,y

    widget.show()
    widget.make_box_plot(data,"x","y","uno",(-4,2))
    widget.box_outlier_pick_signal.connect(handle_box_outlier_pick)
    app = QtGui.QApplication([])
    app.exec_()