import tkMessageBox

__author__ = 'jc.forero47'

from Tkinter import *
import BraintProperties
from tkFileDialog import askopenfile
import os
import Tkinter as tk
from tkFileDialog import asksaveasfile, askopenfilename
import tkMessageBox
import ttk
import vtk
import sys,os,os.path
from vtk.tk.vtkTkRenderWindowInteractor import \
     vtkTkRenderWindowInteractor

#TODO estos import * no son recomendados sino para trabajo interactivo
from kernel.RDFDBManagerClass import *

from ScatterPlotClass import ScatterPlotClass
from VolumeRendererClass import VolumeRendererClass
from SpiderPlotClass import SpiderPlotClass
from TreeRingViewClass import TreeRingViewClass
import CSVManager
import braviz
from os.path import join as path_join
import random
import ConfigParser
import os

from Braint_V_1_6_Relations import RelationsFrame
from Braint_V_1_6_Visualization import VisualizationFrame

#class Braint_V_1_5(Frame):
#    def __init__(self, rootTk):
#        Frame.__init__(self,rootTk)
#        self.rowconfigure(0,weight=1)
#        self.columnconfigure(0,weight = 1)
#        self.grid(row=0,column=0,sticky='NSEW')
#        rootTk.rowconfigure(0,weight=1)
#        rootTk.columnconfigure(0,weight=1)

class MainFrame(Frame):
    def __init__(self, rootTk):
        Frame.__init__(self, rootTk,background='cyan')
        self.rowconfigure(0,weight=1)
        self.columnconfigure(0,weight = 1)
        self.grid(row=0,column=0,sticky='NSEW')
        rootTk.rowconfigure(0,weight=1)
        rootTk.columnconfigure(0,weight=1)

        self.rootTk = rootTk

        self.login_frame = Frame(self, width = 500, height = 400)
        self.login_frame.grid(row = 0, column = 0, sticky = N+S+E+W)
        self.login_frame.rowconfigure(0,weight=1)
        self.login_frame.columnconfigure(0,weight = 1)

        self.user_entry = tk.Entry(self.login_frame)
        self.user_label = tk.Label(self.login_frame, text = 'user')
        self.user_label.grid(row = 0, column = 0, sticky = N+E+W)
        self.user_entry.grid(row =0, column = 1, sticky = N+E+W)

        self.pwd_entry = tk.Entry(self.login_frame, show = '*')
        self.pwd_label = tk.Label(self.login_frame, text = 'password')
        self.pwd_label.grid(row = 1, column = 0, sticky = S+E+W)
        self.pwd_entry.grid(row =1, column = 1, sticky = S+E+W)

        self.login_button = tk.Button(self.login_frame, text = 'login', command = self.login_handler)
        self.login_button.grid(row = 2, column = 1, sticky = S+W+E)

        self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://guitaca.uniandes.edu.co:8080')
        self.reader=braviz.readAndFilter.kmc40AutoReader()

        self.visualization_opened = False


    def login_handler(self):
        self.check_password(self.user_entry.get(), self.pwd_entry.get())

    def check_password(self, user, password):
        my_parser = MyParser()
        my_parser.read('File' + os.sep + 'users.cfg')
        users_dict = my_parser.as_dict()['USERS']
        if user not in users_dict:
            tkMessageBox.showerror('wrong login', 'the user ' + user + ' does not exist')
        else:
            pwd = users_dict[user]
            if pwd == password:
                tkMessageBox.showinfo('', 'Login succesful')
                self.login_frame.destroy()
                self.rootTk.geometry("%dx%d+0+0" % (1500, 1000))
                self.rootTk.wm_title('User: ' + user)
                self.relations_frame = RelationsFrame(self, self.rootTk, self.myManager)
                self.create_menu()
            else:
                tkMessageBox.showerror('wrong login', 'the password is incorrect')

    def update_frame_with_visualization(self, params):
        self.rootTk.geometry("%dx%d+0+0" % (1500, 1000))
        self.rootTk.wm_title('visualization')
        
        self.visualization_frame = VisualizationFrame(self, self.rootTk, self.myManager, 1500, 1000, self.reader)
        self.visualization_opened = True
        params_map = dict()
        params_map['patient'] = '143'
        for i in range(0, len(params)):
            param_i = params[i]
            varcode = param_i[0:param_i.find('-')]
            varname = param_i[param_i.find('-') + 1:]
            params_map['var.' + str(i) + ".code"] = varcode
            params_map['var.' + str(i) + ".name"] = varname 
        
        self.visualization_frame.update_frame(params_map)
    
    def create_menu(self):
        menubar = Menu(self.rootTk)

        menuFile = Menu(menubar, tearoff = 0)
        menuFile.add_command(label = 'save session', command = self.save_session)
        menuFile.add_command(label = 'load session', command = self.load_session)
        #menuFile.add_command(label = 'create relations', command = self.create_relations)
        menubar.add_cascade(label = 'user', menu = menuFile)

        #display the menu
        self.rootTk.config(menu=menubar)
        
    def load_session(self):
        session_file_name = askopenfilename(initialdir = 'Sessions')
        
        config = ConfigParser.ConfigParser()
        config.read(session_file_name)
        vars = int(config.get('SESSION', 'vars'))
        newvars = dict()
        newvars['patient'] = config.get('SESSION', 'patient')
        for i in range(0,vars):
            varcode = config.get('SESSION', 'var.' + str(i) + ".code")
            varname = config.get('SESSION', 'var.' + str(i) + ".name")
            newvars['var.' + str(i) + ".code"] = varcode
            newvars['var.' + str(i) + ".name"] = varname
        
        if not self.visualization_opened:
            self.relations_frame.destroy_frame()
            self.rootTk.geometry("%dx%d+0+0" % (1500, 1000))
            self.rootTk.wm_title('visualization')
            self.visualization_frame = VisualizationFrame(self, self.rootTk, self.myManager, 1500, 1000, self.reader)
            self.visualization_opened = True
        
        focus_on_vtk = config.get('SESSION', 'vtkfocus')
        focus_value = False
        if focus_on_vtk == 'True':
            focus_value = True
        self.visualization_frame.set_focus_on_vtk(focus_value)
        
        self.visualization_frame.update_frame(newvars)
            
        
    def create_relations(self):
        print 'trabajo futuro'
        
    def save_session(self):
        variables = self.visualization_frame.get_variables()
        session_file = asksaveasfile(mode = 'w', defaultextension = '.txt', initialdir = 'Sessions')
        for item in variables:
            session_file.write("%s\n" % item)
        print 'saving file'
        

class MyParser(ConfigParser.ConfigParser):
    def as_dict(self):
        d = dict(self._sections)
        for k in d:
            d[k] = dict(self._defaults, **d[k])
            d[k].pop('__name__', None)
        return d


base_dir=os.path.dirname(os.path.realpath(__file__))
os.chdir(os.path.dirname(os.path.realpath(__file__)))
sys.path.append('./../kernel')
root = Tk()
width_win=1500
height_win=1000
mainFrame = MainFrame(root)
root.wm_title("Braint V 1.5")

root.mainloop()



