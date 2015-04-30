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


from __future__ import division
import cPickle
from functools import wraps
from itertools import izip
import itertools
import logging
import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
import seaborn as sns

from braviz.readAndFilter import tabular_data as braviz_tab_data, user_data as braviz_user_data, config_file
from braviz.readAndFilter.tabular_data import get_var_name, is_variable_nominal, get_labels_dict, get_data_frame_by_index, get_maximum_value, get_min_max_values

__author__ = 'Diego'

from PyQt4 import QtCore
from PyQt4 import QtGui


class RotatedLabel(QtGui.QLabel):

    """
    A vertical label useful for labeling rows of data

    Args:
        parent (QObject) : Qt Parent
    """

    def __init__(self, parent):
        super(RotatedLabel, self).__init__(parent)
        self.color = (255, 0, 0)

    def set_color(self, color):
        """
        Sets the color of the label

        Args:
            color (tuple): a 3-tuple with values in [0,1]
        """
        if color is not None:
            color = [c * 256 for c in color]
            self.color = color
        else:
            self.color = (0, 0, 0)

    def paintEvent(self, QPaintEvent):
        color = self.color
        painter = QtGui.QPainter(self)
        painter.save()
        painter.setPen(QtCore.Qt.black)
        text = self.text()
        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)
        fm = QtGui.QFontMetrics(painter.font())
        # print "g:",self.rect()
        # print "t:",fm.boundingRect(text)
        g = self.rect()
        x = g.width() / 2 + (fm.ascent() / 2)
        #-10 is for the square
        y = g.height() / 2 + fm.width(text) / 2 - 15
        # print "x:",x
        painter.translate(x, y)
        painter.rotate(270)
        qcolor = QtGui.QColor.fromRgb(*color)
        painter.fillRect(
            QtCore.QRect(-1 * fm.height() - 10, -1 * fm.ascent() + 2, 20, 20), qcolor)
        painter.drawText(QtCore.QPoint(0, 0), text)
        painter.restore()


class ListValidator(QtGui.QValidator):

    """
    Can be applied to :obj:`QLineEdit` so that it will only accept input from a list of possible values.

    Can be used together with :obj:`QCompleter`

    Args:
        valid_options (set) : Set of valid strings to accept as input
    """

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

def repeatatable_plot(func):
    @wraps(func)
    def saved_plot_func(*args, **kwargs):
        self = args[0]
        self.last_plot_function = func
        self.last_plot_arguments = args
        self.last_plot_kw_arguments = kwargs
        return func(*args, **kwargs)

    return saved_plot_func

