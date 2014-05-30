'''
Created on 27/08/2013

@author: da.angulo39
'''
import vtk
import numpy as np

import braviz


r=braviz.readAndFilter.BravizAutoReader()
fib=r.get('fibers','093')
struct=r.get('Model','093',name='Brain-Stem')

def compute_fiber_lengths(fib):
    if not fib.GetNumberOfLines()==fib.GetNumberOfCells():
        print "Error, fib must contain only lines"
        raise Exception("Error, fib must contain only lines")
    lengths={}
    def line_length(pl):
        npts=pl.GetNumberOfPoints()
        length=0
        pts=pl.GetPoints()
        pt1=pts.GetPoint(0)
        for i in xrange(1,npts):
            pt2=pts.GetPoint(i)
            length+=np.linalg.norm(np.subtract(pt1,pt2))
            pt1=pt2
        return length
    

    for i in xrange(fib.GetNumberOfLines()):
        lengths[i]=line_length(fib.GetCell(i))
    return lengths       

compute_fiber_lengths(fib)

def add_fibers_balloon(balloon_widget,fib_actor,name=None):
    mapper=fib_actor.GetMapper()
    poly_data=mapper.GetInput()
    d=compute_fiber_lengths(poly_data).values()
    message="""Number of fibers: %.2f
Mean Length: %.2f
Max: %.2f
Min: %.2f
Std: %.2f"""%(len(d),np.mean(d),np.max(d),np.min(d),np.std(d))
    if name is not None:
        message=name+message
    else:
        message='Fiber Bundle\n'+message
    balloon_widget.AddBalloon(fib_actor,message)

#===================
v=braviz.visualization.simpleVtkViewer()
actor=v.addPolyData(fib)
balloon=vtk.vtkBalloonWidget()
balloon_rep=vtk.vtkBalloonRepresentation()
balloon.SetRepresentation(balloon_rep)
balloon.SetInteractor(v.iren)
balloon.On()

add_fibers_balloon(balloon, actor)
v.start()