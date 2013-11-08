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
from itertools import izip


class BarPlot():
    def __init__(self,tight=True):
        #f = Figure( dpi=100,tight_layout=True,facecolor='w',frameon=False,edgecolor='r')
        f = Figure( dpi=None,tight_layout=tight,facecolor='w',frameon=False,edgecolor='r')
        #f = Figure( dpi=None,facecolor='w',frameon=False,edgecolor='r')
        #f = plt.figure()
        a = f.gca(axisbg='w')

        self.figure=f
        self.axis=a
        self.axis.set_xlim(-0.5,0.5)
        self.axis.set_xticks((0,))
        #self.axis.set_xticklabels(('nothing',))
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
        self.style='bars'
        self.yerror=0
        self.back_bars=None
        self.back_error=0
        self.widget=None
        self.resizing = None
        self.tight=tight

    def set_back_bars(self,back_bars,back_error=0):
        self.back_bars=back_bars
        self.back_error=back_error
    def change_style(self,new_style):
        """must be 'bars' or 'markers'"""
        if new_style not in ('bars','markers'):
            return
        else:
            self.style=new_style


    def get_widget(self,master,**kwargs):
        # a tk.DrawingArea
        if self.widget is not None:
            return self.widget
        canvas = FigureCanvasTkAgg(self.figure, master=master)

        def on_key_event(event):
            print('you pressed %s' % event.key)
            key_press_handler(event, canvas)

        canvas.mpl_connect('key_press_event', on_key_event)
        #canvas.mpl_connect('resize_event', resize_event_handler)
        self.canvas = canvas
        widget=canvas.get_tk_widget()
        widget.configure(bd=4,bg='white',highlightcolor='red',highlightthickness=0,**kwargs)

        if self.tight is True:
            self.resizing = None
            def resize_event_handler(event=None):
                #print "rererererere"
                #self.show()
                if self.resizing is not None:
                    widget.after_cancel(self.resizing)
                self.resizing = widget.after(1000, self.show)

            bind_id = widget.bind('<Configure>', resize_event_handler, '+')
            #def unbind_conf(event=None):
            #    print "unbinding"
            #    widget.unbind('<Configure>',bind_id)
            #widget.bind('<Unmap>',unbind_conf)
        widget.focus()
        self.widget=widget
        return widget

        def update_mouse_pos(event):
            self.current_xcoord=event.xdata
            #print event.xdata, event.ydata
        cid = self.figure.canvas.mpl_connect('motion_notify_event', update_mouse_pos)
        def generate_tk_event(event=None):
            widget.event_generate('<<BarSelected>>')

        cid2 = self.figure.canvas.mpl_connect('button_press_event', generate_tk_event)
        self.widget=widget
        return widget

    def show(self):
        self.resizing = None
        self.widget.update_idletasks()
        self.figure.subplots_adjust(bottom=0.0, top=1.0,hspace=0)
        self.canvas.show()

        #print "wolololo"
        #self.widget.after(1000, self.show)


    def set_y_title(self,title):
        self.y_title=title
        self.axis.set_ylabel(self.y_title)

    def set_y_limits(self,button,top,right=False):
        self.y_limits=(button,top)
        self.right_y=right
        self.axis.set_ylim(self.y_limits[0], self.y_limits[1])
    def set_lines(self,lines,dashes):
        self.hlines=[]
        for pos,dash in izip(lines,dashes):
            ls='-'
            if dash is True:
                ls=':'
            self.hlines.append({'y':pos, 'ls':ls, 'color':'k'})
    def set_data(self,values,codes,error=None):
        self.bar_heights=values
        self.bar_names=codes
        if error is not None:
            if hasattr(error,'__iter__') and len(error)==len(values):
                self.yerror=error
            elif np.isfinite(error):
                self.yerror = error
        else:
            self.yerror=0

    def set_color_fun(self,color_function):
        self.color_function=color_function
    def paint_bar_chart(self):
        a=self.axis
        a.cla()
        #y axis
        self.axis.set_ylim(self.y_limits[0], self.y_limits[1])
        labels = self.axis.get_yticklabels()
        #for lab in labels:
        #    lab.set_fontsize('small')
        if self.right_y is True:
            yax = self.axis.get_yaxis()
            yax.tick_right()
            yax.set_label_position('right')
        for li in self.hlines:
            a.axhline(**li)
        a.axhline(color='k')
        #a.set_ylabel(self.y_title,size='small')
        a.set_ylabel(self.y_title)
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
        #a.set_xticklabels(self.bar_names, rotation='horizontal',visible=False)
        a.set_xticklabels('',visible=False)
        a.set_xlabel('',visible=False)
        if len(self.bar_heights) == 0:
            self.show()
            return
        colors = [self.color_function(x) for x in self.bar_heights]
        if self.style == 'bars':
            if self.back_bars is not None:
                back_heights,back_widths=zip(*self.back_bars)
                back_colors=map(self.color_function,back_heights)
                back_positions=np.cumsum([0]+list(back_widths))
                back_positions=back_positions[:-1]
                back_positions=np.subtract(back_positions,0.8)
                back_positions=np.add(back_positions,[0,1,2])
                offsets=[0]*back_widths[0]+[1]*back_widths[1]+[2]*back_widths[2]
                back_widths=np.add(back_widths,0.6)
                bar_positions=np.add(bar_positions,offsets)
                a.set_xticks(bar_positions)
                a.set_xlim(-1, len(bar_positions)+2)
                a.bar(back_positions,back_heights,color=back_colors,width=back_widths,alpha=0.5,yerr=self.back_error)
            patches=a.bar(bar_positions,self.bar_heights, color=colors, align='center',yerr=self.yerror)
            if self.highlight is not None:
                highlighted_rect = patches[self.highlight]
                highlighted_rect.set_linewidth(4)
                highlighted_rect.set_edgecolor('#FF7F00')
        else:
            edge_colors = ['#000000'] * len(self.bar_heights)
            sizes=[40]*len(self.bar_heights)
            linewidths=[1.0]*len(self.bar_heights)
            if self.highlight is not None:
                edge_colors[self.highlight]='#FF7F00'
                sizes[self.highlight]=80
                linewidths[self.highlight]=2
            patches = a.scatter(bar_positions, self.bar_heights, c=colors, marker='s', s=sizes,edgecolors=edge_colors,linewidths=linewidths)
            if self.yerror is not 0:
                a.errorbar(bar_positions, self.bar_heights, yerr=self.yerror, fmt=None)

        #a.autoscale_view()
        self.bars=patches
        self.show()
    def change_bars(self,new_heights):
        """doesn't do highlight"""
        if self.bars is None:
            return
        self.bars.remove()
        self.bar_heights=new_heights
        colors = [self.color_function(x) for x in self.bar_heights]
        a=self.axis
        bar_positions=self.bar_positions
        if self.style == 'bars':
            patches=a.bar(bar_positions,self.bar_heights, color=colors, align='center')
        else:
            patches=a.scatter(bar_positions,self.bar_heights,c=colors,marker='s',s=40)
        self.bars=patches
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


