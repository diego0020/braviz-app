import tkMessageBox

__author__ = 'jc.forero47'

from Tkinter import *
import BraintProperties
from tkFileDialog import askopenfile
import os
import Tkinter as tk
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

from Braint_V_1_5_Relations import RelationsFrame

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
                root.geometry("%dx%d+0+0" % (1500, 1000))
                root.wm_title('User: ' + user)
                self.relations_frame = RelationsFrame(self, self.rootTk, self.myManager)
            else:
                tkMessageBox.showerror('wrong login', 'the password is incorrect')


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



