from __future__ import division
from functools import wraps
from itertools import izip
import itertools
import logging
import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas, FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
import seaborn as sns
from braviz.readAndFilter import tabular_data as braviz_tab_data, tabular_data

__author__ = 'Diego'

from PyQt4 import QtCore
from PyQt4 import QtGui


class RotatedLabel(QtGui.QLabel):
    def __init__(self,parent):
        super(RotatedLabel,self).__init__(parent)
        self.color = (255,0,0)

    def set_color(self,color):
        """
        Sets the color of the label
        :param color: a 3-tuple with values in [0,1]
        """
        if color is not None:
            color = [c*256 for c in color]
            self.color = color
        else:
            self.color = (0,0,0)
    def paintEvent(self, QPaintEvent):
        color = self.color
        painter = QtGui.QPainter(self)
        painter.save()
        painter.setPen(QtCore.Qt.black)
        text = self.text()
        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)
        fm=QtGui.QFontMetrics(painter.font())
        #print "g:",self.rect()
        #print "t:",fm.boundingRect(text)
        g=self.rect()
        x=g.width()/2  + (fm.ascent()/2)
        #-10 is for the square
        y=g.height()/2 + fm.width(text)/2-15
        #print "x:",x
        painter.translate(x,y)
        painter.rotate(270)
        qcolor = QtGui.QColor.fromRgb(*color)
        painter.fillRect(QtCore.QRect(-1*fm.height()-10,-1*fm.ascent()+2,20,20),qcolor)
        painter.drawText(QtCore.QPoint(0,0),text)
        painter.restore()


class ListValidator(QtGui.QValidator):
    def __init__(self, valid_options):
        super(ListValidator, self).__init__()
        self.valid = frozenset(valid_options)

    def validate(self, QString, p_int):
        str_value = str(QString)
        if str_value in self.valid:
            return QtGui.QValidator.Acceptable, p_int
        else:
            if len(str_value) == 0:
                return QtGui.QValidator.Intermediate, p_int
            try:
                i = int(str_value)
            except Exception:
                return QtGui.QValidator.Invalid, p_int
            else:
                return QtGui.QValidator.Intermediate, p_int


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
        self.ylim = self.axes.get_ylim()
        #self.mpl_connect("button_press_event",self.generate_tooltip_event)
        self.mpl_connect("pick_event", self.generate_tooltip_event)
        self.setMouseTracking(True)
        self.mpl_connect('motion_notify_event', self.mouse_move_event_handler)
        self.x_order = None
        self.fliers_x_dict = None

        self.last_plot_function = None
        self.last_plot_arguments = None
        self.last_plot_kw_arguments = None

        self.limits_vertical = True


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

        log = logging.getLogger(__name__)
        self.fig.clear()
        if len(data) == 0:
            log.warning("Data Frame is empty")
        if isinstance(data,(pd.DataFrame,pd.Series)):
            assert pd.isnull(data).sum().sum() == 0
        elif isinstance(data,np.ndarray):
            assert np.sum(np.isnan(data))==0
        elif isinstance(data,list):
            for each in data:
                assert np.sum(np.isnan(each))==0
        else:
            raise  ValueError
        if data2 is not None:
            if isinstance(data2,(pd.DataFrame,pd.Series)):
                assert pd.isnull(data2).sum().sum() == 0
            elif isinstance(data2,np.ndarray):
                assert np.sum(np.isnan(data2))==0
            elif isinstance(data2,list):
                for each in data2:
                    assert np.sum(np.isnan(each))==0
            else:
                raise  ValueError
        self.axes=self.fig.add_subplot(1,1,1)
        self.axes.clear()
        self.draw()
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
            self.axes.scatter(data, data2, color=colors, picker=5, urls=urls, alpha=0.8)
        else:
            for c, d, d2, lbl, url in zip(colors, data, data2, labels, urls):
                self.axes.scatter(d, d2, color=c, label=lbl, picker=5, urls=url, alpha=0.8)
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
            self.axes.set_ylim(auto=True)
        self.draw()
        self.xlim = None
        self.ylim = None
        self.x_order = None
        self.back_fig = None


    def redraw_last_plot(self):
        if self.last_plot_function is None:
            return
        else:
            self.last_plot_function(*self.last_plot_arguments, **self.last_plot_kw_arguments)

    def add_max_min_opt_lines(self, mini, opti, maxi):
        if self.back_fig is None:
            self.back_fig = self.copy_from_bbox(self.axes.bbox)
            self.xlim = self.axes.get_xlim()
            self.ylim = self.axes.get_ylim()
        else:
            self.restore_region(self.back_fig)
        self.axes.set_xlim(self.xlim,auto=False)
        self.axes.set_ylim(self.ylim,auto=False)
        if mini is None:
            self.blit(self.axes.bbox)
            return
        if self.limits_vertical:
            opt_line = self.axes.axvline(opti, color="#8da0cb")
            min_line = self.axes.axvline(mini, color="#fc8d62")
            max_line = self.axes.axvline(maxi, color="#fc8d62")

        else:
            opt_line = self.axes.axhline(opti, color="#8da0cb")
            min_line = self.axes.axhline(mini, color="#fc8d62")
            max_line = self.axes.axhline(maxi, color="#fc8d62")


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
    def make_box_plot(self, data, xlabel, ylabel, xticks_labels, ylims=None, intercet=None):
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
        if ylims is not None:
            yspan = ylims[1] - ylims[0]
            self.axes.set_ylim(ylims[0] - 0.1 * yspan, ylims[1] + 0.1 * yspan)

        self.draw()
        if intercet is not None:
            self.add_intercept_line(intercet)
        self.back_fig = self.copy_from_bbox(self.axes.bbox)
        self.x_order = x_permutation
        self.ylim=None
        self.xlim=None

    @repeatatable_plot
    def make_linked_box_plot(self, data, outcome, x_name, z_name,ylims=None):
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
        if ylims is not None:
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