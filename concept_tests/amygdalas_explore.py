from __future__ import division
import math
from os.path import join as path_join
from itertools import izip

import vtk
import numpy as np

import braviz
from braviz.visualization.create_lut import get_colorbrewer_lut

__author__ = 'Diego'

scalar_column='WMIIQ'

reader=braviz.readAndFilter.BravizAutoReader()
viewer=braviz.visualization.simpleVtkViewer()

subj_ids=reader.get('ids')

amygdalas={}
for subj in subj_ids:
    #amygdalas[subj]=reader.get('model',subj,name='Left-Amygdala',space='talairach')
    amyg1=reader.get('model',subj,name='Left-Amygdala',space='world')
    #center at zero
    center=amyg1.GetCenter()
    trans = vtk.vtkTransformPolyDataFilter()
    t = vtk.vtkTransform()
    t.Identity()
    t.Translate(center)
    t.Inverse()
    trans.SetTransform(t)
    trans.SetInputData(amyg1)
    trans.Update()
    amyg2=trans.GetOutput()
    amygdalas[subj]=amyg2



actors_dict={}
subj_dir={}
for subj in subj_ids:
    actor=viewer.addPolyData(amygdalas[subj])
    actors_dict[actor]=subj
    subj_dir[subj]=actor

#color
csv_file=path_join(reader.get_data_root(),'test_small.csv')
csv_codes=braviz.readAndFilter.read_csv.get_column(csv_file,'code')
csv_data=braviz.readAndFilter.read_csv.get_column(csv_file,scalar_column,True)
#build dict
csv_data_dict={}
for code,datum in izip(csv_codes,csv_data):
    if not math.isnan(datum):
        csv_data_dict[code]=datum

#build lut
scalar_lut=get_colorbrewer_lut(min(csv_data),max(csv_data),'PuBuGn',9)

def get_color(id):
    scalar=csv_data_dict.get(id,float('nan'))
    output=scalar_lut.GetColor(scalar)
    #output=map(lambda x:x/255,output)
    return output
    #return [random.random() for i in range(3)]


for actor,id in actors_dict.iteritems():
    actor.GetProperty().SetColor(get_color(id))


#balloons

balloon_widget=vtk.vtkBalloonWidget()
balloon_rep=vtk.vtkBalloonRepresentation()
balloon_widget.SetRepresentation(balloon_rep)
balloon_widget.SetInteractor(viewer.iren)
balloon_widget.On()

for actor,id in actors_dict.iteritems():
    message="%s\n%s : %.2f"%(id,scalar_column,csv_data_dict.get(id,float('nan')))
    balloon_widget.AddBalloon(actor,message)
#order

#calculate bounds
def get_max_diagonal(actor):
    Xmin, Xmax, Ymin, Ymax, Zmin, Zmax=actor.GetBounds()
    return math.sqrt((Xmax-Xmin)**2+(Ymax-Ymin)**2+(Zmax-Zmin)**2)

max_space=max([get_max_diagonal(actor) for actor in actors_dict])
max_space*=0.8
#calculate renWin proportions
width,height=viewer.renWin.GetSize()
row_proportion=width/height
total_area=width*height
total_objects=len(subj_ids)
area_per_object=total_area/total_objects
n_row=round(math.sqrt(len(subj_ids)/row_proportion))
n_col=math.ceil(len(subj_ids)/n_row)

sorted_subj=sorted(subj_ids,key=lambda x:csv_data_dict.get(x,float('+inf')))
print sorted_subj
#positions_dict={}
for i,subj in enumerate(sorted_subj):
    actor=subj_dir[subj]
    column=i%n_col
    row=i//n_col
    x=column*max_space
    y=row*max_space
    actor.SetPosition(x ,y , 0)
#    positions_dict[actor]=(x,y,0)


viewer.ren.GradientBackgroundOn()
viewer.ren.SetBackground2(0.5,0.5,0.5)
viewer.ren.SetBackground(0.2,0.2,0.2)

#camera
viewer.renWin.Render()
cam1=viewer.ren.GetActiveCamera()
cam1.ParallelProjectionOn()
cam1.SetFocalPoint(n_col*max_space/2-max_space/2,n_row*max_space/2-max_space/2,0)
cam1.SetViewUp(0,-1,0)
cam1.SetParallelScale(0.55*n_row*max_space)
cam_distance=cam1.GetDistance()
cam1.SetPosition(n_col*max_space/2-max_space/2,n_row*max_space/2-max_space/2,-1*cam_distance)

#interaction
#viewer.iren.SetInteractorStyle(vtk.vtkInteractorStyleImage())
viewer.iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballActor())

first_time=True
modified_actor=None

def register_change(caller=None,envent=None):
    global modified_actor,panning
    panning = False
    if modified_actor is not None:
        return
    modified_actor=caller


def after_intareaction(caller=None,event=None):
    global modified_actor
    if modified_actor is not None:
        mimic_actor(modified_actor)

    modified_actor=None

def mimic_actor(caller=None,event=None):
    global first_time
    #orig_pos=np.array(positions_dict[caller])
    for ac in actors_dict:
        if ac is not caller:
            #delta_pos=caller.GetPosition()-orig_pos
            #ac.SetPosition(positions_dict[ac]+delta_pos)
            ac.SetOrientation(caller.GetOrientation())
            ac.SetScale(caller.GetScale())

for actor in actors_dict:
    actor.AddObserver(vtk.vtkCommand.PickEvent,register_change)

def wheel_zoom(caller=None,event=None):
    factor=0.5
    if event=='MouseWheelForwardEvent':
        cam1.SetParallelScale(cam1.GetParallelScale()*factor)
    else:
        cam1.SetParallelScale(cam1.GetParallelScale() / factor)
    viewer.iren.Render()

panning=False
panning_start_pos=None
cam_pos_start_pos=None
cam_focal_start_pos=None
def pan(caller=None, event=None):
    global panning,panning_start_pos,cam_focal_start_pos,cam_pos_start_pos
    if event=='MiddleButtonPressEvent':
        event_pos_x,event_pos_y=caller.GetEventPosition()
        if(viewer.ren.PickProp(event_pos_x,event_pos_y) is not None):
            panning=False
            return
        panning=True
        panning_start_pos=np.array(caller.GetEventPosition())
        cam_pos_start_pos=np.array(cam1.GetPosition())
        cam_focal_start_pos=np.array(cam1.GetFocalPoint())
    else:
        if panning==False:
            return
        if event=='MiddleButtonReleaseEvent':
            panning=False
    delta=caller.GetEventPosition()-panning_start_pos
    delta=(delta[0],-delta[1],0)
    cam1.SetPosition(cam_pos_start_pos-delta)
    cam1.SetFocalPoint(cam_focal_start_pos-delta)
    caller.Render()
    #print "pan: %s"%event
viewer.iren.AddObserver(vtk.vtkCommand.EndInteractionEvent, after_intareaction)
viewer.iren.AddObserver(vtk.vtkCommand.MouseWheelForwardEvent, wheel_zoom)
viewer.iren.AddObserver(vtk.vtkCommand.MouseWheelBackwardEvent, wheel_zoom)
viewer.iren.AddObserver(vtk.vtkCommand.MiddleButtonPressEvent, pan)
viewer.iren.AddObserver(vtk.vtkCommand.MouseMoveEvent, pan)
viewer.iren.AddObserver(vtk.vtkCommand.MiddleButtonReleaseEvent, pan,100)

def print_event(caller=None,event=None):
    print event



viewer.iren.Start()