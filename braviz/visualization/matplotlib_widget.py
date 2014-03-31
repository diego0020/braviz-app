from __future__ import division

__author__ = 'Diego'

from PyQt4 import QtCore
from PyQt4 import QtGui

import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.axes

from itertools import izip
from mpltools import style

from functools import wraps
import numpy as np
import pandas as pd
import itertools

style.use('ggplot')

class MatplotWidget(FigureCanvas):
    #These signals return the id of the point where the action occured
    point_picked = QtCore.pyqtSignal(str)
    context_requested = QtCore.pyqtSignal(str)
    def __init__(self,parent=None,dpi=100,initial_message=None):
        fig = Figure(figsize=(5, 5), dpi=dpi, tight_layout=True)
        self.fig = fig
        self.axes = fig.add_subplot(111)
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.updateGeometry()
        palette = self.palette()
        fig.set_facecolor(palette.background().color().getRgbF()[0:3])
        self.axes.margins(0,0,tight=True)
        #observers
        self.setMouseTracking(True)
        self.mpl_connect('motion_notify_event', self.mouse_move_handler)
        self.mpl_connect("pick_event", self.show_tooltip)
        self.mpl_connect("button_press_event",self.mouse_click_handler)

        #internal_data
        self.painted_plot = None
        self.data = None
        self.last_id = None





    def draw_message(self):
        pass

    def draw_bars(self,data,ylims=None):
        self.painted_plot = MatplotBarPlot(self.axes,data,ylims)
        self.show()
        self.draw()


    def draw_histogram(self):
        pass
    def draw_scatter(self):
        pass
    def draw_boxplot(self):
        pass
    def draw_linked_boxplot(self):
        pass
    def draw_spider_plot(self):
        pass
    def highlight_id(self,hid):
        self.painted_plot.highlight(hid)
        self.refresh_last_plot()

    def get_current_id(self):
        return self.last_id
    def add_subject_markers(self):
        pass

    def refresh_last_plot(self):
        #TODO: Not working

        self.painted_plot.redraw()
        self.show()
        self.draw()

    def show_tooltip(self,event):
        ix = event.artist.get_url()
        self.last_id = ix
        data = self.painted_plot.data
        col_name=data.columns[0]
        message = "%s\n%s: %s"%(ix,col_name,data[col_name][ix])
        #print message
        position=event.mouseevent.x, self.height() - event.mouseevent.y
        QtGui.QToolTip.showText(self.mapToGlobal(QtCore.QPoint(*position)), message, self)


    def mouse_move_handler(self,event):
        self.reset_last_id()
        self.pick(event)

    def reset_last_id(self):
        self.last_id = None

    def mouse_click_handler(self,event):
        button = event.button
        if self.last_id is None:
            return
        if button == 1:
            print "click"
            self.highlight_id(self.last_id)
            self.point_picked.emit(str(self.last_id))
        elif button == 3:
            print "right_click"
            self.context_requested.emit(str(self.last_id))


class MatplotBarPlot():
    def __init__(self,axes,data,ylims=None):
        self.highlight_color = '#000000'
        self.highlighted = None
        self.axes = axes

        assert isinstance(self.axes, matplotlib.axes.Axes)
        self.axes.cla()
        if ylims is None:
            maxi = data.max()[0]
            mini = 0
            span = maxi - mini
            ylims=(0,maxi+0.1*span)
        self.axes.set_ylim(*ylims)
        self.axes.tick_params('y', left='off', right='on', labelleft='off', labelright='on')
        self.axes.tick_params('x', top='off', bottom='on', labelbottom='on', labeltop='off')
        self.axes.get_yaxis().set_label_position("right")
        #sort data
        data2 = data.dropna()
        col0 = data2.columns[0]
        data2.sort(col0,ascending=False,inplace=True)
        heights = data2[col0].get_values()
        pos = np.arange(len(heights))


        self.axes.set_ylabel(col0)
        ix_name = data2.index.name
        self.axes.axhline(ylims[0],color=self.highlight_color)
        if ix_name is not None:
            self.axes.set_xlabel(ix_name)
        self.data = data2
        self.pos=pos
        self.heights = heights

        self.redraw()


    def redraw(self):
        #main plot
        ###################
        self.axes.cla()
        patches=self.axes.bar(self.pos,self.heights,align="center",picker=5)
        data2 = self.data
        for i,p in enumerate(patches):
            p.set_url(data2.index[i])
            if data2.index[i]==self.highlighted:
                p.set_linewidth(2)
                p.set_ec(self.highlight_color)
        self.axes.set_xticklabels(data2.index)
        self.axes.set_xticks(self.pos)
        self.axes.set_xlim(-0.5,len(self.pos)-0.5)




    def __draw(self):
        pass

    def add_subjects(self):
        pass
    def highlight(self,subj):
        self.highlighted = subj

