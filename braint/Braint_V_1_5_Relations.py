__author__ = 'jc.forero47'

from Tkinter import *
import BraintProperties
from tkFileDialog import askopenfile
import os
import Tkinter as tk
import ttk
import vtk
import sys,os,os.path
from vtk.tk.vtkTkRenderWindowInteractor import vtkTkRenderWindowInteractor

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
import os

class RelationsFrame():
    def __init__(self, parent, rootTk, manager):

        self.base_dir=os.path.dirname(os.path.realpath(__file__))
        self.myManager = manager
        self.items_to_add = list()


        rdf_file=os.path.join(self.base_dir,'File','rdfqueries','EvaluationNames.txt')
        evaluations = self.myManager.loadQuery(rdf_file)
        self.evaluations_list = list()
        for item in evaluations:
            self.evaluations_list.append(item['name']['value'])

        self.relations_frame = Frame(parent, width = 500, height = 600)
        self.relations_frame.rowconfigure(0,weight=1)
        self.relations_frame.columnconfigure(0,weight = 1)
        self.relations_frame.grid(row = 0, column = 0, sticky = N+S+E+W)

        menubar = Menu(rootTk)

        menuFile = Menu(menubar, tearoff = 0)
        menuFile.add_command(label = 'load session', command = self.load_session)
        menuFile.add_command(label = 'create relations', command = self.create_relations)
        menubar.add_cascade(label = 'user', menu = menuFile)

        #display the menu
        rootTk.config(menu=menubar)


        #####Este es el frame   que contiene el anillo
        self.RingFrame = Frame(self.relations_frame, width=700, height=700)
        self.RingFrame.columnconfigure(0,weight=1)
        self.RingFrame.rowconfigure(0,weight=1)
        self.RingFrame.grid(row=0, column=0, sticky = W+E+N+S)

        #######Este es el frame que tiene la informacion de las relaciones y las variables que selecciona el usuario en el anillo
        self.RelInfoFrame = Frame(self.relations_frame, width=200, height=700)
        self.RelInfoFrame.columnconfigure(0,weight=1)
        self.RelInfoFrame.rowconfigure(0,weight=1)
        self.RelInfoFrame.rowconfigure(1,weight=1)
        self.RelInfoFrame.grid(row=0, column=1, sticky = W+E+N+S)

        #Este es el frame para meter la lista de relaciones dentro del frame relinfoframe
        self.list_relations_frame = Frame(self.RelInfoFrame, width=200, height=350)
        self.list_relations_frame.grid(row=0, column=0, sticky=W+E+N+S)

        #Este es el frame para meter el texto que se extrae de las relaciones como informacion de la bibliografia y el boton de agregar al panel izq las variables que quiero visualizar
        self.references_frame = Frame(self.RelInfoFrame, width=200, height=200)
        self.references_frame.grid(row=1, column=0, sticky=W+E+N+S)

        #Este es el frame que tiene el nombre de la seleccion y el boton para agregarla a las variables
        self.selection_frame = Frame(self.RelInfoFrame, background = 'red', width = 200, height = 150 )
        self.selection_frame.columnconfigure(0,weight=1)
        self.selection_frame.rowconfigure(0,weight=1)
        self.selection_frame.grid(row = 2, column = 0, sticky=W+E+S+N)

        #####Este es el frame que las variables que quiero visualizar en braint
        self.RelSelFrame = Frame(self.relations_frame, width=200, height=700)
        self.RelSelFrame.rowconfigure(0,weight=1)
        self.RelSelFrame.columnconfigure(1,weight=1)
        self.RelSelFrame.grid(row=0, column=2, sticky = W+E+N+S)

        self.list_final_selection_frame = Frame(self.RelSelFrame, width=200, height=450)
        self.list_final_selection_frame.grid(row=0, column=0, sticky=W+E+N+S)

        self.buttons_final_selection_frame = Frame(self.RelSelFrame, width=200, height=255)
        self.buttons_final_selection_frame.grid(row=1, column=0, sticky=W+E+N+S)

        #Aqui se empiezan a pintar los componentes de la ventana
        self.create_treering(self.RingFrame)
        self.create_list_relations(self.list_relations_frame)
        #self.create_button_add_relation(self.references_frame)
        self.create_button_add_relation(self.list_relations_frame)
        self.create_info_relations(self.references_frame)
        self.create_list_variable_selection(self.list_final_selection_frame)
        self.create_button_clear(self.buttons_final_selection_frame)
        self.create_button_remove(self.buttons_final_selection_frame)
        self.create_button_apply(self.buttons_final_selection_frame)
        self.create_button_add_variable(self.selection_frame)

    def create_treering(self, parent_frame):
        hierarchy_file =os.path.join(self.base_dir,'treetest.xml')
        nodes_csv = "testfilenodes.csv"
        relations_csv = "testfilerelations.csv"

        self.treering_plot = TreeRingViewClass(relations_csv, nodes_csv, hierarchy_file)
        self.treering_plot.set_handler(self.treering_handler)
        ren_win = self.treering_plot.get_render_window()
        self.render_widget_treering = vtkTkRenderWindowInteractor(parent_frame,rw=ren_win, width=700, height=700)

        self.render_widget_treering.grid(row=0, column=0, sticky = N+W+E+S)

        self.treering_plot.init_render(self.render_widget_treering)

    def treering_handler(self, caller, event):
        sel = caller.GetCurrentSelection()

        if sel.GetNumberOfNodes() > 0:
            self.info_area.delete('0.0', 'end')
            item = sel.GetNode(0).GetSelectionList().GetValue(0)
            if item not in self.evaluations_list:
                #if item not in self.items_to_add:
                    #self.items_to_add.append(item)
                    #self.list_items_to_add.insert(END, self.create_item_name(item))
                self.list_selection.delete(0, END)
                self.list_selection.insert(END, self.create_item_name(item))
                rdf_file=os.path.join(self.base_dir,'File','rdfqueries','ChildrenSearch')
                children = self.myManager.loadQueryParentChildren(rdf_file, item, 'isRelatedWith')
                #children = self.myManager.loadQueryParentChildren('File\\rdfqueries\\ChildrenSearch', item, 'isRelatedWith')
                self.list_relations.delete(0, END)
                if len(children) > 0:
                    for child in children:
                        self.list_relations.insert(END, self.create_item_name(child))

                #para el buque

                if item == 'FSIQ':

                    self.info_area.insert(INSERT,'Type: Article\n\n'
                                                 'Title: Visual perception and visual-motor integration in very preterm and/or very low birth weight children: A meta-analysis\n\n'
                                                 'Author: C.J.A. Geldof, A.G. van Wassenaer, J.F. de Kieviet, J.H. Kok, J. Oosterlaan\n\n'
                                                 'Year: 2012')
                elif item == 'UBICA':
                    self.info_area.insert(INSERT,'Type: Hypothesis\n\n'
                                                 'Author: Solecito Feliz\n\n'
                                                 'Year: 2013')
                else:
                    self.info_area.insert(INSERT,'')
            else:
                #if item not in self.items_to_add:
                #    #self.items_to_add.append(item)
                #    #self.list_items_to_add.insert(END, item)
                self.list_selection.delete(0, END)
                self.list_selection.insert(END, item)


                ## Fin de buquee

    def create_list_relations(self, parent_frame):
        self.list_relations=tk.Listbox(parent_frame, width=33, height=20, selectmode = EXTENDED)
        ysb = ttk.Scrollbar(parent_frame, orient='vertical', command=self.list_relations.yview)
        xsb = ttk.Scrollbar(parent_frame, orient='horizontal', command=self.list_relations.xview)
        self.list_relations.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        parent_frame.rowconfigure(0, weight=1)# para quse se extienda hasta abajo
        parent_frame.columnconfigure(0, weight=1)
        self.list_relations.grid(row=0, column=0,sticky = W+E+N+S)
        xsb.grid(row=1, column=0, columnspan=2, sticky = E+W)
        ysb.grid(row=0, column=1, sticky = N+S)

    def create_button_add_relation(self, parent_frame):
        button_add=tk.Button(parent_frame,text='Add Relation',pady=1, command = self.button_add_relation_handler)
        parent_frame.rowconfigure(0, weight=1)
        parent_frame.columnconfigure(0, weight=1)
        button_add.grid(row=2, column=0, columnspan = 2, sticky = N+W+E+S)

    def button_add_relation_handler(self):
        items = self.list_relations.curselection()

        for item_index in items:
            item_raw = self.list_relations.get(item_index)
            item = item_raw
            if '-' in item_raw:
                index = item_raw.index('-')
                item = item[0:index]
            if item not in self.items_to_add:
                self.items_to_add.append(item)
                self.list_items_to_add.insert(END, item_raw)

    def button_add_variable_handler(self):
        item_raw = self.list_selection.get(0)
        if item_raw != '':
            item = item_raw
            if '-' in item_raw:
                index = item_raw.index('-')
                item = item[0:index]
            if item not in self.items_to_add:
                self.items_to_add.append(item)
                self.list_items_to_add.insert(END, item_raw)
        self.list_selection.delete(0,END)

    def create_info_relations(self, parent_frame):
        self.info_area=tk.Text(parent_frame, width=33, height=30)
        self.info_area.insert('1.0', '')
        parent_frame.rowconfigure(0, weight=1)
        parent_frame.columnconfigure(0, weight=1)
        self.info_area.grid(row=0, column=0, sticky = N+W+E+S)

    def create_button_add_variable(self, parent_frame):
        #label_selection = tk.Label(parent_frame, textvariable = self.selection_value)
        #label_selection.grid(row = 0, column = 0, sticky = W+E)
        self.list_selection=tk.Listbox(parent_frame, width=33, height=1)
        xsb = ttk.Scrollbar(parent_frame, orient='horizontal', command=self.list_selection.xview)
        self.list_selection.configure( xscrollcommand=xsb.set)
        parent_frame.rowconfigure(0, weight=1)# para que se extienda hasta abajo
        parent_frame.columnconfigure(0, weight=1)
        self.list_selection.grid(row=0, column=0,sticky = W+E+N+S)
        xsb.grid(row=1, column=0, columnspan=2, sticky = E+W)


        button_add=tk.Button(parent_frame,text='Add Variable',pady=1, command = self.button_add_variable_handler)
        button_add.grid(row=2, column=0, sticky = W+E)

    def create_list_variable_selection(self, parent_frame):
        self.list_items_to_add=tk.Listbox(parent_frame, width=33, height=27, selectmode=EXTENDED)
        ysb = ttk.Scrollbar(parent_frame, orient='vertical', command=self.list_items_to_add.yview)
        xsb = ttk.Scrollbar(parent_frame, orient='horizontal', command=self.list_items_to_add.xview)
        self.list_items_to_add.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        parent_frame.rowconfigure(0, weight=1)# para que se extienda hasta abajo
        parent_frame.columnconfigure(0, weight=1)
        self.list_items_to_add.grid(row=0, column=0,sticky = W+E+N+S)
        xsb.grid(row=1, column=0, columnspan=2, sticky = E+W)
        ysb.grid(row=0, column=1, sticky = N+S)

    def create_button_clear(self, parent_frame):
        button_add=tk.Button(parent_frame,text='Clear', width=15, command = self.button_clear_handler)
        button_add.grid(row=0, column=0, sticky =W)

    def button_clear_handler(self):
        del self.items_to_add[:]
        self.list_items_to_add.delete(0,END)

    def create_button_remove(self, parent_frame):
        button_add=tk.Button(parent_frame,text='Remove', width=15, command = self.button_remove_handler)
        button_add.grid(row=0, column=1,sticky =E)

    def button_remove_handler(self):
        items = self.list_items_to_add.curselection()
        for item in reversed(items):
            del self.items_to_add[int(item)]
            self.list_items_to_add.delete(int(item))

    def create_button_apply(self, parent_frame):
        button_add=tk.Button(parent_frame,text='Apply')
        button_add.grid(row=1, column=0, columnspan=2, sticky = W+E)

    def create_item_name(self, item):
        rdf_file=os.path.join(self.base_dir,'File','rdfqueries','RdfType')
        type =  self.myManager.loadQueryRdfType(rdf_file, item)
        #type =  self.myManager.loadQueryRdfType('File\\rdfqueries\\RdfType', item)
        type_name = type[0] + '_Name'
        rdf_file=os.path.join(self.base_dir,'File','rdfqueries','ChildrenSearch')
        item_name_list = self.myManager.loadQueryParentChildren(rdf_file, item, str(type_name))
        #item_name_list = self.myManager.loadQueryParentChildren('File\\rdfqueries\\ChildrenSearch', item, str(type_name))
        item_name = item
        if len(item_name_list) > 0:
            item_name = item_name + '-' + item_name_list[0]
        return item_name

    def load_session(self):
        print 'trabajo futuro'

    def create_relations(self):
        print 'trabajo futuro'