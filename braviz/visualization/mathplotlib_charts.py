"""Maptplotlib widgets which represent scalars in several charts"""
from __future__ import division
import matplotlib
matplotlib.use('TkAgg')

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# implement the default mpl key bindings
from matplotlib.backend_bases import key_press_handler
from matplotlib.text import Text as matplotlib_text
import random
from matplotlib.figure import Figure
from itertools import izip
from braviz.utilities import ignored

__author__ = 'Diego'
highlight_color='#FF7F00'
class BarPlot():
    """Displays a series of scalars in a bar plot.
    Optionally can highlight a bar, can add error bars, can add background bars to create groups
    Colors are defined by a color function
    Invokes '<<PlotSelected>>' when a bar is clicked"""
    def __init__(self,tight=True):
        """If tight is True uses the tightlayout option of matplotlib"""
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
        self.color_function=lambda x,y:(1,1,0)
        self.current_xcoord=0
        self.highlight=None
        self.style='bars'
        self.yerror=0
        self.back_bars=None
        self.back_error=None
        self.widget=None
        self.resizing = None
        self.tight=tight
        self.back_codes=None
        self.pos2name_dict={}
        self.__names2idx_dict={}

    def set_back_bars(self,back_bars,back_error=None,back_codes=tuple()):
        """Add background bars and group the front bars, see multipleVariables for an example"""
        self.back_bars=back_bars
        self.back_error=back_error
        self.back_codes=back_codes

    def change_style(self,new_style):
        """must be 'bars' or 'markers'"""
        if new_style not in ('bars','markers'):
            return
        else:
            self.style=new_style


    def get_widget(self,master,**kwargs):
        """Get the widget associated to this plot, register callbacks"""
        if self.widget is not None:
            return self.widget
        canvas = FigureCanvasTkAgg(self.figure, master=master)

        def on_key_event(event):
            print('you pressed %s' % event.key)
            key_press_handler(event, canvas)

        #canvas.mpl_connect('key_press_event', on_key_event)
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

        def update_mouse_pos(event):
            """Updates the coordinates whete the mouse was last seen"""
            self.current_xcoord=event.xdata
            if event.xdata is  None:
                if event.x < self.axis.bbox.xmin:
                    self.current_xcoord="axis_0"
                elif event.y < self.axis.bbox.ymin:
                    self.current_xcoord = None
            #print event.xdata, event.ydata
        cid = self.figure.canvas.mpl_connect('motion_notify_event', update_mouse_pos)
        def click_on_bar(event=None):
            """Handles clicks over bars"""
            curr_name=self.get_current_name()
            try:
                idx=self.__names2idx_dict[curr_name]
            except KeyError:
                self.set_higlight_index(None)
                self.paint_bar_chart()
            else:
                widget.event_generate('<<PlotSelected>>')
                self.set_higlight_index(idx)
                self.paint_bar_chart()


        cid2 = self.figure.canvas.mpl_connect('button_press_event', click_on_bar)
        widget.focus()
        self.widget=widget
        return widget

    def show(self):
        """Trys to fix bug with layout at changing window size"""
        self.resizing = None
        self.widget.update_idletasks()
        self.figure.subplots_adjust(bottom=0.0, top=1.0,hspace=0)
        self.canvas.show()

        #print "wolololo"
        #self.widget.after(1000, self.show)


    def set_y_title(self,title):
        """Title for Y axis"""
        if len(title)>25:
            title="".join(("...",title[-20:]))
        self.y_title=title
        self.axis.set_ylabel(self.y_title)


    def set_y_limits(self,button,top,right=False):
        """Limits of y axis"""
        self.y_limits=(button,top)
        self.right_y=right
        self.axis.set_ylim(self.y_limits[0], self.y_limits[1])
    def set_lines(self,lines,dashes):
        """Context lines
        lines: coordinates for lines
        dashes True or False array, indicating if the corresponding line should be dashed"""
        self.hlines=[]
        for pos,dash in izip(lines,dashes):
            ls='-'
            if dash is True:
                ls=':'
            self.hlines.append({'y':pos, 'ls':ls, 'color':'k'})
    def set_data(self,values,codes,error=None):
        """Set the data in the vars, values are the heights of the bars,
         codes should be an array of the same length and are used to identify the bars,
         errors bars can be added additionally"""
        self.bar_heights=values
        self.bar_names=codes
        for i,cd in enumerate(codes):
            self.__names2idx_dict[cd]=i
        if error is not None:
            if hasattr(error,'__iter__') and len(error)==len(values):
                self.yerror=error
            elif np.isfinite(error):
                self.yerror = error
        else:
            self.yerror=None

    def set_color_fun(self,color_function,code_and_val=False):
        """color_function receives(value,code) if code and val is True,
        otherwise it receives just value. If codes are not provided code is None"""
        if code_and_val is False:
            self.color_function=lambda x,y: color_function(x)
        else:
            self.color_function = color_function
    def paint_bar_chart(self):
        """Updates the currently displayed bar chart"""
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
        #colors = [self.color_function(x,y) for x,y in izip(self.bar_heights,self.bar_names)]
        colors = map(self.color_function, self.bar_heights,self.bar_names)
        if self.style == 'bars':
            if self.back_bars is not None:
                back_heights,back_widths=zip(*self.back_bars)
                back_names=self.back_codes
                back_colors=map(self.color_function,back_heights,back_names)
                back_positions=np.cumsum([0]+list(back_widths))
                back_positions=back_positions[:-1]
                back_positions=np.subtract(back_positions,0.8)
                back_positions=np.add(back_positions,[0,1,2])
                offsets=[0]*back_widths[0]+[1]*back_widths[1]+[2]*back_widths[2]
                back_widths=np.add(back_widths,0.6)
                bar_positions=np.add(bar_positions,offsets)
                a.set_xticks(bar_positions)
                a.set_xlim(-1, len(bar_positions)+2)
                a.bar(back_positions,back_heights,color=back_colors,width=back_widths,alpha=0.5,yerr=self.back_error,
                      error_kw={'elinewidth':3,'ecolor':'k','barsabove':True,'capsize':5,'capthick':3})
            patches=a.bar(bar_positions,self.bar_heights, color=colors, align='center',yerr=self.yerror)
            self.pos2name_dict=dict(izip(bar_positions,self.bar_names))
            if self.highlight is not None:
                try:
                    highlighted_rect = patches[self.highlight]
                    highlighted_rect.set_linewidth(4)
                    highlighted_rect.set_edgecolor(highlight_color)
                except IndexError:
                    pass
        else:
            edge_colors = ['#000000'] * len(self.bar_heights)
            sizes=[40]*len(self.bar_heights)
            linewidths=[1.0]*len(self.bar_heights)
            if self.highlight is not None:
                edge_colors[self.highlight]=highlight_color
                sizes[self.highlight]=80
                linewidths[self.highlight]=2
            patches = a.scatter(bar_positions, self.bar_heights, c=colors, marker='s', s=sizes,edgecolors=edge_colors,linewidths=linewidths)
            if self.yerror is not 0:
                a.errorbar(bar_positions, self.bar_heights, yerr=self.yerror, fmt=None)

        #a.autoscale_view()
        self.bars=patches
        self.show()
    def paint(self):
        """same as paint_bar_chart, for providing a common api"""
        self.paint_bar_chart()
    def change_bars(self,new_heights):
        """doesn't do highlight nor errors, used to quickly change bar heights"""
        if self.bars is None:
            return
        self.bars.remove()
        self.bar_heights=new_heights
        #colors = [self.color_function(x,y) for x,y in izip(self.bar_heights,self.bar_names)]
        colors = map(self.color_function,self.bar_heights,self.bar_names)
        a=self.axis
        bar_positions=self.bar_positions
        if self.style == 'bars':
            patches=a.bar(bar_positions,self.bar_heights, color=colors, align='center')
        else:
            patches=a.scatter(bar_positions,self.bar_heights,c=colors,marker='s',s=40)
        self.bars=patches
        self.show()
    def get_current_name(self):
        """Get the name of the object currently under the mouse, or "axis_0" if mouse is over x axis"""
        if self.current_xcoord is None:
            return None
        if type(self.current_xcoord) is str:
            return self.current_xcoord
        pos=int(round(self.current_xcoord))
        return self.pos2name_dict.get(pos,None)
    def set_higlight_index(self,index):
        """Set index of bar to highlight"""
        self.highlight=index