class ScatterPlot():
    def __init__(self,tight=True):
        f = Figure(tight_layout=tight, facecolor='w', frameon=False, edgecolor='r')
        a = f.gca(axisbg='w')
        self.figure=f
        self.axis=a
        self.widget=None
        self.x_values=[]
        self.y_values=[]
        self.x_limits=(0,1)
        self.y_limits=(0,1)
        self.reg_line= None
        self.x_label=''
        self.y_label=''
        self.tight=tight
        self.resizing=None

    def get_widget(self,master,**kwargs):
        if self.widget is not None:
            return self.widget
        canvas = FigureCanvasTkAgg(self.figure, master=master)
        self.canvas=canvas
        widget = self.canvas.get_tk_widget()
        widget.configure(bd=4, bg='white', highlightcolor='red', highlightthickness=0, **kwargs)
        def update_mouse_pos(event):
            self.current_xcoord=event.xdata
            #print event.xdata, event.ydata
        cid = self.figure.canvas.mpl_connect('motion_notify_event', update_mouse_pos)
        def generate_tk_event(event=None):
            widget.event_generate('<<ScatterClick>>')
        cid2 = self.figure.canvas.mpl_connect('button_press_event', generate_tk_event)
        self.widget = widget

        if self.tight is True:
            self.resizing = None
            def resize_event_handler(event=None):
                #print "rererererere"
                #self.show()
                if self.resizing is not None:
                    widget.after_cancel(self.resizing)
                self.resizing = widget.after(1000, self.show)

            bind_id = widget.bind('<Configure>', resize_event_handler, '+')
        widget.focus()
        return widget
    def show(self):
        self.resizing = None
        self.widget.update_idletasks()
        self.figure.subplots_adjust(bottom=0.0, top=1.0,hspace=0)
        self.canvas.show()
    def set_data(self,x_values,y_values):
        self.y_values=y_values
        self.x_values=x_values
        self.calculate_regression_line()
    def calculate_regression_line(self):
        from scipy.stats import linregress
        slope, intercept, r_value, p_value, std_err = linregress(self.x_values, self.y_values)
        def reg_line(x):
            return intercept+slope*x
        self.reg_line=reg_line

    def draw_scatter(self):
        a=self.axis
        a.cla()
        a.set_ylim(self.y_limits[0],self.y_limits[1])
        a.set_xlim(self.x_limits[0],self.x_limits[1])
        a.set_xlabel(self.x_label)
        a.set_ylabel(self.y_label)
        a.plot(self.x_values,self.y_values,'o')
        if self.reg_line is not None:
            a.plot(self.x_limits,map(self.reg_line,self.x_limits))
        a.autoscale_view()
        self.show()
    def set_limits(self,x_lim,y_lim):
        self.x_limits=x_lim
        self.y_limits=y_lim
    def set_labels(self,x_label='',y_label=''):
        self.x_label=x_label
        self.y_label=y_label
