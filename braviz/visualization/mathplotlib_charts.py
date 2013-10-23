__author__ = 'Diego'
import matplotlib
matplotlib.use('TkAgg')

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# implement the default mpl key bindings
from matplotlib.backend_bases import key_press_handler
import math
import random
from matplotlib.figure import Figure

import Tkinter as Tk

class BarPlot():
    def __init__(self):
        f = Figure( dpi=100,tight_layout=True,facecolor='w',frameon=False,edgecolor='r')
        a = f.gca(axisbg='w')
        t = range(1)
        s = [50 for i in t]
        a.axhline()
        colors = [(random.random(), random.random(), random.random()) for i in t]
        a.bar(t, s, color=colors,align='center')

        self.figure=f
        self.axis=a
        self.axis.set_xlim(-0.5,0.5)
        self.axis.set_xticks((0,))
        self.axis.set_xticklabels(('123',),size='small')
    def get_widget(self,master,**kwargs):
        # a tk.DrawingArea
        canvas = FigureCanvasTkAgg(self.figure, master=master)

        def on_key_event(event):
            print('you pressed %s' % event.key)
            key_press_handler(event, canvas)

        canvas.mpl_connect('key_press_event', on_key_event)

        self.canvas = canvas
        widget=self.canvas.get_tk_widget()
        widget.configure(bd=4,bg='white',highlightcolor='red',highlightthickness=0,**kwargs)
        return widget

    def show(self):
        self.canvas.show()


    def set_y_title(self,title):
        axis=self.axis
        axis.set_ylabel(title,size='small')
    def set_y_limits(self,button,top):
        self.axis.set_ylim(button,top)
        labels=self.axis.get_yticklabels()
        for lab in labels:
            lab.set_fontsize('small')