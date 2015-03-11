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


# Import and filter
from __future__ import division, print_function

from braviz.readAndFilter.cache import cache_function

from braviz.readAndFilter.config_file import get_apps_config as __get_config
from braviz.readAndFilter.images import write_vtk_image, write_nib_image, numpy2vtk_img, nifti_rgb2vtk
from braviz.readAndFilter.transforms import numpy2vtkMatrix, transformGeneralData

from filter_fibers import filter_polylines_with_img, filterPolylinesWithModel, extract_poly_data_subset, \
    filter_polylines_by_scalar

# Easy access to kmc readers

# read configuration file and decide which project to expose
__config = __get_config()
PROJECT = __config.get_project_name()


def get_reader_class(project):
    import importlib
    import inspect
    from braviz.readAndFilter.base_reader import BaseReader
    module = importlib.import_module(
        'braviz.readAndFilter.%s' % project.lower())
    pred = lambda c: inspect.isclass(c) and issubclass(c, BaseReader)
    candidate_classes = [c for c in inspect.getmembers(module, pred)]
    project_upper = project.upper()
    candidate_classes2 = sorted([c for c in candidate_classes if c[0].upper().startswith(project_upper)],
                                key=lambda x: x[0])

    return candidate_classes2[0][1]


project_reader = get_reader_class(PROJECT)

BravizAutoReader = project_reader.get_auto_reader
braviz_auto_data_root = project_reader.get_auto_data_root
braviz_auto_dynamic_data_root = project_reader.get_auto_dyn_data_root

if __name__ == "__main__":
    __root = braviz_auto_data_root()
    __reader = BravizAutoReader()
    print(__root)