class SpiderPlot():

    def __init__(self,tight=True):
        from braviz.visualization.radar_chart import radar_factory
        f = Figure(tight_layout=tight, facecolor='w', frameon=False, edgecolor='r')
        self.figure=f
        self.widget=None
        self.N=5
        self.data_dict={}
        self.r_max=1
        self.axis_labels=None
        self.color_fun=lambda *x:'r'
        self.canvas=None


    def get_widget(self,master,**kwargs):
        if self.widget is not None:
            return self.widget
        canvas = FigureCanvasTkAgg(self.figure, master=master)
        self.canvas=canvas
        widget = self.canvas.get_tk_widget()
        widget.configure(bd=4, bg='white', highlightcolor='red', highlightthickness=0, **kwargs)
        def update_mouse_pos(event):
            self.current_xcoord=event.xdata
            #print event.xdata, event.ydata
        cid = self.figure.canvas.mpl_connect('motion_notify_event', update_mouse_pos)
        def generate_tk_event(event=None):
            widget.event_generate('<<ScatterClick>>')
        cid2 = self.figure.canvas.mpl_connect('button_press_event', generate_tk_event)
        self.widget = widget
        widget.focus()
        return widget
    def show(self):
        self.canvas.show()
    def set_data(self,data_dict,axis_labels=None):
        self.data_dict=data_dict
        #check dimensions
        N=None
        for v in data_dict.itervalues():
            if N is None:
                N=len(v)
            assert(len(v)==N)
        self.N=N
        if axis_labels is not None:
            assert (len(axis_labels)==N)
            self.axis_labels=axis_labels
        else:
            if self.axis_labels is not None and len(self.axis_labels)!= N:
                self.axis_labels=None

    def set_rmax(self,r_max):
        self.r_max=r_max
    def set_color_fun(self,color_fun):
        """colof function must take two arguments, key and values array"""
        self.color_fun=color_fun

    def draw_spider(self):
        from braviz.visualization.radar_chart import radar_factory
        theta = radar_factory(self.N, frame='polygon')
        a=self.figure.gca(axisbg='w',projection='radar')
        a.cla()

        for k,val in self.data_dict.iteritems():
            col=self.color_fun(k,val)
            a.plot(theta,val,color=col)
            a.fill(theta,val,color=col,alpha=0.15)
        a.set_rmax(self.r_max)
        a.set_rgrids(np.linspace(0,self.r_max,5)[1:],visible=False)
        a.set_rmin(0)
        if self.axis_labels is not None:
            a.set_varlabels(self.axis_labels)
        self.show()
if __name__=='__main__':
    import Tkinter as tk
    import random
    root=tk.Tk()
    bar_plot=BarPlot()
    bar_widget = bar_plot.get_widget(root, width=400, height=200)
    scatter_plot = ScatterPlot()
    scatter_widget = scatter_plot.get_widget(root, width=400, height=200)
    spider_plot = SpiderPlot()
    spider_widget = spider_plot.get_widget(root, width=400, height=200)

    bar_widget.grid(row=0, sticky="NSEW")
    scatter_widget.grid(row=1, sticky="NSEW")
    spider_widget.grid(row=2, sticky="NSEW")

    def color_fun(key,val):
        from colorbrewer import BrBG
        color_array=BrBG[10]
        return map(lambda x:x/255.0, color_array[key])
    spider_plot.set_color_fun(color_fun)
    def recalc():
        test_data=[random.randrange(1,10) for i in xrange(10)]
        bar_plot.set_data(test_data,range(10),2)
        bar_plot.set_y_limits(0,10)
        bar_plot.paint_bar_chart()

        test_data_x=[random.random() for i in xrange(10)]
        test_data_y=[random.random()*2 for i in xrange(10)]
        scatter_plot.set_limits((0,1),(0,2))
        scatter_plot.set_data(test_data_x,test_data_y)
        scatter_plot.draw_scatter()
        N=random.randrange(3,10)

        spider_test_data={}
        for i in xrange(10):
            spider_test_data[i]=[random.random() for j in xrange(N)]
        spider_plot.set_data(spider_test_data,range(N))
        spider_plot.draw_spider()

    recalc()
    button=tk.Button(root,text='redraw',command=recalc)
    button.grid(row=4)

    root.rowconfigure(0,weight=1)
    root.rowconfigure(1,weight=1)
    root.rowconfigure(2,weight=1)
    root.columnconfigure(0,weight=1)
    root.config(width=400,height=600)
    spider_plot.canvas.resize_event()
    root.mainloop()