class MatplotWidget(FigureCanvas):
    box_outlier_pick_signal = QtCore.pyqtSignal(str, tuple)
    scatter_pick_signal = QtCore.pyqtSignal(str, tuple)
    # TODO: instead of using blit create a @wrapper to save last render command to restore after drawing subjects
    # TODO: Unify with MatplotWidget in visualization

    def __init__(self, parent=None, dpi=100, initial_message=None):
        fig = Figure(figsize=(5, 5), dpi=dpi, tight_layout=True)
        self.fig = fig
        self.axes = fig.add_subplot(111)
        self.axes2 = None
        # self.axes.hold(False)
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(
            self, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.updateGeometry()
        palette = self.palette()
        self.setContentsMargins(0, 0, 0, 0)
        fig.set_facecolor(palette.background().color().getRgbF()[0:3])
        self.initial_text(initial_message)
        self.back_fig = self.copy_from_bbox(self.axes.bbox)
        self.xlim = self.axes.get_xlim()
        self.ylim = self.axes.get_ylim()
        # self.mpl_connect("button_press_event",self.generate_tooltip_event)
        self.mpl_connect("pick_event", self.generate_tooltip_event)
        self.setMouseTracking(True)
        self.mpl_connect('motion_notify_event', self.mouse_move_event_handler)
        self.x_order = None
        self.x_order_i = None
        self.fliers_x_dict = None

        self.last_plot_function = None
        self.last_plot_arguments = None
        self.last_plot_kw_arguments = None

        self.limits_vertical = True

    def initial_text(self, message):
        if message is None:
            message = "Welcome"

        sns.set_style("dark")
        self.fig.clear()
        self.axes = self.fig.add_subplot(111)
        self.axes.text(0.5, 0.5, message, horizontalalignment='center',
                       verticalalignment='center', fontsize=12)
        # Remove tick marks
        self.axes.tick_params(
            'y', left='off', right='off', labelleft='off', labelright='off')
        self.axes.tick_params(
            'x', top='off', bottom='off', labelbottom='off', labeltop='off')
        # Remove axes border
        for child in self.axes.get_children():
            if isinstance(child, matplotlib.spines.Spine):
                child.set_visible(False)
        # remove minor tick lines
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
        if isinstance(data, (pd.DataFrame, pd.Series)):
            assert pd.isnull(data).sum().sum() == 0
        elif isinstance(data, np.ndarray):
            assert np.sum(np.isnan(data)) == 0
        elif isinstance(data, list):
            for each in data:
                assert np.sum(np.isnan(each)) == 0
        else:
            raise ValueError
        if data2 is not None:
            if isinstance(data2, (pd.DataFrame, pd.Series)):
                assert pd.isnull(data2).sum().sum() == 0
            elif isinstance(data2, np.ndarray):
                assert np.sum(np.isnan(data2)) == 0
            elif isinstance(data2, list):
                for each in data2:
                    assert np.sum(np.isnan(each)) == 0
            else:
                raise ValueError
        self.axes = self.fig.add_subplot(1, 1, 1)
        self.axes.clear()
        #self.draw()
        self.axes.tick_params(
            'x', bottom='on', labelbottom='on', labeltop='off', top="off")

        self.axes.yaxis.set_label_position("right")
        # print "urls:" ,urls
        if data2 is None:
            np.random.seed(982356032)
            data2 = np.random.rand(len(data))
            self.axes.tick_params(
                'y', left='off', labelleft='off', labelright='off', right="off")
        else:
            self.axes.tick_params(
                'y', right='on', labelright='on', left='off', labelleft='off')
        if x_lab is not None:
            self.axes.set_xlabel(x_lab)
        if y_lab is not None:
            self.axes.set_ylabel(y_lab)

        if colors is None:
            colors = "#2ca25f"
            self.axes.scatter(
                data, data2, color=colors, picker=5, urls=urls, alpha=0.8)
        else:
            for c, d, d2, lbl, url in zip(colors, data, data2, labels, urls):
                self.axes.scatter(
                    d, d2, color=c, label=lbl, picker=5, urls=url, alpha=0.8)
            self.axes.legend(numpoints=1, fancybox=True, fontsize="small", )
            self.axes.get_legend().draggable(True, update="loc")

        if xlims is not None:
            width = xlims[1] - xlims[0]
            if width == 0:
                xlims2 = (xlims[0] - 0.5, xlims[0] + 0.5)
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
            self.last_plot_function(
                *self.last_plot_arguments, **self.last_plot_kw_arguments)

    def add_max_min_opt_lines(self, mini, opti, maxi):
        if self.back_fig is None:
            self.back_fig = self.copy_from_bbox(self.axes.bbox)
            self.xlim = self.axes.get_xlim()
            self.ylim = self.axes.get_ylim()
        else:
            self.restore_region(self.back_fig)
        self.axes.set_xlim(self.xlim, auto=False)
        self.axes.set_ylim(self.ylim, auto=False)
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

    def add_threshold_line(self, thr):
        thr_line = self.axes.axvline(thr, color="#000000")
        self.axes.draw_artist(thr_line)
        self.blit(self.axes.bbox)

    def add_grayed_scatter(self, data, data2):
        colors = "#BBBBBB"
        patches = self.axes.scatter(data, data2, color=colors,)
        self.axes.draw_artist(patches)
        self.blit(self.axes.bbox)

    @repeatatable_plot
    def make_box_plot(self, data, x_var, y_var,  xlabel, ylabel, xticks_labels, ylims=None, intercet=None):



        if x_var is None:
            data_list = [data[y_var]]
            label_nums = [0]
        else:
            data_list = []
            label_nums = list(set(data[x_var]))
            for i in label_nums:
                data_col = data[y_var][data[x_var] == i]
                data_list.append(data_col.get_values())


        sns.set_style("darkgrid")
        self.fig.clear()
        self.axes = self.fig.add_subplot(1, 1, 1)
        # Sort data and labels according to median
        x_permutation = range(1,len(label_nums)+1)
        data_labels = zip(data_list, label_nums)
        data_labels.sort(key=lambda x: np.median(x[0]))
        data_list, label_nums = zip(*data_labels)
        ticks = None
        if xticks_labels is not None:
            ticks = [xticks_labels.get(i ,"level %d" % i) for i in label_nums]

        self.axes.clear()
        self.axes.tick_params(
            'x', bottom='on', labelbottom='on', labeltop='off', top="off")
        self.axes.tick_params(
            'y', left='off', labelleft='off', labelright='on', right="on")
        self.axes.yaxis.set_label_position("right")
        self.axes.set_ylim(auto=True)
        #artists_dict = self.axes.boxplot(data, sym='gD')

        self.x_order = dict(izip(label_nums,x_permutation))
        self.x_order_i = dict(izip(x_permutation,label_nums))


        sns.boxplot(data_list, ax=self.axes, fliersize=10,
                    names=ticks, color="skyblue", widths=0.5)
        # find fliers
        for ls in self.axes.get_lines():
            if ls.get_markersize() == 10:
                ls.set_picker(5)
                poss_ids=dict()
                for x,y in izip(*ls.get_data()):
                    poss_ids.setdefault((x,y),set()).update(data.loc[(data[x_var] == self.x_order_i[x]) & (data[y_var] == y)].index)
                print poss_ids
                urls = []
                for x,y in izip(*ls.get_data()):
                    u=poss_ids[(x,y)].pop()
                    urls.append(u)
                ls.set_url(urls)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)

        # if xticks_labels is not None:
        #    self.axes.get_xaxis().set_ticklabels(xticks_labels)
        if ylims is not None:
            yspan = ylims[1] - ylims[0]
            self.axes.set_ylim(ylims[0] - 0.1 * yspan, ylims[1] + 0.1 * yspan)

        self.draw()
        if intercet is not None:
            self.add_intercept_line(intercet)
        self.back_fig = self.copy_from_bbox(self.axes.bbox)
        self.ylim = None
        self.xlim = None

    @repeatatable_plot
    def make_linked_box_plot(self, data, outcome, x_name, z_name, ylims=None):
        #TODO: change data to a dataframe
        sns.set_style("darkgrid")
        self.fig.clear()
        self.axes = self.fig.add_subplot(1, 1, 1)

        x_levels = list(data[x_name].unique())
        z_levels = list(data[z_name].unique())
        x_labels = braviz_tab_data.get_labels_dict_by_name(x_name)
        z_labels = braviz_tab_data.get_labels_dict_by_name(z_name)

        palette = sns.color_palette("deep")
        z_colors = dict(izip(z_levels, palette))

        # reorder
        x_levels.sort(reverse=False, key=lambda l: np.median(
            data[outcome][data[x_name] == l]))
        z_levels.sort(reverse=False, key=lambda l: np.median(
            data[outcome][data[z_name] == l]))

        log = logging.getLogger(__name__)
        if log.isEnabledFor(logging.DEBUG):
            for i in x_levels:
                log.debug(
                    "%s %s", i, np.median(data[outcome][data[x_name] == i]))

        box_width = 0.75
        box_pad = 0.15
        group_pad = 0.5
        group_width = len(z_levels) * box_width + box_pad * (len(z_levels) - 1)

        # print "levels"
        labels = []
        colors = []
        values = []
        positions = []
        positions_dict = {}
        fliers_x_dict = {}

        for ix, iz in itertools.product(xrange(len(x_levels)), xrange(len(z_levels))):
            x = x_levels[ix]
            z = z_levels[iz]
            x_lab = x_labels[x]
            z_lab = z_labels[z]
            labels.append("\n".join((x_lab, z_lab)))
            colors.append(z_colors[z])
            vals = data[outcome][(data[x_name] == x) & (data[z_name] == z)]
            values.append(vals)
            pos = box_width / 2 + \
                (group_width + group_pad) * ix + (box_width + box_pad) * iz
            positions.append(pos)
            positions_dict[(x, z)] = pos
            fliers_x_dict[float(pos)] = (x, z)

        sns.boxplot(values, ax=self.axes, names=labels, color=colors,
                    fliersize=10, widths=box_width, positions=positions)

        # find outliers
        for ls in self.axes.get_lines():
            if ls.get_markersize() == 10:
                ls.set_picker(5)
                poss_ids = dict()
                for i,y in izip(*ls.get_data()):
                    x,z = fliers_x_dict[i]
                    poss_ids.setdefault((i,y),set()).update(
                        data.loc[(data[x_name] == x) & (data[z_name] == z) & (data[outcome] == y)].index
                    )
                urls = []
                for i,y in izip(*ls.get_data()):
                    urls.append(poss_ids[(i,y)].pop())
                ls.set_url(urls)
        self.axes.set_ylabel(outcome)
        if ylims is not None:
            yspan = ylims[1] - ylims[0]
            self.axes.set_ylim(ylims[0] - 0.1 * yspan, ylims[1] + 0.1 * yspan)
        self.draw()
        self.back_fig = self.copy_from_bbox(self.axes.bbox)

        self.x_order = positions_dict
        self.fliers_x_dict = fliers_x_dict

    @repeatatable_plot
    def make_diagnostics(self, residuals, fitted):
        import matplotlib.gridspec as gridspec
        gs = gridspec.GridSpec(1, 2, width_ratios=(2, 1))
        sns.set_style("darkgrid")
        self.fig.clear()
        self.axes = self.fig.add_subplot(gs[1])
        self.axes.clear()
        self.axes.tick_params(
            'x', bottom='on', labelbottom='on', labeltop='off', top='off')
        self.axes.tick_params(
            'y', left='off', labelleft='off', labelright='off', right="off")
        self.axes.yaxis.set_label_position("right")
        self.axes.set_ylim(auto=True)
        # self.axes.set_ylabel("Residuals")
        self.axes.set_xlabel("Frequency")
        self.axes.hist(
            residuals, color="#2ca25f", bins=20, orientation="horizontal")

        self.axes2 = self.fig.add_subplot(gs[0], sharey=self.axes)
        self.axes2.scatter(fitted, residuals, s=20, color="#2ca25f")
        self.axes2.tick_params(
            'x', bottom='on', labelbottom='on', labeltop='off', top='off')
        self.axes2.tick_params(
            'y', left='on', labelleft='on', labelright='off', right="off")
        self.axes2.set_ylabel("Residuals")
        self.axes2.set_xlabel("Fitted")
        self.axes2.yaxis.set_label_position("left")
        self.axes2.axhline(color='k')
        self.draw()
        self.back_fig = self.copy_from_bbox(self.axes.bbox)
        self.x_order = None

    def add_subject_points(self, x_coords, y_coords, z_coords=None, color=None, urls=None):
        # print "adding subjects"
        # self.restore_region(self.back_fig)
        self.redraw_last_plot()
        if self.x_order is not None:
            if isinstance(self.x_order, dict):
                if z_coords is not None:
                    x_coords = map(self.x_order.get, izip(x_coords, z_coords))
                else:
                    x_coords = map(self.x_order.get, x_coords)
            else:
                raise Exception("deprecated")
        if color is None:
            color = "black"
        collection = self.axes.scatter(
            x_coords, y_coords, marker="o", s=120, edgecolors=color, urls=urls, picker=5, zorder=10)
        collection.set_facecolor('none')

        self.axes.draw_artist(collection)
        # self.blit(self.axes.bbox)
        self.draw()
        self.back_fig = self.copy_from_bbox(self.axes.bbox)

    def add_intercept_line(self, ycoord):
        self.axes.axhline(ycoord)
        self.draw()
        self.back_fig = self.copy_from_bbox(self.axes.bbox)

    def generate_tooltip_event(self, e):
        # print type(e.artist)
        if type(e.artist) == matplotlib.lines.Line2D:
            urls = e.artist.get_url()
            # print e.ind
            ind = e.ind
            if hasattr(ind, "__iter__"):
                ind = ind[0]
            u=urls[ind]
            self.box_outlier_pick_signal.emit(
                str(u), (e.mouseevent.x, self.height() - e.mouseevent.y))
        elif type(e.artist) == matplotlib.collections.PathCollection:
            if e.artist.get_urls()[0] is None:
                return
            ind = e.ind
            if hasattr(ind, "__iter__"):
                ind = ind[0]

            subj = str(e.artist.get_urls()[ind])
            self.scatter_pick_signal.emit(
                subj, (e.mouseevent.x, self.height() - e.mouseevent.y))

        else:
            return

    def mouse_move_event_handler(self, event):
        # to avoid interference with draggable legend
        # self.pick(event)
        legend = self.axes.get_legend()
        if (legend is not None) and (legend.legendPatch.contains(event)[0] == 1):
            pass
            # print "in legend"
        else:
            self.pick(event)


