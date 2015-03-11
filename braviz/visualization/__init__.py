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


"""This module contains functions and classes which facilitate the display of brain data in the screen"""
from __future__ import division
from braviz.visualization.fmri_view import fMRI_blender

from braviz.visualization.simple_vtk import _test_arrow, SimpleVtkViewer, save_ren_win_picture, remove_nan_from_grid, \
    persistentImagePlane, OutlineActor, OrientationAxes, get_arrow, fibers_balloon_message, cursors, build_grid, \
    add_solid_balloon, add_simple_solid_balloon, add_fibers_balloon

from braviz.visualization.simple_vtk import SimpleVtkViewer


