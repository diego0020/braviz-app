from __future__ import division

__author__ = 'Diego'

from PyQt4 import QtCore
from PyQt4 import QtGui

import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.axes
import matplotlib.gridspec as gridspec

from itertools import izip

import numpy as np
import pandas as pd

import logging

import seaborn as sns


class _AbstractPlot():
    def redraw(self):
        raise NotImplementedError("must be reinplemented")
    def add_subjects(self,subjs):
        return None
    def highlight(self,subj):
        return None
    def get_tooltip(self,event):
        return ""
    def get_last_id(self):
        return None


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

        self.colors_dict = None
        self.__title = None


    def __get_one_axis(self):
        n_axis = len(self.fig.get_axes())
        if n_axis == 1:
            self.axes.clear()
        else:
            self.fig.clear()
            self.axes = self.fig.add_subplot(111)
            self.axes.margins(0,0,tight=True)
        return self.axes


    def draw_message(self,message):
        self.__get_one_axis()
        self.painted_plot=MessagePlot(self.axes,message)
        self.draw()

    def draw_bars(self,data,ylims=None,orientation="vertical",group_labels=None):
        self.__get_one_axis()
        self.painted_plot = MatplotBarPlot(self.axes,data,ylims,orientation,group_labels)
        self.colors_dict = self.painted_plot.colors_dict
        self.draw()

    def draw_coefficients_plot(self,coefficients_df,draw_intecept = False):
        self.__get_one_axis()
        self.painted_plot = CoefficientsPlot(self.axes,coefficients_df,draw_intecept)
        self.draw()

    def draw_histogram(self):
        pass
    def draw_scatter(self,data,x_name,y_name,xlabel=None,ylabel=None,reg_line=True,hue_var=None,hue_labels = None,
                     qualitative_map = True):
        self.__get_one_axis()
        self.painted_plot = ScatterPlot(self.axes,data,x_name,y_name,xlabel,ylabel,reg_line,hue_var=hue_var,
                                        hue_labels=hue_labels,qualitative_map = qualitative_map)
        self.draw()
    def draw_boxplot(self):
        pass
    def draw_spider_plot(self):
        pass
    def draw_residuals(self,residuals,fitted,names=None):
        #this will create two access
        self.painted_plot = ResidualsDiagnosticPlot(self.fig,residuals,fitted,names)
        self.draw()

    def highlight_id(self,hid):
        self.painted_plot.highlight(hid)
        self.refresh_last_plot()

    def get_current_id(self):
        return self.painted_plot.get_last_id()

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
        last_id = self.painted_plot.get_last_id()
        if last_id is None:
            return
        if button == 1:
            log.debug("click")
            self.highlight_id(last_id)
            self.point_picked.emit(str(last_id))
        elif button == 3:
            log.debug("right_click")
            self.context_requested.emit(str(last_id))

    def set_figure_title(self,title):
        #if self.__title is not None:
        #    self.__title.remove()
        self.__title = self.axes.set_title(title)
        self.draw()

class MatplotBarPlot(_AbstractPlot):
    def __init__(self,axes,data,ylims=None,orientation = "vertical",group_labels=None):
        sns.set_style("darkgrid")
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
        self.last_id = None
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
        self.last_id = subj
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

    def get_last_id(self):
        return self.last_id


class CoefficientsPlot(_AbstractPlot):
    def __init__(self,axes,coefs_df,draw_intercept=False):
        sns.set_style("darkgrid")
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
        self.color = matplotlib.rcParams['axes.color_cycle'][1]
        self.axes.tick_params('x', bottom='on', labelbottom='on', labeltop='off',top='off')
        self.axes.tick_params('y', left='on', labelleft='on', labelright='off', right="off")
        self.axes.yaxis.set_label_position("right")
        self.redraw()
    def redraw(self):
        self.axes.clear()
        self.axes.set_ylim(-0.5,self.n_coefs-0.5,auto=False)
        self.axes.set_xlim(-1,1,auto=True)
        self.axes.axvline(0,ls="--",c=(0.4,0.4,0.4))
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

