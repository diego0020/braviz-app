.. module :: braviz.visualization

***********************************
Visualization
***********************************


3D Geometry Visualization
---------------------------



Braviz relies on `VTK <vtk.org>`_ for 3D visualization. The classes and functions in this module are meant to wrap
common vtk tasks in order to make it easier to implement brain visualizations. The main modules used for this
purpose are:

- Simple VTK (:mod:`~braviz.visualization.simple_vtk`) : Several utilities that help displaying data in vtk. Includes
  the :class:`~braviz.visualization.simple_vtk.SimpleVtkViewer`, a lightweight viewer useful for testing.

- Subject Viewer (:mod:`~braviz.visualization.subject_viewer`) : Implements a powerful viewer and Qt4 Widget which
  directly requests data, and handles subject and space changes.

- fMRI View (:mod:`~braviz.visualization.fmri_view`) : Utilities for displaying fMRI data.

.. toctree::
    :hidden:

    simple_vtk





Statistical Visualization
---------------------------

