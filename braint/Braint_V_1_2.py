#TODO: Este se necesita? Es mejor usar todo lo de Tkinter con tk (como esta mas abajo), para no llenar el espacio
#con nombres inutiles
from Tkinter import *
from tkFileDialog import askopenfile
import Tkinter as tk
import ttk

import vtk
from vtk.tk.vtkTkRenderWindowInteractor import \
     vtkTkRenderWindowInteractor

import BraintProperties


#TODO estos import * no son recomendados sino para trabajo interactivo
from kernel.RDFDBManagerClass import *

from ScatterPlotClass import ScatterPlotClass
from VolumeRendererClass import VolumeRendererClass
from SpiderPlotClass import SpiderPlotClass
import CSVManager
import braviz
from os.path import join as path_join
import os
os.chdir(os.path.dirname(__file__))
class MainFrame(Frame):
    def __init__(self, rootTk, width, height):
        Frame.__init__(self, rootTk,background='cyan')
        self.rowconfigure(0,weight=1)
        self.columnconfigure(0,weight = 1)
        self.grid(row=0,column=0,sticky='NSEW')
        rootTk.rowconfigure(0,weight=1)
        rootTk.columnconfigure(0,weight=1)
        #Frame.__init__(self, rootTk)
        #self.grid()
        self.braintProperties = BraintProperties.BraintProperties()

        self.main_frame_root = rootTk
        menubar = Menu(self.main_frame_root)
        
        menuFile = Menu(menubar, tearoff = 0)
        menuFile.add_command(label = self.braintProperties.configLang.get('braint_V_1_0', 'menuFileLoadRDF'), command = self.load_rdf)
        menuFile.add_command(label = self.braintProperties.configLang.get('braint_V_1_0', 'menuFileConnect'), command = self.connect_to_repository)
        menuFile.add_command(label = self.braintProperties.configLang.get('braint_V_1_0', 'menuFileClose'), command = self.main_frame_root.quit)
        menubar.add_cascade(label = self.braintProperties.configLang.get('braint_V_1_0', 'menuFile'), menu = menuFile)
        
        #display the menu
        self.main_frame_root.config(menu=menubar)
        
        #create braviz reader
        self.reader=braviz.readAndFilter.BravizAutoReader()
        self.width_win=width
        self.height_win=height
        
        
        
        #TODO: Esto lo deberias hacer al final cuando sepas a ciencia cierta que filas y columnas tienes. Solamente algunas
        # especificas deberian tener peso de 1, las que quierse que crezcas
        #=======================================================================
        # for r in range(5):
        #     self.main_frame_root.rowconfigure(r, weight=1)    
        # for c in range(6):
        #     self.main_frame_root.columnconfigure(c, weight=1)
        #=======================================================================
        
        #Desde aqui empiezo a agregar todas las cosas a mi frame grandote    
        #TODO Este layout se ve como desorganizado.... Me gusta lo de foco contexto
        # No es obligacion tener un solo frame grandote con una cuadricula gigante
        # en realidad solo van a existir las filas que uses, entonces en este caso las filas 1,2,3 no existen;
        # no hace falta que les pongas rowspan de 4... si lo que quieres es controlar el tamano de las cosas, mejor usa
        # height en los diferentes widgets

        self.focusFrame = Frame(self, background = 'yellow', width=self.width_win/2, height=self.height_win)
        #self.focusFrame = Frame(self.main_frame_root, background = 'red')
        #self.focusFrame.grid(row=0, column=0, rowspan = 4, columnspan = 4, sticky = W+E+N+S)
        self.focusFrame.columnconfigure(0,weight=1) #Esta hace que el ancho del foco sea el unico que cambie cuando cambia el tamanio de la ventana
        self.focusFrame.grid(row=0, column=0, columnspan = 4, sticky = W+E+N+S)
        
        self.contextFrame = Frame(self, background = 'red', width=self.width_win/4, height=self.height_win)
        #self.contextFrame = Frame(self.main_frame_root, background = 'yellow')
        #self.contextFrame.grid(row=0, column=4, rowspan = 4, columnspan = 1, sticky = W+E+N+S)
        self.contextFrame.columnconfigure(0,weight=1)
        self.contextFrame.grid(row=0, column=5, sticky = W+E+N+S)
        
        
        
        self.patientsFrame = Frame(self, background = 'black', width=(self.width_win/4), height=self.height_win)
        #self.patientsFrame = Frame(self.main_frame_root, background = 'blue')
        #self.patientsFrame.grid(row=0, column=5, rowspan = 4, columnspan = 1, sticky = W+E+N+S)
        self.patientsFrame.columnconfigure(0,weight=1)
        self.patientsFrame.grid(row=0, column=6, sticky = W+E+N+S)
        
        
        #=======================================================================
        # self.TreeFrame = Frame(self.patientsFrame, background = 'red', width=self.width_win/3, height=((self.height_win/2)+200))  
        # self.TreeFrame.rowconfigure(0,weight=1)
        # self.TreeFrame.columnconfigure(0,weight=1)      
        # self.TreeFrame.grid(sticky=W+E+N)
        # 
        # self.PatientsList = Frame(self.patientsFrame, background = 'Yellow', width=self.width_win/3, height=((self.height_win/2)-200)) 
        # self.PatientsList.rowconfigure(0,weight=1)
        # self.PatientsList.columnconfigure(0,weight=1)      
        # self.PatientsList.grid(sticky=W+E+S) 
        # 
        #=======================================================================
        

        
        
        #Creamos las variables de estado   
        self.current_subject = '143'
        self.current_subject_index = 1     
        self.current_volume = 'Left-Putamen'
        self.current_x_axis_code_name = 'RID21015'
        self.current_x_axis_name = 'Volume of Left Putamen'
        self.current_x_axis = []
        self.current_y_axis_code_name = 'WMIIQ'
        self.current_y_axis_name = 'Score Working Memory'
        self.current_y_axis = []
        self.current_subject_x_score = [0]
        self.current_subject_y_score = [0]
        
 
        #agregamos los frames       
        self.add_tree_hierarchy_to_frame(self.patientsFrame)
        self.show_patients_list(self.patientsFrame)
        self.create_button_switch(self.focusFrame)
        self.add_vtk_plot_to_frame(self.focusFrame)
        self.focusFrame.columnconfigure(0,weight=1)
        self.create_viewer_2(self.contextFrame, 'model',self.current_subject,self.current_volume, 'mri')
        self.create_button_change_focus(self.contextFrame)
        #para cerrar bien la ventana
        self.main_frame_root.protocol("WM_DELETE_WINDOW", self.clean_exit)
        
        #creamos el primer scatter plot
        self.update_tables(self.current_x_axis_code_name, self.current_x_axis_name, self.current_y_axis_code_name, self.current_y_axis_name)
        self.update_scatterplot()
        self.create_spider_plot(self.contextFrame)   
        
    def create_button_switch(self, parent_frame):  
        "Creates the button "
        button_switch=tk.Button(parent_frame,text='Switch',command=self.button_switch_handler,pady=1)
        #button_switch.pack(side='bottom',fill='x',expand=1,pady=1)   
        #button_switch.grid(row=3, rowspan=1, column=0, columnspan = 4, sticky = W+E+N+S)
        button_switch.grid(row=1, column=0, sticky = W+E+S)
        
    def create_button_change_focus(self, parent_frame):  
        "Creates the button "
        button_switch=tk.Button(parent_frame,text='switch focus/context',command=self.button_switch_handler,pady=1)
        #button_switch.pack(side='bottom',fill='x',expand=1,pady=1)   
        #button_switch.grid(row=3, rowspan=1, column=0, columnspan = 4, sticky = W+E+N+S)
        button_switch.grid(row=2, column=0, sticky = W+E)
        
    def button_switch_handler(self):
        temp_list = list(self.current_x_axis)
        temp_name = self.current_x_axis_name
        temp_code = self.current_x_axis_code_name
        temp_score = list(self.current_subject_x_score)
        
        self.current_x_axis = list(self.current_y_axis)
        self.current_x_axis_name = self.current_y_axis_name
        self.current_x_axis_code_name = self.current_y_axis_code_name
        self.current_subject_x_score = self.current_subject_y_score
        
        self.current_y_axis = list(temp_list)
        self.current_y_axis_name = temp_name
        self.current_y_axis_code_name = temp_code
        self.current_subject_y_score = temp_score
        
        self.update_scatterplot()
        
    
    def show_patients_list(self, parent_frame):  
        """
        Muestra la lista de pacientes en un list box y lo pinto en el parent_frame que yo ingrese
        """      
        self.select_subj_frame=braviz.interaction.subjects_list(self.reader,self.setSubj,parent_frame,text='Subject',padx=5,pady=5,height=((self.height_win/2)-200))
        
        index = self.select_subj_frame.getSelectionIndex(self.current_subject)
        self.select_subj_frame.setSelection(index)
        #TODO: Ten cuidado con mezclar pack con grid... si te equivocas y dejas un papa que tenga ambos.. se enloquece
        #self.select_subj_frame.pack(side='top')
        
        self.select_subj_frame.grid(row=2, column=0, columnspan=2, sticky = S+E+W) 

    def setSubj(self,event=None):
        """
        Es el evento que se lanza cuando selecciono algo de la lista show_patients_list
        """
        subj=self.select_subj_frame.get()
        self.update_current_subject(subj)
        
    def update_current_subject(self, subj):
        """
        Funcion que realiza las acciones en mi visualizacion cuando cambio un paciente
        Esto puede ser por medio de la seleccion de un sujeto en la list box o por la seleccion en el
        scatterplot
        """
        
        #actualizo el volumen
        self.volume_renderer.update_image_plane('mri', subj, 'vtk')
        self.volume_renderer.remove_current_actors()
        self.volume_renderer.load_model('model', subj, self.current_volume)
        self.volume_renderer.refresh()
        #actualizo el sujeto y su indice dentro de la lista de pacientes
        self.current_subject = subj
        # TODO: Aca toca tener mucho cuidado... los sujetos de test-small2.csv, son diferentes a los de KAB-DB
        # No todos tienen imagenes, y algunos estan mal etiquetados... entonces no estoy seguro si sea tan facil
        # No se si tenga que ver, pero cuando uno selecciona sujetos de codigo algo, como mas de 900, aparecen
        # cruces rojas donde no hay cruces negras

        #tomar los indices de uno y los del otro
        self.current_subject_index = self.select_subj_frame.getSelectionIndex(self.current_subject)
        #actualizo el scatterplot
        self.update_current_subject_score()
        self.update_scatterplot()
        self.update_spiderplot()
             
    def add_tree_hierarchy_to_frame(self, parent_frame):      
        """
        Esta funcion pinta un arbol con la informacion que se encuentra en el repositorio RDF de las jerarquias.
        Test-Subtest-Subsubtest
        Importante revisar en RDFDBManager que este trayendo las cosas del repositorio adecuado
        """    
        self.my_tree= ttk.Treeview(parent_frame)
        
        #TODO: Y estas por que no se ven?
        self.my_tree.heading('#0', text='BraInt Hierarchy', anchor='w')
        self.my_tree.column('#0', stretch=False, width=self.width_win/4)
        ysb = ttk.Scrollbar(parent_frame, orient='vertical', command=self.my_tree.yview)
        xsb = ttk.Scrollbar(parent_frame, orient='horizontal', command=self.my_tree.xview)
        self.my_tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)     
        abspath = 'BraInt'
        parent=self.my_tree.insert('', 'end', text=abspath, open=True)
        self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://guitaca.uniandes.edu.co:8080')
        #self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://localhost:8080') ##Crear objeto del tipo RDFDBmanager
        #self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://gambita.uniandes.edu.co:8080') ##Crear objeto del tipo RDFDBmanager
        listResults=self.myManager.loadQuery('File\\rdfqueries\IdAndNames')
        self.items_add = dict()
        id_tree_vol='i'
        id_tree_fib='i'
        self.volume_list=[]
        self.fiber_list=[]
        for my_item in listResults:
            evaluation_name = my_item['Evaluation']['value']
            if evaluation_name not in self.items_add:
                tree_id_evaluation= self.my_tree.insert(parent, 'end', text=evaluation_name, tags=(evaluation_name), open=False)
                self.items_add.update({evaluation_name:tree_id_evaluation})              
            if 'Test' in my_item:
                raw_test_id = my_item['Test']['value']
                wVal,wSep,test_id = raw_test_id.partition('#')
                if test_id not in self.items_add:
                    list_id_evaluation=self.items_add[evaluation_name]
                    node_name = test_id + '-'
                    if 'TestName' in my_item:
                         test_name=my_item['TestName']['value']
                         node_name = node_name + test_name
                    tree_id_test=self.my_tree.insert(list_id_evaluation, 'end', text=node_name, tags=(test_id), open=False)
                    self.items_add.update({test_id:tree_id_test})
                
            if 'SubTest' in my_item:
                raw_subtest_id = my_item['SubTest']['value']
                wVal,wSep,subtest_id = raw_subtest_id.partition('#')
                if subtest_id not in self.items_add:
                    list_id_test=self.items_add[test_id]
                    node_name = subtest_id + '-'
                    if 'SubTestName' in my_item:
                        subtest_name=my_item['SubTestName']['value']
                        node_name = node_name + subtest_name
                    tree_id_subtest=self.my_tree.insert(list_id_test, 'end', text=node_name, tags=(subtest_id), open=False)
                    self.items_add.update({subtest_id:tree_id_subtest})
                    if subtest_name=='Volume':
                        id_tree_vol=tree_id_subtest
                    if subtest_name=='Total number':
                        id_tree_fib=tree_id_subtest    
            if 'SubSubTest' in my_item:
                raw_subsubtest_id = my_item['SubSubTest']['value']
                wVal,wSep,subsubtest_id = raw_subsubtest_id.partition('#')
                if subsubtest_id not in self.items_add:   
                    list_id_subtest=self.items_add[subtest_id]
                    node_name = subsubtest_id + '-'
                    if 'SubSubTestName' in my_item:
                        subsubtest_name=my_item['SubSubTestName']['value']
                        node_name = node_name + subsubtest_name
                    tree_id_subsubtest=self.my_tree.insert(list_id_subtest, 'end', text=node_name, tags=(subsubtest_id), open=False)
                    #self.my_tree.tag_configure(subsubtest_id, background='black')#Si quiero cambiar el color de  fondo del tree
                    self.items_add.update({subsubtest_id:tree_id_subsubtest})
                    if list_id_subtest==id_tree_vol:
                        self.volume_list.append(subsubtest_id)
                    if list_id_subtest==id_tree_fib:
                        self.fiber_list.append(subsubtest_id) 
                    #print self.fiber_list, 'fibraaaaaaaaas'       
        #self.my_tree.pack(side=TOP, fill=BOTH, expand=1, anchor=NW)
        self.my_tree.grid(row=0, column=0, sticky = N+S+E+W )
        parent_frame.rowconfigure(0, weight=1)# para quse se extienda hasta abajo
        parent_frame.columnconfigure(0, weight=1)
        xsb.grid(row=1, column=0, columnspan=2, sticky = E+W)
        ysb.grid(row=0, column=1, sticky = N+S)        
        self.my_tree.bind('<Double-1>',self.treeview_selection_handler)          
        return self.volume_list        

    def treeview_selection_handler(self, event):
        """
        Esta funcion se activa cuando en la funcion anterior alguien hace doble clic sobre el arbol.
        Tambien realiza la consulta de las demas varialbes que se relacionan con la seleccion y las pinta de amarillo
        Tambien pinta un volumen en caso de haber sido seleccionado en el arbol
        Importante revisar en RDFDBManager que este trayendo las cosas del repositorio adecuado
        """
        item = self.my_tree.selection()[0]
        chosen = self.my_tree.item(item, "text")
        regexIndex=chosen.find('-')
        name = chosen[regexIndex + 1:]
        chosen=chosen[0:regexIndex]

        self.update_tables(chosen, name, self.current_y_axis_code_name, self.current_y_axis_name)
        self.update_scatterplot()
        
        children = self.myManager.loadQueryParentChildren('File\\rdfqueries\\ChildrenSearch', chosen, 'isRelatedWith')
        for my_component in self.items_add:            
            if my_component in children:

                self.my_tree.tag_configure(my_component, background='yellow')
            elif my_component in chosen:
                self.my_tree.tag_configure(chosen, background='red')
            else:
                #TODO Si quieres volverlo a dejar como es originalmente, le puedes dar background=''
                self.my_tree.tag_configure(my_component, background='white')


                
    def load_rdf(self):
        #TODO: estos no hacen nada?
        rdfFileName = askopenfile()
        print rdfFileName
        
    def connect_to_repository(self):
        # TODO: este tampoco?
        print "connect"
        
    def add_vtk_plot_to_frame(self, parent_frame):
        self.create_plot_test()
        view = self.scatterPlot.get_vtk_view()

        renWin=vtk.vtkRenderWindow()
        #render_widget = vtkTkRenderWindowInteractor(parent_frame,rw=renWin,width=500, height=900) 
        render_widget = vtkTkRenderWindowInteractor(parent_frame,rw=renWin)  
        iact=render_widget.GetRenderWindow().GetInteractor()                            
        view.SetRenderWindow(render_widget.GetRenderWindow())
        view.SetInteractor(iact)
        #render_widget.grid(row=0, rowspan=2, column=0, columnspan = 4, sticky = W+E+N+S)
        parent_frame.rowconfigure(0, weight=1)# para quse se extienda hasta abajo

        render_widget.grid(row=0, column=0, sticky = W+E+N+S)
        #render_widget.pack(side=LEFT, fill=BOTH, expand=1, anchor=NW)
        view.GetRenderWindow().SetMultiSamples(0)
        iact.Initialize()
        view.GetRenderWindow().Render()
        iact.Start()
        
    def update_current_subject_score(self):
        if self.current_x_axis_code_name in self.volume_list:
            self.volume_renderer.remove_current_actors()
            self.volume_renderer.load_model('model', self.current_subject, self.current_volume)
            self.volume_renderer.refresh()

            # TODO: Esta linea esta re compleja, y creo que usar map para una lista de un solo elemento es overkill...
            # yo lo dejaria conmo
            # self.current_subject_x_score = self.scatterPlot.get_struct_volume(self.reader, self.current_volume, self.current_subject)
            self.current_subject_x_score = map(lambda code: self.scatterPlot.get_struct_volume(self.reader, self.current_volume, code) ,[self.current_subject])

        else: 
            self.current_x_axis = self.scatterPlot.get_columnFromCSV(self.file_name, self.current_x_axis_code_name, True)
            self.current_subject_x_score = [self.current_x_axis[self.current_subject_index]]
            
        if self.current_y_axis_code_name in self.volume_list:
            self.volume_renderer.remove_current_actors()
            self.volume_renderer.load_model('model', self.current_subject, self.current_volume)
            self.volume_renderer.refresh()
            #TODO: Igual que arriba, aca no vale la pena usar map y lambda
            self.current_subject_y_score = map(lambda code: self.scatterPlot.get_struct_volume(self.reader, self.current_volume, code) ,[self.current_subject])

        else: 
            self.current_y_axis = self.scatterPlot.get_columnFromCSV(self.file_name, self.current_y_axis_code_name, True)
            self.current_subject_y_score = [self.current_y_axis[self.current_subject_index]]
            
    def update_tables(self, x_axis_code, x_axis_name, y_axis_code, y_axis_name):
        #TODO: AGREGAR EL CASO DE DOS VOLUMENES!!!
        if x_axis_code in self.volume_list:
            self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://guitaca.uniandes.edu.co:8080')
            #self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://localhost:8080') ##Crear objeto del tipo RDFDBmanager
            #self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://gambita.uniandes.edu.co:8080') ##Crear objeto del tipo RDFDBmanager
            Result=self.myManager.load_each_free_name('File\\rdfqueries\\Each_Free_Name.txt', x_axis_code)             
            self.current_x_axis=map(lambda code: self.scatterPlot.get_struct_volume(self.reader, Result, code) ,self.codes)
            self.current_x_axis_code_name = x_axis_code
            self.current_x_axis_name = x_axis_name
            self.current_volume = Result
            self.volume_renderer.remove_current_actors()
            self.volume_renderer.load_model('model', self.current_subject, self.current_volume)
            self.volume_renderer.refresh()
            
            self.current_subject_x_score = map(lambda code: self.scatterPlot.get_struct_volume(self.reader, Result, code) ,[self.current_subject])

        else:
            #TODO: Podrias ponerle try except aca para manejar el caso en que no exista aun la columna
            self.current_x_axis = self.scatterPlot.get_columnFromCSV(self.file_name, x_axis_code, True)
            self.current_x_axis_code_name = x_axis_code
            self.current_x_axis_name = x_axis_name
            self.current_subject_x_score = [self.current_x_axis[self.current_subject_index]]
            
        if y_axis_code in self.volume_list:
            self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://guitaca.uniandes.edu.co:8080')
            #self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://localhost:8080') ##Crear objeto del tipo RDFDBmanager
            #self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://gambita.uniandes.edu.co:8080') ##Crear objeto del tipo RDFDBmanager
            Result=self.myManager.load_each_free_name('File\\rdfqueries\\Each_Free_Name.txt', y_axis_code)             
            self.current_y_axis=map(lambda code: self.scatterPlot.get_struct_volume(self.reader, Result, code) ,self.codes)
            self.current_y_axis_code_name = y_axis_code
            self.current_y_axis_name = y_axis_name
            self.current_volume = Result
            self.volume_renderer.remove_current_actors()
            self.volume_renderer.load_model('model', self.current_subject, self.current_volume)
            self.volume_renderer.refresh()
            
            self.current_subject_y_score = map(lambda code: self.scatterPlot.get_struct_volume(self.reader, Result, code) ,[self.current_subject])

        else: 
            self.current_y_axis = self.scatterPlot.get_columnFromCSV(self.file_name, y_axis_code, True)
            self.current_y_axis_code_name = y_axis_code
            self.current_y_axis_name = y_axis_name
            self.current_subject_y_score = [self.current_y_axis[self.current_subject_index]]
            
        if (x_axis_code in self.volume_list) and (y_axis_code in self.volume_list):
            self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://guitaca.uniandes.edu.co:8080')
            #self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://localhost:8080') ##Crear objeto del tipo RDFDBmanager
            #self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://gambita.uniandes.edu.co:8080') ##Crear objeto del tipo RDFDBmanager
            Result=self.myManager.load_each_free_name('File\\rdfqueries\\Each_Free_Name.txt', y_axis_code)             
            self.current_y_axis=map(lambda code: self.scatterPlot.get_struct_volume(self.reader, Result, code) ,self.codes)
            self.current_y_axis_code_name = y_axis_code
            self.current_y_axis_name = y_axis_name
            self.current_volume = Result
            self.volume_renderer.remove_current_actors()
            self.volume_renderer.load_model('model', self.current_subject, self.current_volume)
            self.volume_renderer.refresh()
            
            ##Aqui empieza mi nuevo sufrimiento!
            
            

    def create_plot_test(self):
        
        data_root=self.reader.getDataRoot()
        self.file_name=path_join(data_root,'test_small2.csv')
        self.scatterPlot = ScatterPlotClass(500,500)
        self.codes = self.scatterPlot.get_columnFromCSV(self.file_name, 'CODE', False)
        self.scatterPlot.set_callback(self.scatterplot_callback)

        
    def create_viewer_2(self, parent_frame, model, patient, structure, image_type,):        
        self.volume_renderer = VolumeRendererClass()
        self.volume_renderer.load_model(model,patient,structure)
        self.volume_renderer.load_image_plane(image_type, patient,'vtk')
        #self.volume_renderer.load_fibers('325','fa','CC_Central')
        ren_win = self.volume_renderer.get_render_window()
        #self.render_widget = vtkTkRenderWindowInteractor(parent_frame, rw=ren_win, width=700, height=600)
        self.render_widget = vtkTkRenderWindowInteractor(parent_frame, rw=ren_win)
        self.render_widget.grid(row=0, column=0, sticky = W+E+N+S)
        
        self.volume_renderer.render(self.render_widget)
    
    def create_spider_plot(self, parent_frame):        
        
        axes_names = ['vision', 'audicion', 'nutricion', 'Talla', 'Peso']
        
        csv_values = []
        axes_ranges = dict()
        for axis_name in axes_names:
            csv_values.append(CSVManager.get_column_from_csv(self.file_name, axis_name, False))
            axes_ranges[axis_name] = CSVManager.get_column_range_from_csv(self.file_name, axis_name, False)

        
        #axes_ranges = {'eje 1':[0,10], 'eje 2':[0,10], 'eje 3':[0,10], 'eje 4':[0,10], 'eje 5':[0,10]}
        num_tuples = 3
        title = 'Patient ' + self.current_subject
        self.spider_plot = SpiderPlotClass(title, num_tuples,axes_names, axes_ranges, 500, 500)
        
        data = []
        #=======================================================================
        # for i_data in range(0,5):
        #     data_row = []
        #     for j_data in range(0,num_tuples):
        #         data_row.append(random.randint(1,10))
        #     data.append(data_row)
        #=======================================================================
        
        index = 0
        for axis_name in axes_names:
            patient_value = csv_values[index][self.current_subject_index]
            if ',' in patient_value:
                patient_value = patient_value.replace(',','.')
            data.append([axes_ranges[axis_name][0], float(patient_value), axes_ranges[axis_name][1]]);
            index = index + 1
        
        self.spider_plot.update_data(data);
        
        #=======================================================================
        # ren1 = vtk.vtkRenderer()
        # renWin = self.spider_plot.get_render_window()
        # renWin.AddRenderer(ren1)
        # iren=vtkTkRenderWindowInteractor(parent_frame,rw=renWin)
        # iact=iren.GetRenderWindow().GetInteractor()
        # iren.SetRenderWindow(renWin)
        # ren1.AddActor(self.spider_plot.get_actor())
        # ren1.SetBackground(0, 0, 0)
        # renWin.SetSize(500, 500)
        # parent_frame.rowconfigure(0, weight=1)# para quse se extienda hasta abajo
        # iren.grid(row=0, column=0, sticky = S)
        # iact.Initialize()
        # renWin.Render()
        # iact.Start()
        #=======================================================================
        
        self.render_widget_2=vtkTkRenderWindowInteractor(parent_frame,rw=self.spider_plot.get_render_window())

        parent_frame.rowconfigure(0, weight=1)# para quse se extienda hasta abajo
        self.render_widget_2.grid(row=3, column=0, sticky = W+E+S)
        self.spider_plot.init_render(self.render_widget_2)
        

    def update_spiderplot(self):
        axes_names = ['vision', 'audicion', 'nutricion', 'Talla', 'Peso']
        csv_values = []
        axes_ranges = dict()
        for axis_name in axes_names:
            csv_values.append(CSVManager.get_column_from_csv(self.file_name, axis_name, False))
            axes_ranges[axis_name] = CSVManager.get_column_range_from_csv(self.file_name, axis_name, False)

        
        #axes_ranges = {'eje 1':[0,10], 'eje 2':[0,10], 'eje 3':[0,10], 'eje 4':[0,10], 'eje 5':[0,10]}
        num_tuples = 3
        title = 'Patient ' + self.current_subject

        #DIEGO: Solo comente esta linea, estabas creand un spiderplot nuevo (con ventana y todo) cada que cambiabas de paciente,
        #la idea es solamente cambiarle los datos al que ya tiene
        #self.spider_plot = SpiderPlotClass(title, num_tuples,axes_names, axes_ranges, 500, 500)
        
        data = []
        
        index = 0
        for axis_name in axes_names:
            patient_value = csv_values[index][self.current_subject_index]
            if ',' in patient_value:
                patient_value = patient_value.replace(',','.')
            data.append([axes_ranges[axis_name][0], float(patient_value), axes_ranges[axis_name][1]]);
            index = index + 1
        
        self.spider_plot.update_data(data);
        self.spider_plot.update_title(title)
        self.spider_plot.refresh()

    def clean_exit(self):     
        print "adios"
        self.volume_renderer.clean_exit()
        self.render_widget.destroy()
        self.main_frame_root.quit()
        self.main_frame_root.destroy()

    def scatterplot_callback(self, caller, event):
        sel = caller.GetCurrentSelection()
 
        for nn in range(sel.GetNumberOfNodes()):
            sel_ids = sel.GetNode(nn).GetSelectionList()
            if sel_ids.GetNumberOfTuples() > 0:
                for ii in range(sel_ids.GetNumberOfTuples()):
                    code_index = int(sel_ids.GetTuple1(ii))
                    #TODO: Esto no funciona!!!, no hay my_new_codelist
                    #Yaaaa!
                    subj = self.codes[code_index]
                    self.update_current_subject(subj)
                    self.select_subj_frame.setSelection(code_index)
                    print 'patient',subj
            else:
                print "-- empty"

    def update_scatterplot(self):
        self.scatterPlot.add_axes_complete(self.current_x_axis, self.current_x_axis_name, self.current_y_axis, self.current_y_axis_name, self.codes, 'codes', self.current_subject_x_score, self.current_subject_y_score) 
        
root = Tk()
width_win=1500
height_win=1000
mainFrame = MainFrame(root, width_win, height_win)
root.configure(background='blue')
#width=(root.winfo_screenwidth())*0.8
#height=(root.winfo_screenheight())*0.8

root.geometry("%dx%d+0+0" % (width_win*0.8, height_win*0.7))
root.wm_title("Braint V 1.2")
root.mainloop()