class OldMatplotWidget(FigureCanvas):
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
        self.x_order = None
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
        self.axes.clear()
        self.axes.tick_params('x', bottom='on', labelbottom='on', labeltop='off')

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
            xlims2 = (xlims[0] - width / 10, xlims[1] + width / 10,)
            self.axes.set_xlim(xlims2, auto=False)
        else:
            self.axes.set_xlim(auto=True)
        self.draw()
        self.back_fig = self.copy_from_bbox(self.axes.bbox)
        self.xlim = self.axes.get_xlim()
        self.x_order = None

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

    @repeatatable_plot
    def make_box_plot(self, data, xlabel, ylabel, xticks_labels, ylims, intercet=None):

        #Sort data and labels according to median
        x_permutation = range(len(data))
        if xticks_labels is None:
                xticks_labels = range(len(data))
        data_labels = zip(data, xticks_labels, x_permutation)
        data_labels.sort(key=lambda x: np.median(x[0]))
        data, xticks_labels, x_permutation = zip(*data_labels)
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
        if intercet is not None:
            self.add_intercept_line(intercet)
        self.back_fig = self.copy_from_bbox(self.axes.bbox)
        self.x_order = x_permutation

    @repeatatable_plot
    def make_linked_box_plot(self, data, xlabel, ylabel, xticks_labels, colors, top_labels, ylims):
        self.axes.clear()
        self.axes.tick_params('x', bottom='on', labelbottom='on', labeltop='off')
        self.axes.tick_params('y', left='off', labelleft='off', labelright='on', right="on")
        self.axes.yaxis.set_label_position("right")
        self.axes.set_ylim(auto=True)
        x_permutation = range(len(data[0]))
        data_join = [list(itertools.chain.from_iterable(l)) for l in zip(*data)]
        data_order = zip(data_join, x_permutation)
        data_order.sort(key=lambda y: np.median(y[0]))
        _, x_permutation = zip(*data_order)

        # self.x_order=x_permutation # at the end of method for consistency
        #sort data
        for k, l in enumerate(data):
            data[k] = [l[i] for i in x_permutation]
        xticks_labels = [xticks_labels[i] for i in x_permutation]

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
        self.x_order = x_permutation

    @repeatatable_plot
    def make_histogram(self, data, xlabel):
        self.axes.clear()
        self.axes.tick_params('x', bottom='on', labelbottom='on', labeltop='off')
        self.axes.tick_params('y', left='off', labelleft='off', labelright='on', right="on")
        self.axes.yaxis.set_label_position("right")
        self.axes.set_ylim(auto=True)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel("Frequency")
        self.axes.hist(data, color="#2ca25f", bins=20)
        self.draw()
        self.back_fig = self.copy_from_bbox(self.axes.bbox)
        self.x_order = None

    def add_subject_points(self, x_coords, y_coords, color=None, urls=None):
        #print "adding subjects"
        #self.restore_region(self.back_fig)
        self.redraw_last_plot()
        if self.x_order is not None:
            #labels go from 1 to n; permutation is from 0 to n-1
            assert 0 not in x_coords
            x_coords = map(lambda k: self.x_order.index(int(k) - 1) + 1, x_coords)
        if color is None:
            color = "black"
        collection = self.axes.scatter(x_coords, y_coords, marker="o", s=120, edgecolors=color, urls=urls, picker=5)
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
    #init widget
    app = QtGui.QApplication([])
    #show bar plot
    values = np.random.rand(10)
    data = pd.DataFrame({"test":values})
    widget = MatplotWidget()
    widget.show()
    widget.draw_bars(data)
    app.exec_()