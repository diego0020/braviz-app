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

import numpy as np
import pandas as pd

import logging

style.use('ggplot')


class _AbstractPlot():
    def redraw(self):
        raise NotImplementedError("must be reinplemented")
    def add_subjects(self,subjs):
        return None
    def highlight(self,subj):
        return None
    def get_tooltip(self,event):
        return ""


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

        self.colors_dict = None




    def draw_message(self,message):
        self.axes.clear()
        self.axes.set_ylim(0,1)
        self.axes.set_xlim(0,1)
        self.axes.text(0.5, 0.5, message, horizontalalignment='center',
                       verticalalignment='center', fontsize=16)
        self.draw()

    def draw_bars(self,data,ylims=None,orientation="vertical",group_labels=None):
        self.painted_plot = MatplotBarPlot(self.axes,data,ylims,orientation,group_labels)
        self.colors_dict = self.painted_plot.colors_dict
        self.draw()

    def draw_coefficients_plot(self,coefficients_df,draw_intecept = False):
        self.painted_plot = CoefficientsPlot(self.axes,coefficients_df,draw_intecept)
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
        self.painted_plot.redraw()
        self.draw()

    def show_tooltip(self,event):
        if not isinstance(self.painted_plot,_AbstractPlot):
            log = logging.getLogger(__name__)
            log.error("Invalid plot")
            return

        message = self.painted_plot.get_tooltip(event)
        if len(message)>0:
            position=event.mouseevent.x, self.height() - event.mouseevent.y
            QtGui.QToolTip.showText(self.mapToGlobal(QtCore.QPoint(*position)), message, self)
        else:
            QtGui.QToolTip.hideText()


    def mouse_move_handler(self,event):
        self.reset_last_id()
        self.pick(event)

    def reset_last_id(self):
        self.last_id = None

    def mouse_click_handler(self,event):
        button = event.button
        log = logging.getLogger(__name__)
        if self.last_id is None:
            return
        if button == 1:
            log.debug("click")
            self.highlight_id(self.last_id)
            self.point_picked.emit(str(self.last_id))
        elif button == 3:
            log.debug("right_click")
            self.context_requested.emit(str(self.last_id))


class MatplotBarPlot(_AbstractPlot):
    def __init__(self,axes,data,ylims=None,orientation = "vertical",group_labels=None):
        self.highlight_color = '#000000'
        self.highlighted = None
        self.axes = axes
        self.orientation = orientation
        self.group_labels=group_labels

        self.grouped = True if data.shape[1]>=2 else False

        assert isinstance(self.axes, matplotlib.axes.Axes)
        self.axes.cla()
        if ylims is None:
            maxi = data.max()[0]
            mini = 0
            span = maxi - mini
            ylims=(0,maxi+0.1*span)

        col0 = data.columns[0]
        self.col0=col0
        ix_name = data.index.name
        if self.orientation == "vertical":
            self.axes.set_ylim(*ylims)
            self.axes.tick_params('y', left='off', right='on', labelleft='off', labelright='on')
            self.axes.tick_params('x', top='off', bottom='on', labelbottom='on', labeltop='off')
            self.axes.get_yaxis().set_label_position("right")
            self.axes.set_ylabel(col0)
            if ix_name is not None:
                self.axes.set_xlabel(ix_name)
        else:
            self.axes.set_xlim(*ylims)
            self.axes.tick_params('y', left='on', right='off', labelleft='on', labelright='off')
            self.axes.tick_params('x', top='off', bottom='on', labelbottom='on', labeltop='off')
            self.axes.get_yaxis().set_label_position("left")
            self.axes.set_xlabel(col0)
            if ix_name is not None:
                self.axes.set_ylabel(ix_name)
        #sort data
        data2 = data.dropna()
        if self.orientation == "vertical":
            data2.sort(col0,ascending=False,inplace=True)
        else:
            data2.sort(col0,ascending=True,inplace=True)
        heights = data2[col0].get_values()
        pos = np.arange(len(heights))
        data2["_pos"]=pos

        #create colors
        # colors_list=matplotlib.rcParams['axes.color_cycle']
        # if data2.shape[1]>=2:
        #     groups_col = data2.columns[1]
        #     unique_indexes = data2[groups_col].unique()
        #     unique_map = dict(izip(unique_indexes,range(len(unique_indexes))))
        #     colors = [colors_list[unique_map[i]] for i in data2[groups_col]]
        # else:
        #     colors = colors_list[0]


        self.axes.axhline(ylims[0],color=self.highlight_color)

        self.data = data2
        self.pos=pos
        self.heights = heights
        #self.colors = colors

        groups = self.data.groupby(self.data.columns[1])
        colors_list=matplotlib.rcParams['axes.color_cycle']
        self.colors_dict = dict((n,colors_list[i]) for i, (n,g) in enumerate(groups) if len(g)>0)
        self.redraw()


    def redraw(self):
        #main plot
        ###################
        self.axes.cla()
        log = logging.getLogger(__name__)
        colors_list=matplotlib.rcParams['axes.color_cycle']
        if self.grouped is False:
            self.__draw_bars_and_higlight(self.data,"_nolegend_",colors_list[0])
        else:
            groups = self.data.groupby(self.data.columns[1])
            for i,(name,group) in enumerate(groups):
                if len(group)>0:
                    label = self.group_labels[name] if self.group_labels is not None else None
                    if label is None or len(label)==0:
                        label = "Level %s"%name
                    log.debug(label)
                    self.__draw_bars_and_higlight(group,label,colors_list[i])

        if self.orientation == "vertical":
            self.axes.set_xticklabels(self.data.index)
            self.axes.set_xticks(self.pos)
            self.axes.set_xlim(-0.5,len(self.pos)-0.5)
        else:
            self.axes.set_yticklabels(self.data.index)
            self.axes.set_yticks(self.pos)
            self.axes.set_ylim(-0.5,len(self.pos)-0.5)

        ix_name = self.data.index.name
        if self.orientation == "vertical":
            self.axes.tick_params('y', left='off', right='on', labelleft='off', labelright='on')
            self.axes.tick_params('x', top='off', bottom='on', labelbottom='on', labeltop='off')
            self.axes.get_yaxis().set_label_position("right")
            self.axes.set_ylabel(self.col0)
            if ix_name is not None:
                self.axes.set_xlabel(ix_name)
        else:
            self.axes.tick_params('y', left='on', right='off', labelleft='on', labelright='off')
            self.axes.tick_params('x', top='off', bottom='on', labelbottom='on', labeltop='off')
            self.axes.get_yaxis().set_label_position("left")
            self.axes.set_xlabel(self.col0)
            if ix_name is not None:
                self.axes.set_ylabel(ix_name)

        if self.grouped is True:
            self.axes.legend(loc="lower right")


    def add_subjects(self):
        pass

    def __draw_bars_and_higlight(self,data,label,color):
        if self.orientation == "vertical":
            patches=self.axes.bar(data["_pos"].values,data[self.col0].values,align="center",picker=5,color=color)
        else:
            patches=self.axes.bar(left=None,bottom=data["_pos"].values,width=data[self.col0].values,align="center",picker=5,
                              orientation=self.orientation, height=0.8,label=label,color=color)
        for i,p in enumerate(patches):
            p.set_url(data.index[i])
            if data.index[i]==self.highlighted:
                p.set_linewidth(2)
                p.set_ec(self.highlight_color)


    def highlight(self,subj):
        self.highlighted = subj

    def get_tooltip(self,event):
        subj = event.artist.get_url()
        data = self.data
        col0 = data.columns[0]
        message_rows = ["%s:"%subj]
        #value
        row="%s : %.2f"%(col0,data.ix[subj,col0])
        message_rows.append(row)
        #group?
        if self.grouped:
            col1 = data.columns[1]
            label = data.ix[subj,col1]
            if self.group_labels is not None:
                label = self.group_labels[label]
            row = "%s : %s"%(col1,label)
            message_rows.append(row)
        message = "\n".join(message_rows)
        #print message
        return message