class ScatterPlot():
    """A widget for displaying two variables in a scatter plot with an optional regression line"""
    def __init__(self,tight=True):
        """If tight is True uses the tightlayout option of matplotlib
        Colors are defined by a color function
        Invokes <<PlotSelected>>  if a dot is selected
        Invokes <<ScatterClick>> if a mouse is clicked over the scatter plot
        """
        f = Figure(tight_layout=tight, facecolor='w', frameon=False, edgecolor='r')
        a = f.gca(axisbg='w')
        self.figure=f
        self.axis=a
        self.widget=None
        self.x_values=[]
        self.y_values=[]
        self.__data_names=[]
        self.x_limits=(0,1)
        self.y_limits=(0,1)
        self.reg_line= None
        self.x_label=''
        self.y_label=''
        self.tight=tight
        self.resizing=None
        self.__color_fun=lambda x,y:(0,1,1)
        self.__groups_dict = None
        self.__paths=None
        self.current_id=None
        self.__highlited = None
        self.__name2idx_dict={}


    def get_widget(self,master,**kwargs):
        """Get the widget associated to this plot, register callbacks"""
        if self.widget is not None:
            return self.widget
        canvas = FigureCanvasTkAgg(self.figure, master=master)
        self.canvas=canvas
        widget = self.canvas.get_tk_widget()
        widget.configure(bd=4, bg='white', highlightcolor='red', highlightthickness=0, **kwargs)
        def update_mouse_pos(event):
            """Updates the coordinates whete the mouse was last seen"""
            if self.axis.contains(event)[0]:
                self.current_id=None
                #Pick will change it if over a point
                self.__paths.pick(event)
            else:
                if event.x < self.axis.bbox.xmin:
                    self.current_id="axis_0"
                elif event.y < self.axis.bbox.ymin:
                    self.current_id = "axis_1"
        cid = self.figure.canvas.mpl_connect('motion_notify_event', update_mouse_pos)
        def generate_tk_event(event=None):
            widget.event_generate('<<ScatterClick>>')
        cid2 = self.figure.canvas.mpl_connect('button_press_event', generate_tk_event)
        self.widget = widget
        def click_on_scatter(event=None):
            """Handles click on scatter"""
            curr_name=self.get_current_name()
            try:
                idx=self.__name2idx_dict[curr_name]
            except KeyError:
                self.set_higlight_index(None)
                self.draw_scatter()
            else:
                widget.event_generate('<<PlotSelected>>')
                self.set_higlight_index(idx)
                self.draw_scatter()

        cid2 = self.figure.canvas.mpl_connect('button_press_event', click_on_scatter)
        if self.tight is True:
            self.resizing = None
            def resize_event_handler(event=None):
                """Tries to adapt to resize events"""
                #print "rererererere"
                #self.show()
                if self.resizing is not None:
                    widget.after_cancel(self.resizing)
                self.resizing = widget.after(1000, self.show)

            bind_id = widget.bind('<Configure>', resize_event_handler, '+')
        widget.focus()
        return widget
    def show(self):
        """Show widget, attempt to fix bugs when resizing"""
        self.resizing = None
        self.widget.update_idletasks()
        self.figure.subplots_adjust(bottom=0.0, top=1.0,hspace=0)
        self.canvas.show()
    def set_data(self,x_values,y_values,names=None):
        """Sets the data for the scatter plot, x_values and y_values should be arrays of the same size,
        names if provided is used to identify the points, it should have the same size as x_values and y_values"""
        self.y_values=y_values
        self.x_values=x_values
        if names is None:
            self.__data_names = range(len(x_values))
        else:
            self.__data_names=names
        for i,name in enumerate(self.__data_names):
            self.__name2idx_dict[name]=i


    def draw_scatter(self):
        """Updates the scatter representation"""
        a=self.axis
        a.cla()
        a.set_ylim(self.y_limits[0],self.y_limits[1])
        a.set_xlim(self.x_limits[0],self.x_limits[1])
        a.set_xlabel(self.x_label)
        a.set_ylabel(self.y_label)
        colors=map(self.__color_fun,izip(self.x_values,self.y_values),
                                         self.__data_names)
        sizes=[20]*len(self.x_values)
        linewidths=[0]*len(self.x_values)
        if self.__highlited is not None:
            with ignored(ValueError):
                idx=self.__highlited
                sizes[idx] = 40
                linewidths[idx]=2
        self.__paths =a.scatter(self.x_values,self.y_values,color=colors,picker=1
            ,s=sizes,linewidths=linewidths,edgecolor=highlight_color)
        reg_line,r=calculate_regression_line(self.x_values,self.y_values)
        a.plot(self.x_limits,map(reg_line,self.x_limits),c='k',label="all (r=%.2f)"%r)
        if self.__groups_dict is not None:
            groups=set(self.__groups_dict.itervalues())
            x_data=np.array(self.x_values)
            y_data=np.array(self.y_values)
            for g in groups:
                g_idxs=filter(lambda i:self.__groups_dict[self.__data_names[i]]==g,xrange(len(self.__data_names)))
                reg_line,r=calculate_regression_line(x_data[g_idxs],y_data[g_idxs])
                a.plot(self.x_limits, map(reg_line, self.x_limits), c=self.__color_fun(0,g),label="%s (r=%.2f)"%(g,r))
        leg=a.legend(fontsize='small',fancybox=True)
        leg.get_frame().set_alpha(0.7)
        #a.autoscale_view()
        def on_pick(event):
            self.current_id=event.ind
        self.canvas.mpl_connect('pick_event',on_pick)
        self.show()
    def paint(self):
        """same as draw_scatter, for providing a common api"""
        self.draw_scatter()
    def set_limits(self,x_lim,y_lim):
        """Set limits for x and y axes"""
        self.x_limits=x_lim
        self.y_limits=y_lim
    def set_labels(self,x_label='',y_label=''):
        """Set names for the plot labels"""
        if len(y_label)>20:
            y_label="".join(("...",y_label[-20:]))
        if len(x_label)>50:
            x_label="".join(("...",x_label[-50:]))
        self.x_label=x_label
        self.y_label=y_label
    def set_color_function(self,color_fun):
        """function must take val,code pairs"""
        self.__color_fun=color_fun
    def set_groups(self,group_dict):
        """Extra regression lines will be added for the groups, a legend will be shown with r-values"""
        self.__groups_dict=group_dict
    def get_current_name(self,event=None):
        """Get the name of the dot current under the mouse, if mouse is over an axis retunr axis_0 or axis_1"""
        if self.current_id is None:
            return None
        if type(self.current_id) is str:
            return self.current_id
        else:
            return self.__data_names[self.current_id[0]]

    def set_higlight_index(self,highlighted_id=None):
        """Sets the dot to highlight"""
        self.__highlited=highlighted_id