class ContextVariablesPanel(QtGui.QGroupBox):

    """
    A panel that displays and allows to edit variables for a given subject.

    The context menu of the panel allows the user to select variables and to make some of them editable.
    In this case a *save changes* button will also be displayed. Pressing it will cause the changes to be
    written into the databases

    Args:
        parent (QObject) : Qt parent
        title (str) : Title for the widget
        initial_variable_idxs (list) : List of variable indices to display at start
        initial_subject : Id of the initial subject whose variable values will be displayed
        app : Optional, an application with the ``save_screenshot`` and ``get_state_dict`` method.
            In this case a scenario will be automatically created whenever a variable is first modified.
        sample (list) : list of subjects. This sample will be passed on to the variable select dialog deployed
            by the panel.

    """

    def __init__(self, parent, title="Context", initial_variable_idxs=None, initial_subject=None, app=None,
                 sample=None):
        super(ContextVariablesPanel, self).__init__(parent)

        if initial_variable_idxs is None or initial_subject is None:

            config = config_file.get_apps_config()
            if initial_variable_idxs is None:
                var_names = config.get_default_variables().values()
                initial_variable_idxs = [
                    braviz_tab_data.get_var_idx(v) for v in var_names]
            if initial_subject is None:
                initial_subject = config.get_default_subject()

        self.setTitle(title)
        self.setToolTip(
            "Right click to select context variables, and to make them editable")
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.layout = QtGui.QHBoxLayout(self)
        self.setLayout(self.layout)
        self.app = app
        self.sample = sample
        if self.sample is None:
            self.sample = braviz_tab_data.get_subjects()

        self.layout.setContentsMargins(7, 2, 7, 2)
        self.customContextMenuRequested.connect(self.create_context_menu)

        size_policy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Maximum)
        # size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(1)
        self.setSizePolicy(size_policy)
        #self.setMaximumSize(QtCore.QSize(16777215, 56))
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setObjectName("context_frame")
        # self.setFrameStyle(self.NoFrame)

        # internal variables
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
        """
        Sets a new set of variables for the panel

        Args:
            variables (list) : List of variable indices
            editables (dict) : Dictionary mapping varible indices to booleans that indicate if a variable should
                be modifiable by the user
        """
        self.__context_variable_codes = list(variables)
        self.__context_variable_names = dict(
            (idx, get_var_name(idx)) for idx in self.__context_variable_codes)
        self.__is_nominal = dict(
            (idx, is_variable_nominal(idx)) for idx in self.__context_variable_codes)
        self.__labels_dict = dict((idx, get_labels_dict(idx)) for idx in self.__context_variable_codes if
                                  self.__is_nominal[idx])
        self.__internal_df = get_data_frame_by_index(
            self.__context_variable_codes)
        self.__values_widgets = []
        if editables is None:
            self.__editables_dict = dict((idx, False) for idx in variables)
        else:
            self.__editables_dict = editables
        self._reset_internal_widgets()

    def get_variables(self):
        """
        Get a list of current variable codes
        """
        return self.__context_variable_codes

    def get_editables(self):
        """
        Get a list of tuples (var_code, editable) indicating which variables are editable
        """
        return self.__editables_dict.items()

    def _reset_internal_widgets(self):
        # clear layout
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
            # add separator
            if not first:
                self.layout.addStretch()
            else:
                first = False
            # add label
            label = QtGui.QLabel("%s : " % self.__context_variable_names[idx])
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.__context_labels.append(label)
            self.layout.addWidget(label)
            # add value
            if self.__editables_dict.get(idx) is True:
                value_widget = self._get_editable_widget(idx)
                any_editable = True
            else:
                value_widget = self._get_read_only_widget(idx)
            self.layout.addWidget(value_widget)
            self.__values_widgets.append(value_widget)
        if any_editable is True:
            self.__save_changes_button = QtGui.QPushButton("Save")
            self.__save_changes_button.setEnabled(False)
            self.__save_changes_button.clicked.connect(
                self._save_changes_into_db)
            self.layout.addWidget(self.__save_changes_button)
        return

    def _get_read_only_widget(self, idx):
        value_widget = QtGui.QLabel("XXXXXXX")
        value_widget.setFrameShape(QtGui.QFrame.Box)
        value_widget.setFrameShadow(QtGui.QFrame.Raised)
        # value_widget.setContentsMargins(7,7,7,7)
        value_widget.setMargin(7)
        value_widget.setAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setPointSize(11)
        value_widget.setFont(font)
        value_widget.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        value_widget.setCursor(QtCore.Qt.IBeamCursor)
        # calculate maximum width
        if is_variable_nominal(idx):
            lens = [(x, len(x))
                    for x in self.__labels_dict[idx].itervalues() if x is not None]
            if len(lens) == 0:
                longest = "<Unknown>"
            else:
                longest = max(lens, key=lambda x: x[1])[0]
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

    def _get_editable_widget(self, idx):
        if self.__is_nominal.get(idx) is True:
            value_widget = QtGui.QComboBox()
            for i, lbl in self.__labels_dict[idx].iteritems():
                if not np.isnan(float(i)):
                    value_widget.addItem(lbl, i)
            value_widget.insertSeparator(value_widget.count())
            value_widget.addItem("<Unknown>", float("nan"))
            value_widget.currentIndexChanged.connect(self._enable_save_changes)
        else:
            value_widget = QtGui.QDoubleSpinBox()
            minim, maxim = get_min_max_values(idx)
            value_widget.setMaximum(10 * maxim)
            value_widget.setMinimum(-10 * maxim)
            value_widget.setSingleStep((maxim - minim) / 20)
            value_widget.valueChanged.connect(self._enable_save_changes)
        font = QtGui.QFont()
        font.setPointSize(11)
        value_widget.setFont(font)
        return value_widget

    def set_subject(self, subject_id):
        """
        Set the current subject to which variable values are associated

        Args:
            subject_id : Subject id
        """
        values = self.__internal_df.loc[int(subject_id)]
        for i, idx in enumerate(self.__context_variable_codes):
            try:
                value = values[self.__context_variable_names[idx]]
            except KeyError:
                value = float("nan")
            # print self.__context_variable_names[idx], value
            value_widget = self.__values_widgets[i]
            if self.__is_nominal[idx]:

                if isinstance(value_widget, QtGui.QLabel):
                    label = self.__labels_dict[idx].get(value, "?")
                    if label is None:
                        label = "?"
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
        """
        Create a context menu which gives the user the option to open a dialog to select variables

        Args:
            pos : Position of event
        """
        from braviz.interaction.qt_dialogs import ContextVariablesSelectDialog
        global_pos = self.mapToGlobal(pos)
        change_action = QtGui.QAction("Change Variables", None)
        menu = QtGui.QMenu()
        menu.addAction(change_action)

        def change_variables(*args):
            context_change_dialog = ContextVariablesSelectDialog(current_subject=self.__curent_subject,
                                                                 variables_list=self.__context_variable_codes,
                                                                 editables_dict=self.__editables_dict,
                                                                 sample=self.sample)
            context_change_dialog.exec_()
            self.set_variables(
                self.__context_variable_codes, self.__editables_dict)
            self.set_subject(self.__curent_subject)

        change_action.triggered.connect(change_variables)
        menu.addAction(change_action)
        menu.exec_(global_pos)

    def _enable_save_changes(self, *args):

        if self.__save_changes_button is None:
            return
        self.__save_changes_button.setEnabled(True)

    def _save_changes_into_db(self):

        for i, idx in enumerate(self.__context_variable_codes):
            if self.__editables_dict[idx] is True:
                value_widget = self.__values_widgets[i]
                if isinstance(value_widget, QtGui.QDoubleSpinBox):
                    value = float(value_widget.value())
                elif isinstance(value_widget, QtGui.QComboBox):
                    value = value_widget.itemData(value_widget.currentIndex())
                    value = value.toDouble()[0]
                    if np.isnan(float(value)):
                        value = None
                    else:
                        value = int(value)
                # update value
                braviz_tab_data.updata_variable_value(
                    int(idx), self.__curent_subject, value)
                # update internal
                var_name = self.__context_variable_names[idx]
                self.__internal_df[var_name][
                    int(self.__curent_subject)] = value
                # check if scenarios exists for this variable
                if braviz_user_data.count_variable_scenarios(int(idx)) == 0 and self.app is not None:
                    # save scenario
                    name = "<AUTO_%s>" % self.__context_variable_names[idx]
                    desc = "Created automatically when saving values for variable %s" % self.__context_variable_names[
                        idx]
                    data = self.app.get_state_dict()
                    app = data["meta"]["application"]
                    data_s = cPickle.dumps(data, 2)
                    scn_idx = braviz_user_data.save_scenario(
                        app, name, desc, data_s)
                    # link
                    braviz_user_data.link_var_scenario(int(idx), scn_idx)
                    # save screenshot
                    self.app.save_screenshot(scn_idx)

        self.__save_changes_button.setEnabled(0)
        # print idx_value_tuples

    def set_sample(self, new_sample):
        """
        Set the sample used in the variable selection dialogs

        Args:
            new_sample (list) : List of subject ids
        """
        self.sample = list(new_sample)

if __name__ == "__main__":
    app = QtGui.QApplication([])
    context = ContextVariablesPanel(None)
    context.show()
    app.exec_()
