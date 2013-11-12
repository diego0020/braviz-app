"Illustrate how to load and display Slicer 3d Models"
import Tkinter as tk
import ttk

import vtk
from vtk.tk.vtkTkRenderWindowInteractor import \
     vtkTkRenderWindowInteractor

import braviz.readAndFilter
from braviz.visualization import add_solid_balloon

currSubj='093'
chosen_models= {'CC_Anterior', 'CC_Central', 'CC_Mid_Anterior', 'CC_Mid_Posterior', 'CC_Posterior'}
currSpace='world'

reader=braviz.readAndFilter.kmc40AutoReader()
img=reader.get('MRI',currSubj,format='VTK',space=currSpace)
aparc=reader.get('aparc',currSubj,format='vtk',space=currSpace)

availableModels=reader.get('MODEL',currSubj,index='t')

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

planeWidget.SetResliceInterpolateToNearestNeighbour() # Sin interpolar

aparc_lut=reader.get('aparc',None,lut=1)
planeWidget.setLabelsLut(aparc_lut)

planeWidget.SetPicker(picker)
renWin.SetSize(600, 600)

balloon_widget=vtk.vtkBalloonWidget()
balloon_widget_repr=vtk.vtkBalloonRepresentation()
balloon_widget.SetRepresentation(balloon_widget_repr)

# An outline is shown for context.
outline = vtk.vtkOutlineFilter()
outline.SetInputData(img)

outlineMapper = vtk.vtkPolyDataMapper()
outlineMapper.SetInputConnection(outline.GetOutputPort())

outlineActor = vtk.vtkActor()
outlineActor.SetMapper(outlineMapper)
ren.AddActor(outlineActor)

# Tracts
tracts_actor=vtk.vtkActor()
tracts_mapper=vtk.vtkPolyDataMapper()
tracts_actor.SetMapper(tracts_mapper)
tracts_actor.SetVisibility(0)
ren.AddActor(tracts_actor)

def setSubj(event=None):
    global img, currSubj,availableModels,previous_selection
    subj=select_subj_frame.get()
    currSubj=subj
    img=reader.get(images_var.get(),subj,format='VTK',space=currSpace)
    aparc=reader.get('aparc',subj,format='vtk',space=currSpace)
    planeWidget.SetInputData(img)
    planeWidget.addLabels(aparc)
    availableModels=reader.get('MODEL',subj,index='t')
    availableModels.sort()
    outline.SetInputData(img)
    #update model
    select_model_frame.changeSubj(subj)
    if show_tracts_var.get():
        enque_calculate_fibers()
    refresh_display()
    
#=========================================Load freeSurfer Model=========================
#this dictionary will contain (model,mapper,actor) tupples
models={}
actor2model={} #used for picking
context_models={}

def addModel(model_name):
    #if already exists make visible
    if models.has_key(model_name):
        model,mapper,actor=models[model_name]
        if model_name in availableModels:
            model=reader.get('MODEL',currSubj,name=model_name,space=currSpace)            
            mapper.SetInputData(model)
            actor.SetVisibility(1)
            models[model_name]=(model,mapper,actor)
    else:
        #New model
        if model_name in availableModels:
            model=reader.get('MODEL',currSubj,name=model_name,space=currSpace)
            model_color=reader.get('MODEL',None,name=model_name,color='T')
            model_mapper=vtk.vtkPolyDataMapper()
            model_actor=vtk.vtkActor()
            model_properties=model_actor.GetProperty()
            model_properties.SetColor(list(model_color[0:3]))
            model_mapper.SetInputData(model)
            model_actor.SetMapper(model_mapper)
            ren.AddActor(model_actor)
            models[model_name]=(model,model_mapper,model_actor)
            actor2model[id(model_actor)]=model_name
    actor=models[model_name][2]
    model_volume=reader.get('model',currSubj,name=model_name,volume=1)
    add_solid_balloon(balloon_widget, actor, model_name,model_volume)

def removeModel(model_name):
    #check that it actually exists
    if not models.has_key(model_name):
        return
    model, mapper, actor=models.pop(model_name)
    ren.RemoveActor(actor)
    actor2model.pop(id(actor))
    balloon_widget.RemoveBalloon(actor)
    del actor
    del mapper
    del model


def add_tracts():
    models=select_model_frame.get()
    tracts=reader.get('fibers',currSubj,space=space_var.get(),waypoint=models,operation='or')
    #print currSubj, space_var.get(), models
    #print tracts
    tracts_mapper.SetInputData(tracts)
    tracts_actor.SetVisibility(1)
    refresh_display()
    #print models


def process_model(action,model):
    if action=='remove':
        removeModel(model)
    elif action=='add':
        addModel(model)
    else:
        print "unknown action %s"%action
    refresh_context()
    if show_tracts_var.get():
        enque_calculate_fibers()
    refresh_display()

