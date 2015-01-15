
"""This module contains functions and classes which facilitate the display of brain data in the screen"""
from __future__ import division
from braviz.visualization.fmri_view import fMRI_blender

from braviz.visualization.simple_vtk import _test_arrow, SimpleVtkViewer, save_ren_win_picture, remove_nan_from_grid, \
    persistentImagePlane, OutlineActor, OrientationAxes, get_arrow, fibers_balloon_message, cursors, build_grid, \
    add_solid_balloon, add_simple_solid_balloon, add_fibers_balloon
import create_lut
from create_lut import get_colorbrewer_lut

from braviz.visualization.simple_vtk import SimpleVtkViewer


#Easy access to GridView
from braviz.visualization.grid_viewer import GridView
if __name__ == "__main__":

    test_grid=GridView()