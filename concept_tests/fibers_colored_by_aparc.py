from __future__ import division, print_function
import braviz
import braviz.readAndFilter
import braviz.visualization.simple_vtk
import braviz.readAndFilter.images
import braviz.readAndFilter.transforms
import numpy as np

def main(subj):
    space = "diff"
    reader = braviz.readAndFilter.BravizAutoReader()
    lut = reader.get("fibers",subj,space="subject",scalars="aparc",lut=True)
    pd = reader.get("fibers",subj,scalars="aparc",space=space)
    #pd2 = reader.get("fibers",subj,space=space)
    n_img = reader.get("label",subj,name="aparc",space=space)
    v_img = braviz.readAndFilter.images.nibNii2vtk(n_img)
    img2 = braviz.readAndFilter.transforms.applyTransform(v_img,np.linalg.inv(n_img.get_affine()),interpolate=False)
    img = reader.get("label",subj,name="aparc",space=space,format="vtk")

    v = braviz.visualization.simple_vtk.SimpleVtkViewer()
    ac = v.addPolyData(pd, lut)
    #ac2 = v.addPolyData(pd2)
    pw = v.addImg(img)
    pw.SetLookupTable(lut)
    pw.SetResliceInterpolateToNearestNeighbour()
    v.start()


if __name__ == "__main__":
    main(326)