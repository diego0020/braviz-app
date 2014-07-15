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

class TimeseriesPlot(FigureCanvas):
    #These signals return the id of the point where the action occured
    point_picked = QtCore.pyqtSignal(str)
    context_requested = QtCore.pyqtSignal(str)
    def __init__(self,parent=None,dpi=100):
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
        #self.mpl_connect('motion_notify_event', self.mouse_move_handler)
        #self.mpl_connect("pick_event", self.show_tooltip)
        #self.mpl_connect("button_press_event",self.mouse_click_handler)

        #internal_data
        self.spm = None
        self.bold = None

        self.colors_dict = None
        self.__title = None

        self.axes.tick_params('y', left='off', right='off', labelleft='off', labelright='off')
        self.axes.tick_params('x', top='off', bottom='on', labelbottom='on', labeltop='off')
        self.axes.set_xlabel("Time (s.)")
        self.axes.set_ylim(-1.5,1.5)

    def clear(self):
        self.axes.clear()

    def set_bold(self,bold_image):
        self.bold = bold_image

    def set_spm(self,spm_struct):
        self.spm = spm_struct

    def draw_bold_signal(self,coordinates):
        pass

    def add_perm_bold_signal(self,coordinates):
        pass

    def draw_contrast(self,contrast_index):
        pass

