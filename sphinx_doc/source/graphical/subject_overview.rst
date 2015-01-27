Subject Overview
==================

.. image:: images/subj_overview.png
    :align: center
    :width: 90%
    :alt: Subject overview screenshot

This is the largest application in the braviz systems. It provides access to several kinds of neuro-image based data
for a single subject in the same view. The kind of data and visualization parameters can be configured using individual
controls. Afterwards it is possible to cycle through the subjects keeping this parameters constant.

This application sends a message to the rest of the system when the current subject changes. It also listens for
messages indicating a subject change, and when it receives one switches to that subject. If you want to avoid that
behaviour, press the keychain button at the right side of the subject widget.

Most of the application interface is occupied by a 3d viewer (see :doc:`3dviews`). At the left side is the control
panel, where the graphical attributes for the different data types can be set. This panel includes tabs for controling
the list of available subjects, and for showing additional details.  At the lower left is a small panel for changing
the coordinate system (see :doc:`concepts`) and for resetting the camera to pre defined locations.

Under the main 3d viewer is a widget that displays the current subject and allows you to change it, and at the
very bottom is a *context panel* which provides values for certain variables for the current subject.

.. hint::
    The control panel, context panel, and the subject widget can be hidden in order to provide more room
    for the 3d view. Move the mouse to their border until you get
    a cursor with two arrows, then click and drag to hide (or enlarge) these panels.

Changing subjects
-------------------

.. image:: images/subject_overview/select_subject.png
    :align: center
    :alt: Subject selection widget

This widget displays the current subject and lets you change it. The arrow buttons can be used to select the
previous and next subjects based on the list shown in the *Subjects tab* of the control panel. You can also click
on the text area and write the id of a subject using the keyboard. Notice a message will be broad-casted to all other
applications indicating the new subject.

The keychain button allows you to lock the current subject. In the locked status it will become impossible to change
the current subject, neither by using the other controls in this widget nor by messages from other applications.

The context panel
------------------

.. image:: images/subject_overview/context.png
    :align: center
    :width: 100%
    :alt: Context panel

The view panel
---------------

.. image:: images/subject_overview/view.png
    :align: center
    :width: 30%
    :alt: View panel

The control panel
------------------

.. image:: images/subject_overview/control.png
    :align: center
    :width: 80%
    :alt: Control panel tabs

Subject tab
^^^^^^^^^^^^

.. image:: images/subject_overview/subject_tab.png
    :align: center
    :width: 50%
    :alt: Subject tab


Details tab
^^^^^^^^^^^^

.. image:: images/subject_overview/details_tab.png
    :align: center
    :width: 50%
    :alt: Details tab

Images tab
^^^^^^^^^^^^

.. image:: images/subject_overview/images_tab.png
    :align: center
    :width: 50%
    :alt: Images tab

fMRI tab
^^^^^^^^^^^^

.. image:: images/subject_overview/fmri_tab.png
    :align: center
    :width: 50%
    :alt: fMRI tab

Segmentation tab
^^^^^^^^^^^^^^^^^^

.. image:: images/subject_overview/subject_tab.png
    :align: center
    :width: 50%
    :alt: Subject tab

Tractography tab
^^^^^^^^^^^^^^^^^^

.. image:: images/subject_overview/tractography_tab.png
    :align: center
    :width: 50%
    :alt: Tractography tab


Tracula tab
^^^^^^^^^^^^^^^^^^

.. image:: images/subject_overview/tracula_tab.png
    :align: center
    :width: 50%
    :alt: Tracula tab

Surfaces tab
^^^^^^^^^^^^^^^^^^

.. image:: images/subject_overview/surfaces_tab.png
    :align: center
    :width: 50%
    :alt: Surfaces tab

Scenarios
------------

Saving and loading