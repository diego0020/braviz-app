##############################################################################
#    Braviz, Brain Data interactive visualization                            #
#    Copyright (C) 2014  Diego Angulo                                        #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU Lesser General Public License as          #
#    published by  the Free Software Foundation, either version 3 of the     #
#    License, or (at your option) any later version.                         #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU Lesser General Public License for more details.                     #
#                                                                            #
#    You should have received a copy of the GNU Lesser General Public License#
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.   #
##############################################################################


from __future__ import division,print_function


import braviz
import numpy as np
import scipy.spatial


from braviz.visualization.simple_vtk import SimpleVtkViewer


__author__ = 'da.angulo39'


def _get_descriptors(aseg, labels, draw=False):
    if not hasattr(labels, "__iter__"):
        labels = [labels]

    data = aseg.get_data()
    pre_coords = np.zeros(data.shape, np.bool)
    for l in labels:
        pre_coords |= data == l

    coords = np.where(pre_coords)
    coords_h = np.array(
        (coords[0], coords[1], coords[2], np.ones(len(coords[0]))))
    affine = aseg.get_affine()
    mm_h = np.dot(affine, coords_h)
    mm = mm_h[0:3, :] / np.tile(mm_h[3, :], (3, 1))

    points = mm.T
    hull = scipy.spatial.ConvexHull(points)

    verts = points[hull.vertices]

    m_p = scipy.spatial.distance.pdist(verts)
    m = scipy.spatial.distance.squareform(m_p)

    max_distance = np.max(m)
    i1, i2 = np.unravel_index(np.argmax(m), m.shape)
    p1, p2 = verts[i1], verts[i2]

    # project into the plane perpendicular to p1-p2
    norm = (p2 - p1) / np.linalg.norm(p2 - p1)

    verts2 = verts - np.dot(verts, norm)[:, np.newaxis] * norm

    m_p2 = scipy.spatial.distance.pdist(verts2)
    m_2 = scipy.spatial.distance.squareform(m_p2)
    max_distance2 = np.max(m_2)
    i3, i4 = np.unravel_index(np.argmax(m_2), m_2.shape)
    p3, p4 = verts2[i3], verts2[i4]

    # project into line perependicular to p3-p4

    norm2 = (p4 - p3) / np.linalg.norm(p4 - p3)
    verts3 = verts2 - np.dot(verts2, norm2)[:, np.newaxis] * norm2

    m_p3 = scipy.spatial.distance.pdist(verts3)
    m_3 = scipy.spatial.distance.squareform(m_p3)
    max_distance3 = np.max(m_3)
    i5, i6 = np.unravel_index(np.argmax(m_3), m_3.shape)
    p5, p6 = verts3[i5], verts3[i6]

    if draw is True:
        import vtk
        viewer = SimpleVtkViewer()

        def paint_verts(vs, color, size=2):
            if vs.shape[1] != 3:
                vs = vs.T
            points = vtk.vtkPoints()
            points.SetNumberOfPoints(len(vs))
            len(vs)
            for i in xrange(len(vs)):
                points.SetPoint(i, vs[i, :])
            pd = vtk.vtkPolyData()
            pd.SetPoints(points)
            gf = vtk.vtkVertexGlyphFilter()
            gf.SetInputData(pd)
            gf.Update()
            gs = gf.GetOutput()
            ac = viewer.addPolyData(gs)
            prop = ac.GetProperty()
            prop.SetColor(color)
            prop.SetPointSize(size)

        def paint_line(p1, p2, color):
            line = vtk.vtkLineSource()
            line.SetPoint1(p1)
            line.SetPoint2(p2)
            line.Update()
            ac = viewer.addPolyData(line.GetOutput())
            ac.GetProperty().SetColor(color)
            ac.GetProperty().SetLineWidth(5)

        paint_verts(points, (1, 1, 1), size=1)
        viewer.start()

        paint_verts(verts, (1, 0, 0))
        paint_line(p1, p2, (1, 0, 0))
        viewer.start()

        c = np.dot((p2 + p1) / 2, norm) * norm
        paint_verts(verts2 + c, (1, 1, 0))
        paint_line(p3 + c, p4 + c, (1, 1, 0))
        viewer.start()

        c2 = (np.linalg.norm(p3 - p4) / 2 + np.dot(p3 + c, norm2)) * norm2 + c
        paint_verts(verts3 + c2, (1, 0, 1))
        paint_line(p5 + c2, p6 + c2, (1, 0, 1))
        viewer.start()

    return max_distance, max_distance2, max_distance3


def get_descriptors(aseg, labels, draw=False):
    """
    Calculate the longest axis in a structure, the second longest axis perpendicular to it, and the third axis
    perpendicular to both

    Args:
        aseg (nibabel.spatialimages.SpatialImage) : Label map
        labels (list) : list of integer labels to look for in the label map
        draw (bool) : If ``True`` the process will be illustrated in a
            :class:`~braviz.visualization.simple_vtk.SimpleVtkViewer`, press 'q' after each stage

    Returns:
        A tuple with the lengths of the three axes
    """
    try:
        return _get_descriptors(aseg, labels, draw)
    except Exception:
        return np.nan, np.nan, np.nan


if __name__ == "__main__":
    labels = [250, 251, 252, 253, 254, 255]
    reader = braviz.readAndFilter.BravizAutoReader()
    subj = reader.get("ids")[0]
    aseg = reader.get("APARC", subj)
    print(get_descriptors(aseg, labels, draw=True))