queued_refresh=False
def refresh_display(*args):
    global queued_refresh          
    if not queued_refresh:
        top.after_idle(do_refresh)
        queued_refresh=True

def do_refresh():
    global queued_refresh
    renWin.Render()
    queued_refresh=False

queued_calculate_fibers=False
def enque_calculate_fibers(*args):
    global queued_calculate_fibers
    if not queued_calculate_fibers:
        top.after_idle(do_calculate_fibers)
        queued_calculate_fibers=True

def do_calculate_fibers():
    global queued_calculate_fibers
    add_tracts()
    queued_calculate_fibers=False

#=============================================Picking====================================
text2=vtk.vtkTextActor()
cor=text2.GetPositionCoordinate()
cor.SetCoordinateSystemToNormalizedDisplay()
text2.SetPosition([0.99,0.01])
text2.SetInput('probando')
tprop=text2.GetTextProperty()
tprop.SetJustificationToRight()
tprop.SetFontSize(18)
ren.AddActor(text2)
text2.SetVisibility(0)

highlighted_item=None
picked_actor=None
def picking(caller,event,*args):
    global highlighted_item,picked_actor
    x,y=caller.GetEventPosition()
    picked=picker.Pick(x,y,0,ren)
    picked_model=actor2model.get(id(picker.GetProp3D()))
    if highlighted_item:
        select_model_frame.itemconfigure(highlighted_item,selectbackground='')
    if picked_actor:
        picked_actor.GetProperty().SetEdgeVisibility(0)
        picked_actor=None
    if picked and picked_model:
        text2.SetInput(picked_model)
        text2.SetVisibility(1)
        i=availableModels.index(picked_model)
        select_model_frame.see(i)
        highlighted_item=i
        select_model_frame.itemconfigure(highlighted_item,selectbackground='sea green')
        picked_actor=picker.GetProp3D()
        picked_actor_property=picked_actor.GetProperty()
        picked_actor_property.SetEdgeVisibility(1)
        picked_actor_property.SetEdgeColor((1,1,1))
    else:
        text2.SetVisibility(0)
        highlighted_item=None

    #print picker
picker.SetPickFromList(0)
#===============================================Inteface=================================

root = tk.Tk()
root.withdraw()
top = tk.Toplevel(root)
top.title('BraViz-Mri Multi Slicer')

control_frame = tk.Frame(top,width=100)

#===========================subjects list====================
#select_subj_frame=tk.LabelFrame(control_frame,text='Subject',padx=10,pady=5,height='100')
select_subj_frame=braviz.interaction.subjects_list(reader,setSubj,control_frame,text='Subject',padx=10,pady=5,height='100')
select_subj_frame.pack(side='top',fill='x',expand='false')
ctxt_subject_idx=None
def subj_context_init(event):

    #print 'hola menu'
    subject_idx=select_subj_frame.subjects_list.nearest(event.y)
    subject=select_subj_frame.subjects_list.get(subject_idx)
    #print 'subject = %s'%subject
    subj_context_menu.entryconfig(0, label='Set %s as context'%subject,command=lambda :set_context(subject_idx))
    subj_context_menu.tk_popup(event.x_root, event.y_root)
    

def set_context(subject_idx):
    global ctxt_subject_idx
    clear_context()
    ctxt_subject_idx=subject_idx
    select_subj_frame.subjects_list.itemconfigure(subject_idx,bg='light grey')
    subject=select_subj_frame.subjects_list.get(subject_idx)
    for m in select_model_frame.get():
        mo=reader.get('model',subject,name=m,space=currSpace)
        mo_color=reader.get('MODEL',None,name=m,color='T')
        ma=vtk.vtkPolyDataMapper()
        ac=vtk.vtkActor()
        mo_properties=ac.GetProperty()
        mo_properties.SetColor(list(mo_color[0:3]))
        mo_properties.SetOpacity(0.2)
        ma.SetInputData(mo)
        ac.SetMapper(ma)
        ren.AddActor(ac)
        context_models[m]=(mo,ma,ac)
    refresh_display()    
    
def clear_context():
    global ctxt_subject_idx
    #print ctxt_subject_idx
    if ctxt_subject_idx is not None:
        select_subj_frame.subjects_list.itemconfigure(ctxt_subject_idx,bg='')
    ctxt_subject_idx=None
    for _,_,ac in context_models.itervalues():
        ren.RemoveActor(ac) 
    refresh_display()
    
def refresh_context():    
    if ctxt_subject_idx is not None:
        context_index=ctxt_subject_idx
        clear_context()
        set_context(context_index)
    
subj_context_menu=tk.Menu(select_subj_frame,title='hola',tearoff=0)

subj_context_menu.add_command(label='Set as context')
subj_context_menu.add_command(label='Clear context',command=clear_context)



subj_list=select_subj_frame.subjects_list
if (top.tk.call('tk', 'windowingsystem')=='aqua'):
    subj_list.bind('<2>', subj_context_init)
    subj_list.bind('<Control-1>', subj_context_init)