class CoefficientsPlot(_AbstractPlot):
    def __init__(self,axes,coefs_df,draw_intercept=False):
        self.axes = axes
        if draw_intercept is False:
            self._df = coefs_df.iloc[1:].copy()
        else:
            self._df = coefs_df.copy()

        self.centers = self._df.Slope
        self.l95 = [i[0] for i in self._df.CI_95]
        self.h95 = [i[1] for i in self._df.CI_95]
        self.l68 = self.centers - self._df.Std_error
        self.h68 = self.centers + self._df.Std_error
        self.names = list(self._df.index)
        self.n_coefs = len(self._df)
        self.pos = range(self.n_coefs)
        self.color =matplotlib.rcParams['axes.color_cycle'][1]
        self.redraw()
    def redraw(self):
        self.axes.clear()
        self.axes.set_ylim(-0.5,self.n_coefs-0.5,auto=False)
        self.axes.set_xlim(-1,1,auto=True)
        self.axes.axvline(0,ls="--",c="k")
        self.axes.minorticks_off()

        #draw centers
        self.axes.plot(self.centers,self.pos,"o",ms=8,zorder=10, c=self.color)

        #draw 68
        for p,l,h in izip(self.pos,self.l68,self.h68):
            self.axes.plot([l,h],[p,p],c=self.color,solid_capstyle="round", lw=2.5,zorder=5)
        #draw 95
        for p,l,h in izip(self.pos,self.l95,self.h95):
            self.axes.plot([l,h],[p,p],c=self.color,solid_capstyle="round", lw=1,zorder=1,picker=0.5)

        #ticks
        self.axes.set_yticks(self.pos)
        self.axes.set_yticklabels(self.names)

        self.axes.set_xlabel("Standardized coefficients")

    def get_tooltip(self, event):
        y_coord = event.mouseevent.ydata
        i = int(round(y_coord))
        try:
            name = self.names[i]
            slope = self.centers[i]
            message = "%s: %.2g"%(name,slope)
            return message
        except IndexError:
            return ""

if __name__ == "__main__":
    #init widget
    app = QtGui.QApplication([])
    #show bar plot
    values = np.random.rand(10)
    groups = np.random.randint(1,3,10)
    data = pd.DataFrame({"test":values, "group":groups},columns=["test","group"])
    widget = MatplotWidget()
    widget.show()
    widget.draw_bars(data,orientation="horizontal",group_labels={1:"One",2:"Two"})
    #widget.draw_bars(data,orientation="vertical")
    app.exec_()