def calculate_regression_line(x,y):
    """uses scipy to calculate a regression line between arrays x and y"""
    from scipy.stats import linregress
    slope, intercept, r_value, p_value, std_err = linregress(x, y)
    def reg_line(x):
        return intercept+slope*x
    return reg_line,r_value

class SpiderPlot():
    """Shows several variables in a spider plot, colors are defined by a color function"""
    def __init__(self,tight=True):
        """If tight is True uses the tightlayout option of matplotlib"""
        f = Figure(tight_layout=tight, facecolor='w', frameon=False, edgecolor='r')
        self.figure=f
        self.widget=None
        self.N=5
        self.data_dict={}
        self.r_max=1
        self.axis_labels=None
        self.color_fun=lambda x,y:'g'
        self.canvas=None
        self.__groups_dict={}
        self.__groups=[None]
        self.__current_name=None
        self.__axis_labels=[]
        self.__highlight_key=None



    def get_widget(self,master,**kwargs):
        """Get the widget associated to this plot, register callbacks,
        Invokes <<PlotSelected>> when a web is selected"""
        if self.widget is not None:
            return self.widget
        canvas = FigureCanvasTkAgg(self.figure, master=master)
        self.canvas=canvas
        widget = self.canvas.get_tk_widget()
        widget.configure(bd=4, bg='white', highlightcolor='red', highlightthickness=0, **kwargs)

        def click_on_spider(event=None):
            """Handles clicks on the chart"""
            curr_name=self.get_current_name()
            if curr_name in self.data_dict:
                self.set_highlighted_key(curr_name)
                self.draw_spider()
                widget.event_generate('<<PlotSelected>>')
            else:
                self.set_highlighted_key(None)
                self.draw_spider()

        cid2 = self.figure.canvas.mpl_connect('button_press_event', click_on_spider)
        self.widget = widget
        widget.focus()
        return widget
    def show(self):
        """Show figure"""
        self.canvas.show()
    def set_data(self,data_dict,axis_labels=None):
        """Sets data for the plot, it should be a dictionary containing ids as keys, and iterables as values,
        All iterables should be of the same length. Axis labels may also be set here"""
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
        """Sets maximum radius of the web"""
        self.r_max=r_max
    def set_groups(self,groups_dict):
        """Divides the data into different groups,
        groups_dict should contain the same keys as the data_dict from set_data, values define groups"""
        self.__groups=set(groups_dict.itervalues())
        self.__groups_dict=groups_dict

    def set_color_fun(self,color_fun):
        """colof function must take two arguments, key and values array"""
        self.color_fun=color_fun

    def draw_spider(self):
        """Updates the graph with all the setted parameters"""
        from braviz.visualization.radar_chart import radar_factory
        theta = radar_factory(self.N, frame='polygon')

        group_list=sorted(list(self.__groups))
        #print group_list
        for i,g in enumerate(group_list):
            a=self.figure.add_subplot(1,len(self.__groups), i+1,
                                      axisbg='w',projection='radar',label=g)
            filtered_keys = []
            pickers_dict = {}
            for k,val in self.data_dict.iteritems():
                if self.__groups_dict.get(k)==g:
                    filtered_keys.append(k)
                    col=self.color_fun(val,k)
                    if k==self.__highlight_key:
                        a.plot(theta,val,color=highlight_color,label=k,linewidth=2,marker='o',
                               mew=0,ms=5,zorder=10,mec=col)
                    else:
                        a.plot(theta,val,color=col,label=k)
                    patches=a.fill(theta,val,color=col,alpha=0.15)
                    for p in patches:
                        max_r_func=self.get_r_functions(p.xy)
                        pickers_dict[k]=max_r_func
            a.set_rmax(self.r_max)
            a.set_rgrids(np.linspace(0,self.r_max,5)[1:],visible=False)
            a.set_rmin(0)
            if self.axis_labels is not None:
                a.set_varlabels(self.axis_labels,picker=True)
            custom_pick=self.get_custom_picker_function(filtered_keys,pickers_dict)
            a.set_picker(custom_pick)
        #end axis
        def on_pick(event):
            """handles picks on widget"""
            #print "auch, %s (%f)"%(event.url,event.r_max)
            if isinstance(event.artist,matplotlib_text):
                self.__current_name = "axis_%s"%event.artist.get_text()
            else:
                self.__current_name=event.url
        self.canvas.mpl_connect('pick_event', on_pick)
        def update_mouse_pos(event):
            """registers last known mouse position"""
            self.__current_name = None
            if event.inaxes is None:
                self.figure.pick(event)
                #print "axes=%s"%self.__current_name
            else:
                event.inaxes.pick(event)
            #print self.__current_name
        cid = self.figure.canvas.mpl_connect('motion_notify_event', update_mouse_pos)
        self.show()
    def paint(self):
        """Analogous to draw_spider, to provide common api"""
        self.draw_spider()
    def get_current_name(self):
        """Gets name currently under the mouse, or axis_n if over an axis"""
        return self.__current_name
    def set_highlighted_key(self,high_key=None):
        """sets the highlighted web"""
        self.__highlight_key=high_key
    @staticmethod
    def get_r_functions(patches):
        """Creates functions that help decide if a click is inside a web"""
        def r_function(theta):
            "r(theta) for all theta in a web"
            #patches are uniformly spaced:
            #Find to which patch the angle belongs