else:
    subj_list.bind('<3>', subj_context_init)

#======================Space change============================

def spaceChange(event=None):
    global currSpace
    newSpace=space_var.get()
    if distance_w.GetWidgetState()!=0:
        translateMeasure(currSpace, newSpace)
    currSpace=newSpace
    setSubj(None)
    refresh_context()

coordinates_label=tk.Label(control_frame,text='Coordinates:',pady=5)
coordinates_label.pack(side='top')
space_var=tk.StringVar()
space_sel=ttk.Combobox(control_frame,textvariable=space_var)
space_sel['values']=('World','Talairach','Dartel')
space_sel['state']='readonly'
space_sel.set(currSpace)
space_sel.pack(side='top')
space_sel.bind('<<ComboboxSelected>>',spaceChange)

#=========================Show Planes========================
planes_frame=tk.Frame(control_frame)
def imagePlanesStatus():
    if active_planes.get():
        planeWidget.On()
    else:
        planeWidget.Off()
    refresh_display()

active_planes=tk.BooleanVar()
active_planes.set(True)
show_planes=tk.Checkbutton(planes_frame,text='Show Plane',command=imagePlanesStatus,variable=active_planes,pady=10)
images_var=tk.StringVar()
images_var.set('MRI')
image_type=ttk.Combobox(planes_frame,textvariable=images_var,width=5)
image_type['values']=('MRI','APARC')
image_type['state']='readonly'
show_planes.grid(row=0,column=0,sticky='w')
image_type.grid(row=0,column=1,sticky='e')
planes_frame.pack(side='top')

previous_img='MRI'
mri_lut=vtk.vtkLookupTable()
mri_window_level=[0,0]
def change_img_type(event=None):
    global previous_img,mri_window_level,mri_lut
    if images_var.get()==previous_img:
        return
    #print "image changed to %s"%images_var.get()
    if images_var.get()=='MRI':
        img=reader.get('mri',currSubj,format='vtk',space=currSpace)
        img_lut=mri_lut
        
    elif images_var.get()=='APARC':
        mri_lut.DeepCopy(planeWidget.GetLookupTable())
        planeWidget.GetWindowLevel(mri_window_level)
        img=reader.get('aparc',currSubj,format='vtk',space=currSpace)
        img_lut=reader.get('aparc',currSubj,format='vtk',space=currSpace,lut='t')
    else:
        print "unknown image kind %s"%images_var.get()
        return
    planeWidget.SetInputData(img)
    outline.SetInputData(img)
    planeWidget.SetLookupTable(img_lut)
    planeWidget.SetWindowLevel(*mri_window_level)
    previous_img=images_var.get()
    renWin.Render()
image_type.bind('<<ComboboxSelected>>',change_img_type)         

#------------------------------------------------------------
show_tracts_var=tk.BooleanVar()
show_tracts_var.set(0)
def toggle_show_tracts(event=None):
    if show_tracts_var.get():
        add_tracts()
    else:
        tracts_actor.SetVisibility(0)
    refresh_display()
show_tracts_toggle=tk.Checkbutton(control_frame,text='Show tracts',variable=show_tracts_var,command=toggle_show_tracts)
show_tracts_toggle.pack(side='top')
#===========================models list=======================
select_model_frame=braviz.interaction.structureList(reader,currSubj,process_model, control_frame,text='Model',padx=10,pady=5)
select_model_frame.pack(side='top',fill='both',expand=1)







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
top.protocol("WM_DELETE_WINDOW", clean_exit)

render_widget.pack(fill='both', expand='true')                                            
display_frame.pack(side="top", anchor="n", fill="both", expand="true")
iact = render_widget.GetRenderWindow().GetInteractor()

planeWidget.SetInteractor(iact)
planeWidget.On()

balloon_widget.SetInteractor(iact)
balloon_widget.On()


cam1 = ren.GetActiveCamera()
cam1.Elevation(80)
cam1.SetViewUp(0, 0, 1)
cam1.Azimuth(80)
ren.ResetCameraClippingRange()
render_widget.Render()

iact.Initialize()
iact.AddObserver(vtk.vtkCommand.LeftButtonPressEvent,picking,10)
custom_iact_style=config.get_interaction_style()
iact_style=getattr(vtk,custom_iact_style)()
iact.SetInteractorStyle(iact_style)

refresh_display()
iact.Start()
setSubj()


#=====================MEASURE WIDGET========================

distance_w=vtk.vtkDistanceWidget()
distance_wr=vtk.vtkDistanceRepresentation3D()
distance_w.SetInteractor(iact)
distance_w.SetRepresentation(distance_wr)
distance_w.PickingManagedOn()
distance_wr.SetHandleSize(0.5)    
distance_w.SetKeyPressActivationValue('m')
distance_w.SetPriority(8)

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
    refresh_display()
    
    

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









# Start Tkinter event loop
root.mainloop()