class ResidualsDiagnosticPlot(_AbstractPlot):
    def __init__(self,figure,residuals,fitted,names=None):

        sns.set_style("darkgrid")
        self.names = names
        figure.clear()
        self.fig = figure
        gs = gridspec.GridSpec(1,2,width_ratios=(2,1))
        self.axes=self.fig.add_subplot(gs[1])
        self.axes.clear()
        self.axes.tick_params('x', bottom='on', labelbottom='on', labeltop='off',top='off')
        self.axes.tick_params('y', left='off', labelleft='off', labelright='off', right="off")
        self.axes.yaxis.set_label_position("right")
        self.axes.set_ylim(auto=True)
        #self.axes.set_ylabel("Residuals")
        self.axes.set_xlabel("Frequency")
        self.axes2 = self.fig.add_subplot(gs[0],sharey=self.axes)

        self.axes2.tick_params('x', bottom='on', labelbottom='on', labeltop='off',top='off')
        self.axes2.tick_params('y', left='on', labelleft='on', labelright='off', right="off")
        self.axes2.set_ylabel("Residuals")
        self.axes2.set_xlabel("Fitted")
        self.axes2.yaxis.set_label_position("left")
        self.axes2.axhline(color='k')

        self.residuals = residuals
        self.fitted = fitted
        self.redraw()

    def get_tooltip(self, event):
        if self.names is None:
            return ""
        if event.mouseevent.inaxes == self.axes2:
            ind = event.ind
            names = ["%s"%self.names[i] for i in ind]
            return "\n".join(names)

    def redraw(self):
        residuals, fitted = self.residuals, self.fitted
        self.axes.hist(residuals, color="#2ca25f", bins=20,orientation = "horizontal")
        self.axes2.scatter(fitted,residuals,s=20,color="#2ca25f",picker=0.5)


class MessagePlot(_AbstractPlot):
    def __init__(self,axes,message):
        sns.set_style("darkgrid")
        self.axes = axes
        self.axes.set_ylim(0,1)
        self.axes.set_xlim(0,1)

        self.message = message
        self.axes.tick_params('x', bottom='off', labelbottom='off', labeltop='off',top='off')
        self.axes.tick_params('y', left='off', labelleft='off', labelright='off', right="off")
        self.axes.yaxis.set_label_position("right")
        self.redraw()
    def redraw(self):
        message = self.message
        self.axes.text(0.5, 0.5, message, horizontalalignment='center',
                    verticalalignment='center', fontsize=16)


class ScatterPlot(_AbstractPlot):
    def __init__(self,axes,data,x_var,y_var,xlabel=None,ylabel=None,reg_line=True,hue_var = None, hue_labels = None,
                 qualitative_map = True):
        sns.set_style("darkgrid")
        self.x_name=x_var
        self.y_name=y_var
        self.z_name = hue_var
        if xlabel is None:
            xlabel = x_var
        if ylabel is None:
            ylabel = y_var
        self.df = data.copy()
        self.axes = axes
        self.reg_line = reg_line
        self.axes.tick_params('x', bottom='on', labelbottom='on', labeltop='off',top='off')
        self.axes.tick_params('y', left='off', labelleft='off', labelright='on', right="on")
        self.axes.yaxis.set_label_position("right")
        self.axes.set_ylabel(ylabel)
        self.axes.set_xlabel(xlabel)
        self.axes.set_xlim(auto=True)
        self.axes.set_ylim(auto=True)
        self.color = matplotlib.rcParams['axes.color_cycle'][1]
        self.hue_labels = hue_labels
        self.qualitative_map = qualitative_map
        self.redraw()

    def redraw(self):
        self.axes.clear()
        if self.z_name is None:
            url = self.df.index
            sns.regplot(self.x_name,self.y_name,data=self.df,fit_reg=self.reg_line,
                        scatter_kws={"picker":0.5,"url":url},ax=self.axes,
                    color=self.color)
        else:
            self.artists_dict=dict()
            unique_levels = np.unique(self.df[self.z_name])
            n_levels=len(unique_levels)
            if self.qualitative_map:
                colors = sns.color_palette("Dark2",n_levels)
            else:
                #first one is too light
                colors = sns.color_palette("YlOrRd",n_levels+1)[1:]
            for c,l in izip(colors,unique_levels):
                df2 = self.df[self.df[self.z_name] == l]
                if self.hue_labels is not None:
                    label = self.hue_labels.get(l,"?")
                else:
                    label = "?"
                url = df2.index
                sns.regplot(self.x_name,self.y_name,data=df2,fit_reg=self.reg_line,
                            scatter_kws={"picker":0.5,"url":url},label=label,ax=self.axes,
                    color=c)
            self.add_legend()

    def add_subjects(self, subjs):
        _AbstractPlot.add_subjects(self, subjs)

    def highlight(self, subj):
        _AbstractPlot.highlight(self, subj)

    def get_tooltip(self, event):
        if event.mouseevent.inaxes == self.axes:
            ind = event.ind
            urls = event.artist.get_url()
            names = ["%s"%urls[i] for i in ind]
            #names = ["%s"%self.names[i] for i in ind]
            return "\n".join(names)

    def add_legend(self):
        if self.hue_labels is None:
            return
        self.axes.legend()


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