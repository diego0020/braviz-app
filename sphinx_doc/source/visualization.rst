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


The module :mod:`~braviz.visualization.fmri_view` contains some low level utilities for displaying fMRI data.
The module :mod:`~braviz.visualization.checkerboard_view` implements a widget that shows two images in a checkboard
pattern. It is intended to check the registration between different modalities.

.. toctree::
    :hidden:

    simple_vtk
    subject_viewer
    fmri_view
    checkboard_view






Statistical Visualization
---------------------------

