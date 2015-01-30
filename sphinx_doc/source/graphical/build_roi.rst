ROI Builder
============

.. image:: images/roi_builder.png
    :align: center
    :width: 90%
    :alt: Roi builder screenshot

This application allows you to place spherical regions of interest on each subject of the sample. The sphere can be
adjusted independently for each subject, in size and in position. It is also possible to extrapolate the position of
the sphere from one subject to others in order to get plausible starting points, afterwards small adjustments
can be made. Before entering the real application you will find a start dialog.

In other words, in this application you define individual spheres for each subject. This spheres are grouped into
one name. Later on, the system accesses each sphere through the ROI name and subject id.

Start dialog
-------------

.. image:: images/roi_builder/roi_start.png
    :align: center
    :width: 50%
    :alt: Roi builder start screen

In the startup dialog you have to choose one of the following options

    -   **New ROI**: Create a new set of spheres (one for each subject), you will be asked for a name, a description
        and a coordinate system. Notice that spheres will, in general, only be spheres in one coordinate system. After
        applying a linear transformation they will likely look as ellipses, while after applying a non linear
        deformation they can look like blobs.
    -   **Load ROI**: Continue working on an existing sphere set.
    -   **Load scenario**: Load a scenario to re take the work exactly where you left it a previous time. See
        *Saving Scenarios* below

Main Application
------------------

The main application is composed of three panels, at the left there is a tabbed box where you can choose the
context or the sphere panel (look below). At the middle is a 3d viewer, and at the right side is a list of subjects
with checkboxes. The checkboxes represent the subjects to which a sphere has been defined. As you start saving spheres,
you will see check-marks start to appear. The objective of the application is to go through all subjects and defining
ROIs.

.. hint::
    You can press the right and left arrow keys in the keyboard to move trough the subjects in the list


Context Panel
^^^^^^^^^^^^^^

.. image:: images/roi_builder/roi_context.png
    :align: center
    :alt: Roi builder context panel



Sphere Panel
^^^^^^^^^^^^^^

.. image:: images/roi_builder/roi_sphere.png
    :align: center
    :alt: Roi builder sphere panel

.. hint::
    You can also move the sphere center towards the cursor by pressing the *c* key in the keyboard.

The extrapolate dialog
^^^^^^^^^^^^^^^^^^^^^^^^

.. image:: images/roi_builder/roi_extrapolate.png
    :align: center
    :width: 60%
    :alt: Roi builder extrapolate dialog