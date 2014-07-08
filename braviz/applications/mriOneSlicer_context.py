"Illustrate how to load and display Slicer 3d Models"
import Tkinter as tk
import ttk
import threading
import thread

import vtk
from vtk.tk.vtkTkRenderWindowInteractor import \
     vtkTkRenderWindowInteractor

import braviz.readAndFilter
from braviz.visualization import add_solid_balloon,add_fibers_balloon
from braviz.interaction.tkSimpleDialog import Dialog as simpleDialog
from braviz.utilities import configure_console_logger

if __name__ == "__main__":
    configure_console_logger("mriOneSlicer_context")
    currSpace='World'
    current_models=[]
    #reader=braviz.readAndFilter.kmc40.kmc40Reader(r'C:\Users\da.angulo39\Documents\Kanguro')
    reader=braviz.readAndFilter.BravizAutoReader()
    currSubj=reader.get("ids")[0]
    img=reader.get('MRI',currSubj,format='VTK',space=currSpace)
    aparc=reader.get('aparc',currSubj,format='vtk',space=currSpace)

    picker = vtk.vtkCellPicker()
    picker.SetTolerance(0.005)

    #Visualization
    ren=vtk.vtkRenderer()
    renWin=vtk.vtkRenderWindow()
    renWin.AddRenderer(ren)
    config=braviz.interaction.get_config(__file__)
    background= config.get_background()
    ren.SetBackground(background)

    planeWidget=braviz.visualization.persistentImagePlane()
    planeWidget.SetInputData(img)

    planeWidget.addLabels(aparc)
    planeWidget.SetResliceInterpolateToNearestNeighbour()
    planeWidget.PickingManagedOn()
    planeWidget.SetPicker(picker)
    renWin.SetSize(600, 600)


    outline = vtk.vtkOutlineFilter()
    outline.SetInputData(img)

    outlineMapper = vtk.vtkPolyDataMapper()
    outlineMapper.SetInputConnection(outline.GetOutputPort())

    outlineActor = vtk.vtkActor()
    outlineActor.SetMapper(outlineMapper)
    ren.AddActor(outlineActor)

    axes_actor=vtk.vtkAnnotatedCubeActor()
    axes_actor.SetXPlusFaceText("R")
    axes_actor.SetXMinusFaceText("L")
    axes_actor.SetYPlusFaceText("A")
    axes_actor.SetYMinusFaceText("P")
    axes_actor.SetZPlusFaceText("S")
    axes_actor.SetZMinusFaceText("I")

    axes_actor.GetTextEdgesProperty().SetColor(1,1,1)
    axes_actor.GetTextEdgesProperty().SetLineWidth(2)
    axes_actor.GetCubeProperty().SetColor(0.3,0.3,0.3)

    axes=vtk.vtkOrientationMarkerWidget()
    axes.SetOrientationMarker(axes_actor)
    axes.SetViewport(0, 0, 0.1,0.1)

    balloon_widget=vtk.vtkBalloonWidget()
    balloon_widget_repr=vtk.vtkBalloonRepresentation()
    balloon_widget.SetRepresentation(balloon_widget_repr)

    aparc_lut=reader.get('aparc',None,lut=1)
    planeWidget.setLabelsLut(aparc_lut)

    def setSubj(event=None):
        global img, currSubj
        subj=select_subj_frame.get()
        currSubj=subj
        try:
            img=reader.get('MRI',subj,format='VTK',space=currSpace)
            aparc=reader.get('aparc',subj,format='vtk',space=currSpace)
        except Exception:
            img = None
            aparc = None

        if img is not None:
            planeWidget.SetInputData(img)
            planeWidget.On()
        else:
            planeWidget.Off()
        planeWidget.addLabels(aparc)
        outline.SetInputData(img)
        #update model
        model_list.changeSubj(currSubj)
        setModel()

        update_context()
        renWin.Render()

    #=========================================Load freeSurfer Model=========================

    # model=reader.get('MODEL',currSubj,name=availableModels[0],space=currSpace)
    #name -> (polydata, mapper, actor)
    models=dict()
    #
    # model_color=reader.get('MODEL',None,name=availableModels[0],color='T')
    # model_mapper=vtk.vtkPolyDataMapper()
    # model_actor=vtk.vtkActor()
    # model_properties=model_actor.GetProperty()
    # model_properties.SetColor(list(model_color[0:3]))
    # model_mapper.SetInputData(model)
    # model_actor.SetMapper(model_mapper)
    # volume_model=reader.get('model',currSubj,name=availableModels[0],volume=1)
    # add_solid_balloon(balloon_widget, model_actor,availableModels[0],volume_model )
    # ren.AddActor(model_actor)


    def setModel(event=None):
        requested=model_list.get()
        for _,_,actor in models.itervalues():
            actor.SetVisibility(0)

        for model_name in requested:
            poly_data,mapper,actor=models.get(model_name,(None,None,None))
            poly_data=reader.get('MODEL',currSubj,name=model_name,space=currSpace)
            if mapper is None:
                mapper=vtk.vtkPolyDataMapper()
                actor=vtk.vtkActor()
                actor.SetMapper(mapper)
                ren.AddActor(actor)
            actor.SetVisibility(1)
            mapper.SetInputData(poly_data)
            mapper.Update()
            model_color=reader.get('MODEL',None,name=model_name,color='T')
            model_properties=actor.GetProperty()
            model_properties.SetColor(list(model_color[0:3]))
            volume_model = reader.get('model', currSubj, name=model_name, volume=1)
            add_solid_balloon(balloon_widget, actor,model_name,volume_model )
            models[model_name]=(poly_data,mapper,actor)
        show_fibers()


    #=============================================Fibers====================================
    fibers_mapper=vtk.vtkPolyDataMapper()
    fibers_actor=vtk.vtkActor()
    fibers_actor.SetVisibility(0)
    fibers_actor.SetMapper(fibers_mapper)
    ren.AddActor(fibers_actor)
    fibers_lock=threading.Lock()
    fibers_working=False
    def show_fibers():
        global fibers,fibers_working
        if fibers_active.get():
            for w in widgets:
                w.configure(state='disabled')
            space_sel['state']='disabled'
            progress.set(0)
            fibers_working=True
            fibers_progress_bar['mode']='indeterminate'
            fibers_progress_bar.start(20)
            thread.start_new_thread(async_load_fibers,(model_list.get(),and_or_variable.get() ) )
            #async_load_fibers(model_name)
            fibers_progress_bar.after(20,refresh_display )
        else:
            fibers_actor.SetVisibility(0)
            refresh_display()

    def async_load_fibers(models,operation):
        global fibers_working,fibers
        fibers=reader.get('fibers', currSubj,waypoint=models,space=currSpace,operation=operation)
        #print 'finished reading fibers %s'%model_name
        fibers_mapper.SetInputData(fibers)
        fibers_actor.SetVisibility(1)
        add_fibers_balloon(balloon_widget, fibers_actor,'Fibers bundle')
        fibers_lock.acquire()
        fibers_working=False
        fibers_lock.release()
    def refresh_display(*args):
        fibers_lock.acquire()
        if fibers_working:
            fibers_progress_bar.after(100,refresh_display )
        else:
            renWin.Render()
            for w in widgets:
                w.configure(state='normal')
            space_sel['state']='readonly'
            fibers_progress_bar.stop()
            fibers_progress_bar['mode']='determinate'
            progress.set(100)
        fibers_lock.release()

    #================================CONTEXT==========================
    context_models=['3rd-Ventricle', '4th-Ventricle', '5th-Ventricle', 'Brain-Stem', 'CSF', 'Left-Lateral-Ventricle', 'Left-vessel', 'Right-Lateral-Ventricle', 'Right-vessel']
    context_dict={}
    def update_context():
        for m in context_dict.iterkeys():
            c_model,c_map,c_actor=context_dict[m]
            c_model=c_model=reader.get('model',currSubj,space=currSpace,name=m)
            if c_model is not None:
                c_map.SetInputData(c_model)
                c_actor.SetVisibility(1)
                add_solid_balloon(balloon_widget, c_actor,m )
            else:
                c_actor.SetVisibility(0)
            context_dict[m]=(c_model,c_map,c_actor)


    def change_context():
        #clean up
        for c_model,c_mapper,c_actor in context_dict.itervalues():
            balloon_widget.RemoveBalloon(c_actor)
            ren.RemoveActor(c_actor)

        context_dict.clear()
        for m in context_models:
            c_model=reader.get('model',currSubj,space=currSpace,name=m)
            c_mapper=vtk.vtkPolyDataMapper()
            c_mapper.SetInputData(c_model)
            c_mapper.Update()
            c_model_color=reader.get('MODEL',None,name=m,color='T')
            c_actor=vtk.vtkActor()
            c_actor.SetMapper(c_mapper)
            c_properties=c_actor.GetProperty()
            c_color=list(c_model_color[0:3])
            c_properties.SetColor(c_color)
            c_properties.SetOpacity(0.5)
            ren.AddActor(c_actor)
            volume_model=reader.get('model',currSubj,name=m,volume=1)
            add_solid_balloon(balloon_widget, c_actor,m,volume_model )
            context_dict[m]=(c_model,c_mapper,c_actor)


    #===============================================Inteface=================================

    root = tk.Tk()
    root.withdraw()
    top = tk.Toplevel(root)
    top.title('BraViz-MriSlicer')

    control_frame = tk.Frame(top,width=100)

    #===========================subjects list====================
    #select_subj_frame=tk.LabelFrame(control_frame,text='Subject',padx=10,pady=5,height='100')
    select_subj_frame=braviz.interaction.subjects_list(reader,setSubj,control_frame,text='Subject',padx=10,pady=5,height='100')
    select_subj_frame.pack(side='top',fill='x',expand='false')


    #======================Space change============================

    def spaceChange(event=None):
        global currSpace
        newSpace=space_var.get()
        if distance_w.GetWidgetState()!=0:
            translateMeasure(currSpace, newSpace)
        currSpace=newSpace
        setSubj(None)

    coordinates_label=tk.Label(control_frame,text='Coordinates:',pady=5)
    coordinates_label.pack(side='top')
    space_var=tk.StringVar()
    space_sel=ttk.Combobox(control_frame,textvariable=space_var)
    space_sel['values']=('World','Talairach','Dartel')
    space_sel['state']='readonly'
    space_sel.set(currSpace)
    space_sel.pack(side='top')
    space_sel.bind('<<ComboboxSelected>>',spaceChange)

    #==========================Show Fibers=======================

    class locked_IntVar(object):
        def __init__(self,x0):
            self.lock=threading.Lock()
            self.x=x0
        def set(self,v):
            self.lock.acquire()
            self.x=v
            self.lock.release()
        def get(self):
            self.lock.acquire()
            v=self.x
            self.lock.release()
            return v


    fibers_active=tk.BooleanVar()
    fibers_active.set(False)
    progress=tk.IntVar()
    progress.set(100)

    fibers_frame=tk.Frame(control_frame,padx=10,pady=1)
    fibers_check=tk.Checkbutton(fibers_frame,text='Fibers',command=show_fibers,variable=fibers_active)

    fibers_progress_bar=ttk.Progressbar(fibers_frame,orient='horizontal',length='150',mode='determinate',
                                        variable=progress)


    #=========================Show Planes========================
    def imagePlanesStatus():
        if active_planes.get():
            planeWidget.On()
        else:
            planeWidget.Off()
        renWin.Render()

    active_planes=tk.BooleanVar()
    active_planes.set(True)
    show_planes=tk.Checkbutton(fibers_frame,text='Plane',command=imagePlanesStatus,variable=active_planes,pady=10)
    show_planes.grid(column=0,row=0)
    fibers_check.grid(column=1,row=0)
    and_or_variable=tk.StringVar()
    and_or_variable.set('or')
    and_or_combo=ttk.Combobox(fibers_frame,textvariable=and_or_variable,values=['and','or'],state='readonly',width=4)
    and_or_combo.grid(row=0,column=2)
    fibers_progress_bar.grid(row=1,columnspan=3)
    fibers_frame.pack(side='top')
    #===========================models list=======================



    model_list=braviz.interaction.tk_gui.structureList(reader,currSubj,None,control_frame)
    model_list.pack(side='top',fill='both',expand=1)

    model_list.focus()


    class ctx_dialog(simpleDialog):
        def body(self,master):
            label=tk.Label(master,text='Select structures to show as context')
            label.grid(row=0,sticky='ew')
            self.select_model=braviz.interaction.structureList(reader,currSubj,None, master,initial_models=context_models,text='Model',padx=10,pady=5)
            self.select_model.grid(row=1,column=0,sticky='nsew')
            master.rowconfigure(1,weight=1)
            master.columnconfigure(0,weight=1)
        def apply(self):
            global context_models
            context_models=self.select_model.get()
            print context_models
            change_context()
            renWin.Render()

    def ctx_action(event=None):
        ctx_dialog(top,'Context')
        ctx_but.config(text='Change Context')


    apply_but=tk.Button(control_frame,text='Apply Selection',command=setModel,pady=0)
    apply_but.pack(side='top',fill='x',expand=0,pady=1)

    ctx_but=tk.Button(control_frame,text='Add Context',command=ctx_action,pady=0)
    ctx_but.pack(side='top',fill='x',expand=0,pady=1)


    widgets=[model_list, fibers_check, select_subj_frame, show_planes,ctx_but,apply_but,model_list]


    #=====================================================================
    display_frame = tk.Frame(top)
    control_frame.pack(side="left", anchor="n", fill="y", expand="false")
    display_frame.pack(side="left", anchor="n", fill="both", expand="true")
    renderer_frame = tk.Frame(display_frame)
    renderer_frame.pack(padx=3, pady=3,side="left", anchor="n",
                        fill="both", expand="true")

    render_widget = vtkTkRenderWindowInteractor(renderer_frame,
                                                rw=renWin,width=600,
                                                height=600)
    def clean_exit():
        global renWin
        print "adios"
        renWin.Finalize()
        del renWin
        render_widget.destroy()
        root.quit()
        root.destroy()
        quit()
    top.protocol("WM_DELETE_WINDOW", clean_exit)

    render_widget.pack(fill='both', expand='true')
    display_frame.pack(side="top", anchor="n", fill="both", expand="true")
    iact = render_widget.GetRenderWindow().GetInteractor()
    custom_iact_style=config.get_interaction_style()
    iact_style=getattr(vtk,custom_iact_style)()
    iact.SetInteractorStyle(iact_style)
    iact.SetPicker(picker)

    planeWidget.SetInteractor(iact)
    planeWidget.On()

    balloon_widget.SetInteractor(iact)
    balloon_widget.On()

    axes.SetInteractor(iact)
    axes.EnabledOn()
    axes.InteractiveOn()

    render_widget.GetRenderWindow().SetAlphaBitPlanes(1)
    render_widget.GetRenderWindow().SetMultiSamples(0)
    ren.SetUseDepthPeeling(1)


    render_widget.Render()
    setModel()
    cam1 = ren.GetActiveCamera()
    cam1.Elevation(80)
    cam1.SetViewUp(0, 0, 1)
    cam1.Azimuth(80)
    ren.ResetCameraClippingRange()

    iact.Initialize()
    renWin.Render()
    iact.Start()


    #=====================MEASURE WIDGET========================

    distance_w=vtk.vtkDistanceWidget()
    distance_wr=vtk.vtkDistanceRepresentation3D()
    distance_w.SetInteractor(iact)
    distance_w.SetRepresentation(distance_wr)
    distance_w.PickingManagedOn()
    distance_wr.SetHandleSize(0.5)
    distance_w.SetKeyPressActivationValue('m')
    distance_w.PickingManagedOn()
    distance_w.SetPriority(8)
    planeWidget.SetPriority(5)

    measure_tip=vtk.vtkTextActor()
    tip_coor=measure_tip.GetPositionCoordinate()
    tip_coor.SetCoordinateSystemToNormalizedViewport()
    measure_tip.SetPosition([0.5,0.95])
    measure_tip.SetInput("Press 'm' to measure")
    tip_prop=measure_tip.GetTextProperty()
    tip_prop.SetJustificationToCentered()
    tip_prop.SetFontSize(18)
    measure_tip.SetVisibility(0)
    ren.AddActor(measure_tip)
    # Start Tkinter event loop
    def show_measure_tip(obj,event):
        if event=='EnterEvent' and distance_w.GetEnabled()==0:
            measure_tip.SetVisibility(1)
        elif event in ['LeaveEvent','StartInteractionEvent']:
            measure_tip.SetVisibility(0)
        renWin.Render()



    iact.AddObserver(vtk.vtkCommand.EnterEvent,show_measure_tip)
    iact.AddObserver(vtk.vtkCommand.LeaveEvent,show_measure_tip)
    distance_w.AddObserver(vtk.vtkCommand.StartInteractionEvent,show_measure_tip)

    def translateMeasure(previous_space,new_space):
        x1=[0,0,0]
        x2=[0,0,0]
        distance_wr.GetPoint1WorldPosition(x1)
        distance_wr.GetPoint2WorldPosition(x2)
        pts=vtk.vtkPoints()
        pts.SetNumberOfPoints(2)
        pts.SetPoint(0, x1)
        pts.SetPoint(1, x2)
        poly_data=vtk.vtkPolyData()
        poly_data.SetPoints(pts)
        poly_data2=reader.transformPointsToSpace(poly_data, previous_space,currSubj , True)
        #Poly Data 2 is in world coordinates
        poly_data3=reader.transformPointsToSpace(poly_data2, new_space,currSubj , False)
        y1=poly_data3.GetPoint(0)
        y2=poly_data3.GetPoint(1)

        distance_wr.SetPoint1WorldPosition(y1)
        distance_wr.SetPoint2WorldPosition(y2)


    #========================Main Loop==========================
    root.mainloop()