#            print theta
            theta_moved = (theta - np.pi / 2)
            if theta_moved < 0:
                theta_moved += 2 * np.pi
            try:
                index = int(theta_moved // (2 * np.pi / (len(patches) - 1)))
            except ValueError:
                #print theta
                return 0
            if index==len(patches):
                index-=1
            #print "%f in [%f , %f) "%(theta,patches[index][0],patches[index+1][0])
            t1, r1 = patches[index]
            t2, r2 = patches[index + 1]
            x1 = r1 * np.cos(t1)
            x2 = r2 * np.cos(t2)
            y1 = r1 * np.sin(t1)
            y2 = r2 * np.sin(t2)
            if x2==x1:
                #vertical line
                return np.min(np.abs((y1,y2)))
            m = (y2 - y1) / (x2 - x1)
            q = y1 - x1 * m
            g = np.arctan(m)
            r3 = (q / np.sqrt(1 + m * m)) / np.sin(theta - g)
            return np.abs(r3)
        return r_function
    @staticmethod
    def get_custom_picker_function(filtered_keys2,pickers_dict2):
        """picks the outer web which stills traps the mouse"""
        filtered_keys=filtered_keys2[:]
        pickers_dict=dict(pickers_dict2.iteritems())
        def custom_pick(artist, event=None):
            if event.ydata is None:
                return False, {}
            radius = event.ydata
            angle = event.xdata
            #print radius
            min_k = None
            min_r = float('+inf')
            for k in filtered_keys:
                r_max = pickers_dict[k](angle)
                if radius < r_max < min_r:
                    min_r, min_k = r_max, k
            if min_k is not None:
                return True, {'url': min_k, 'r_max': min_r}
            else:
                return False, {}
        return custom_pick


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

    def color_fun(value,key):
        from colorbrewer import BrBG
        color_array=BrBG[10]
        return map(lambda x:x/255.0, color_array[key])
    spider_plot.set_color_fun(color_fun)
    def recalc():
        test_data=[random.randrange(1,10) for i in xrange(10)]
        highlight=random.randrange(0,10)
        bar_plot.set_data(test_data,range(10),2)
        bar_plot.set_higlight_index(highlight)
        bar_plot.set_y_limits(0,10)
        bar_plot.paint_bar_chart()

        test_data_x=[random.random() for i in xrange(10)]
        test_data_y=[random.random()*2 for i in xrange(10)]
        scatter_plot.set_limits((0,1),(0,2))
        scatter_plot.set_data(test_data_x,test_data_y)
        scatter_plot.set_higlight_index(highlight)

        scatter_plot.draw_scatter()
        N=random.randrange(3,10)

        spider_test_data={}
        for i in xrange(10):
            spider_test_data[i]=[random.random() for j in xrange(N)]
        spider_plot.set_data(spider_test_data,range(N))
        spider_plot.set_highlighted_key(highlight)
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
