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
import matplotlib.pyplot as plt
import Tkinter as Tk

class BarPlot():
    def __init__(self):
        f = Figure( dpi=100,tight_layout=True,facecolor='w',frameon=False,edgecolor='r')
        #f = plt.figure()
        a = f.gca(axisbg='w')

        self.figure=f
        self.axis=a
        self.axis.set_xlim(-0.5,0.5)
        self.axis.set_xticks((0,))
        self.axis.set_xticklabels(('nothing',),size='small')
        self.hlines = []
        self.y_limits=(0,100)
        self.y_title=''
        self.right_y=False
        self.bar_heights=[0]
        self.bar_names=['nothing']
        self.bar_positions=[0]
        self.bars=None
        self.color_function=lambda x:(1,1,0)
        self.current_xcoord=0
        self.highlight=None





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
        def print_events(event):
            self.current_xcoord=event.xdata
            #print event.xdata, event.ydata
        cid = self.figure.canvas.mpl_connect('motion_notify_event', print_events)
        def generate_tk_event(event=None):
            widget.event_generate('<<BarSelected>>')

        cid2 = self.figure.canvas.mpl_connect('button_press_event', generate_tk_event)
        return widget

    def show(self):
        self.canvas.show()


    def set_y_title(self,title):
        self.y_title=title
        self.axis.set_ylabel(self.y_title, size='small')

    def set_y_limits(self,button,top,right=False):
        self.y_limits=(button,top)
        self.right_y=right
        self.axis.set_ylim(self.y_limits[0], self.y_limits[1])
    def set_lines(self,lines,dashes):
        self.hlines=[]
        for pos,dash in zip(lines,dashes):
            ls='-'
            if dash is True:
                ls=':'
            self.hlines.append({'y':pos, 'ls':ls, 'color':'k'})
    def set_data(self,values,codes):
        self.bar_heights=values
        self.bar_names=codes
    def set_color_fun(self,color_function):
        self.color_function=color_function
    def paint_bar_chart(self):
        a=self.axis
        a.cla()
        #y axis
        self.axis.set_ylim(self.y_limits[0], self.y_limits[1])
        labels = self.axis.get_yticklabels()
        for lab in labels:
            lab.set_fontsize('small')
        if self.right_y is True:
            yax = self.axis.get_yaxis()
            yax.tick_right()
            yax.set_label_position('right')
        for li in self.hlines:
            a.axhline(**li)
        a.axhline(color='k')
        a.set_ylabel(self.y_title,size='small')
        #x axis
        if len(self.bar_heights)==0:
            bar_positions = [0]
            a.set_xlim(-0.5, 0.5)
            self.bar_names=['']
        else:
            bar_positions = range(len(self.bar_heights))
            a.set_xlim(-0.5, len(bar_positions) - 0.5)



        self.bar_positions = bar_positions
        a.set_xticks(bar_positions)
        #a.set_xticklabels(self.bar_names, size='small', rotation='horizontal')
        a.set_xticklabels(self.bar_names, size='small', rotation='horizontal',visible=False)
        if len(self.bar_heights) == 0:
            self.show()
            return
        colors = [self.color_function(x) for x in self.bar_heights]
        patches=a.bar(bar_positions,self.bar_heights, color=colors, align='center')
        if self.highlight is not None:
            highlighted_rect=patches[self.highlight]
            highlighted_rect.set_linewidth(4)
            highlighted_rect.set_edgecolor('#FAFA3E')
        self.show()
        self.bars=patches
    def change_bars(self,new_heights):
        if self.bars is None:
            return
        self.bars.remove()
        self.bar_heights=new_heights
        colors = [self.color_function(x) for x in self.bar_heights]
        self.bars=self.axis.bar(self.bar_positions,self.bar_heights, color=colors, align='center')
        self.show()
    def get_current_name(self):
        if self.current_xcoord is None:
            return None
        bar_names=self.bar_names
        idx=round(self.current_xcoord)
        idx = int(idx)
        if 0 <= idx < len(bar_names):
            return bar_names[idx]
        return None
    def set_higlight_index(self,index):
        self.highlight=index