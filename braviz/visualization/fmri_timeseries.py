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


from __future__ import division, print_function

__author__ = 'Diego'

from PyQt4 import QtCore
from PyQt4 import QtGui

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import braviz

import numpy as np
from scipy import io as sio
import seaborn as sns
import logging


class TimeseriesPlot(FigureCanvas):
    # These signals return the id of the point where the action occured
    point_picked = QtCore.pyqtSignal(str)
    context_requested = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, dpi=100):
        fig = Figure(figsize=(5, 5), dpi=dpi, tight_layout=True)
        self.fig = fig
        self.axes = fig.add_subplot(111)
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(
            self, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.updateGeometry()
        palette = self.palette()
        fig.set_facecolor(palette.background().color().getRgbF()[0:3])
        self.axes.margins(0, 0, tight=True)
        # observers
        self.setMouseTracking(True)
        #self.mpl_connect('motion_notify_event', self.mouse_move_handler)
        #self.mpl_connect("pick_event", self.show_tooltip)
        # self.mpl_connect("button_press_event",self.mouse_click_handler)

        # internal_data
        self.spm = None
        self.bold = None
        self.volumes_times = None
        self.experiment_time = None
        self.__contrast = None

        self.__condition_colors = None
        self.__background = None
        self.__old_size = None

        self.__frozen_points_signals = {}
        self.__frozen_colors = None
        self.__frozen_groups = None
        self.__frozen_group2color = None
        self.__frozen_aggregration = False

        self.axes.tick_params(
            'y', left='off', right='off', labelleft='off', labelright='off')
        self.axes.tick_params(
            'x', top='off', bottom='on', labelbottom='on', labeltop='off')
        self.axes.set_xlabel("Time (s.)")
        self.axes.set_ylim(-2, 2, auto=False)

    def clear(self):
        self.axes.clear()
        self.draw()

    def _set_bold(self, bold_image):
        if bold_image is None:
            self.volumes_times = None
            self.bold = None
            return
        self.bold = bold_image.get_data()
        self.volumes_times = np.arange(0, self.bold.shape[3],dtype=np.float)
        self.volumes_times *= self.spm.tr
        self.volumes_times += self.spm.tr / 2  # middle of acquisition
        # HACK
        if braviz.readAndFilter.PROJECT == "kmc40":
            # ignore first volume
            self.bold = self.bold[:, :, :, 1:]
            self.volumes_times = self.volumes_times[1:]
        self.axes.set_xlim(0, self.spm.tr + self.volumes_times[-1], auto=False)

    def _set_spm(self, spm_struct):
        self.spm = spm_struct
        if self.spm is None:
            return
        self.experiment_time = spm_struct.get_time_vector()
        self.__condition_colors = sns.color_palette(
            "Dark2", len(spm_struct.conditions))

    def set_spm_and_bold(self, spm_file, bold_image):
        self._set_spm(spm_file)
        self._set_bold(bold_image)

    def draw_bold_signal(self, coordinates):
        if self.bold is None or coordinates is None:
            return
        # draw background
        current_size = self.axes.bbox.width, self.axes.bbox.height
        if current_size != self.__old_size:
            self.draw_background()
        else:
            self.restore_region(self.__background)
        self.axes.set_ylim(-2, 2, auto=False)
        self.axes.set_xlim(0, self.spm.tr + self.volumes_times[-1], auto=False)

        coordinates = np.array(coordinates).astype(np.int)
        signal = self.bold[coordinates[0], coordinates[1], coordinates[2], :]
        normalized_signal = (signal - np.mean(signal)) / np.std(signal)
        bold_artist = self.axes.plot(
            self.volumes_times, normalized_signal, c="k", zorder=10)
        for a in bold_artist:
            self.axes.draw_artist(a)
        self.blit(self.axes.bbox)
        pass

    def add_frozen_bold_signal(self, url, coordinates, bold=None):
        if bold is None:
            bold = self.bold
        elif braviz.readAndFilter.PROJECT == "kmc40":
            # HACK
            # ignore first volume
            bold = bold[:, :, :, 1:]
        signal = bold[coordinates[0], coordinates[1], coordinates[2], :]
        normalized_signal = (signal - np.mean(signal)) / np.std(signal)
        self.__frozen_points_signals[url] = normalized_signal
        self.draw_background()
        pass

    def remove_frozen_bold_signal(self, url):
        del self.__frozen_points_signals.clear[url]
        self.draw_background()

    def clear_frozen_bold_signals(self):
        self.__frozen_points_signals.clear()
        self.draw_background()

    def draw_frozen_bold_signals(self):
        dark_gray = (0.2, 0.2, 0.2)
        if self.__frozen_aggregration is False:
            for k, v in self.__frozen_points_signals.iteritems():
                # adjust length
                vn = self.normalize_time_signal_length(v)
                if self.__frozen_colors is None:
                    color = dark_gray
                else:
                    color = self.__frozen_colors(k)
                self.axes.plot(
                    self.volumes_times, vn, color=color, zorder=5, alpha=0.4, url=k)
        else:
            if self.__frozen_groups is None:
                n_signals = [self.normalize_time_signal_length(
                    s) for s in self.__frozen_points_signals.itervalues()]
                print(len(n_signals))
                if len(n_signals) > 0:
                    sns.tsplot(n_signals, time=self.volumes_times,
                               legend=False, color="k", ax=self.axes, ci=(95, 68))
            else:
                grouped_signals = dict()
                for k, s in self.__frozen_points_signals.iteritems():
                    g = self.__frozen_groups(k)
                    grouped_signals.setdefault(g, []).append(
                        self.normalize_time_signal_length(s))
                for g, ss in grouped_signals.iteritems():
                    color = self.__frozen_group2color[g]
                    if len(ss) > 0:
                        sns.tsplot(
                            ss, time=self.volumes_times, legend=False, color=color, ax=self.axes, ci=(95, 68))

    def normalize_time_signal_length(self, signal):
        if len(signal) > len(self.volumes_times):
            signal = signal[:len(self.volumes_times)]
        elif len(signal) < len(self.volumes_times):
            signal2 = np.zeros(len(self.volumes_times))
            signal2[:len(signal)] = signal
            signal = signal2
        return signal

    def set_frozen_colors(self, color_fun):
        self.__frozen_colors = color_fun
        self.draw_background()

    def set_frozen_groups_and_colors(self, groups, colors):
        self.__frozen_groups = groups
        self.__frozen_group2color = colors

    def set_frozen_aggregration(self, aggregrate):
        self.__frozen_aggregration = aggregrate
        self.draw_background()

    def highlight_frozen_bold(self, url):
        from matplotlib import patheffects
        # draw background
        current_size = self.axes.bbox.width, self.axes.bbox.height
        if current_size != self.__old_size:
            self.draw_background()
        else:
            self.restore_region(self.__background)
        self.axes.set_ylim(-2, 2, auto=False)
        self.axes.set_xlim(0, self.spm.tr + self.volumes_times[-1], auto=False)
        if self.__frozen_colors is None:
            color = "k"
        else:
            color = self.__frozen_colors(url)
        signal = self.__frozen_points_signals[url]
        artist = self.axes.plot(self.volumes_times, signal, c=color, zorder=10, linewidth=3,
                                path_effects=[patheffects.withStroke(linewidth=5, foreground="w")])

        for a in artist:
            self.axes.draw_artist(a)
        self.blit(self.axes.bbox)

    def set_contrast(self, contrast):
        self.__contrast = contrast
        self.draw_background()

    def draw_background(self):
        self.draw_contrast()
        self.draw_frozen_bold_signals()
        self.draw()
        self.__background = self.copy_from_bbox(self.axes.bbox)
        current_size = self.axes.bbox.width, self.axes.bbox.height
        self.__old_size = current_size

    def draw_contrast(self):
        if self.spm is None or self.__contrast is None:
            return
        cont = self.spm.contrasts[self.__contrast]
        self.axes.clear()
        self.axes.set_ylim(-2, 2, auto=False)
        if self.volumes_times is not None:
            self.axes.set_xlim(
                0, self.spm.tr + self.volumes_times[-1], auto=False)
        self.axes.set_xlabel("Time (s.)")

        design = cont.design
        for i, v in enumerate(design):
            if v != 0:
                c = self.__condition_colors[i]
                blocks = self.spm.get_condition_block(i) * v
                self.axes.plot(
                    self.experiment_time, blocks, color=c, zorder=1, label=self.spm.conditions[i].name)
                self.axes.fill_between(self.experiment_time, blocks, alpha=0.5, color=c,
                                       zorder=1)
        self.axes.legend()

    def export_frozen_signals(self, filename):
        # create numpy object array
        obj_array = np.zeros(
            (len(self.__frozen_points_signals),), dtype=np.object)
        for i, (k, v) in enumerate(self.__frozen_points_signals.iteritems()):
            obj = {"subj": k[0], "coordinates": k[1:], "signal": v}
            obj_array[i] = obj
        output = {"signals": obj_array, "time": self.volumes_times}
        sio.savemat(filename, output)
