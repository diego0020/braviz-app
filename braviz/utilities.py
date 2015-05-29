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


"""Utility functions used in braviz library but not directly related to the interactive visual analysis of brain data"""
from __future__ import print_function
import contextlib
import os
from collections import defaultdict
import logging
import subprocess

def set_pyqt_api_2():
    import sip
    sip.setapi('QDate',2)
    sip.setapi('QDateTime',2)
    sip.setapi('QString',2)
    sip.setapi('QTextStream',2)
    sip.setapi('QTime',2)
    sip.setapi('QUrl',2)
    sip.setapi('QVariant',2)

def configure_logger_from_conf(app_name="Braviz"):
    from braviz.readAndFilter.config_file import get_apps_config
    conf = get_apps_config()
    log_out = conf.get("Braviz", "logger")
    if log_out[0] == 'c':
        configure_console_logger(app_name)
    else:
        configure_logger(app_name)


def configure_logger(app_name):
    """
    Helper function to configure loggers in similar ways from all the applications
    """
    import logging
    import datetime
    from braviz.readAndFilter import braviz_auto_dynamic_data_root
    now = datetime.datetime.now()
    time_str = now.strftime("%d_%m_%y-%Hh%Mm%Ss")
    path_root = os.path.join(braviz_auto_dynamic_data_root(), "logs")
    if not os.path.isdir(path_root):
        os.mkdir(path_root)
    log_file = os.path.join(path_root, "%s_%s.txt" % (app_name, time_str))
    format_str = "%(asctime)s %(levelname)s %(name)s %(funcName)s ( %(lineno)d ) : %(message) s"
    try:
        logging.basicConfig(
            filename=log_file, level=logging.INFO, format=format_str)
    except Exception:
        print("couldnt create file logger in file %s" % log_file)
        print("falling back to console logger")
        logging.basicConfig(level=logging.INFO, format=format_str)
    logging.captureWarnings(True)


def configure_console_logger(app_name):
    """
    Helper function to configure loggers to console for using while implementing/debugging
    """
    import logging
    format_str = "%(asctime)s %(levelname)s %(name)s %(funcName)s ( %(lineno)d ) : %(message) s"
    logging.basicConfig(level=logging.INFO, format=format_str)
    logging.captureWarnings(True)


@contextlib.contextmanager
def working_directory(path):
    """A context manager which changes the working directory to the given
    path, and then changes it back to its previous value on exit.

    """
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)

from contextlib import contextmanager


@contextmanager
def ignored(*exceptions):
    """A context manager which ignores exceptions of specific types"""
    try:
        yield
    except exceptions as e:
        log = logging.getLogger(__name__)
        log.exception(e)
        pass


def recursive_default_dict():
    """A default dict which by default contains default dicts which by default contain default dicts...."""
    return defaultdict(recursive_default_dict)


def get_leafs(rec_dict, name):
    """ input should be a recursive dicitionary whose elements are dictionaries, and a base name
    output will be a list of leafs, this is, elements which contain empty dictionaries as sons
    names in the output list will have the structure name:grandparent:parent:leaf"""
    if len(rec_dict) == 0:
        return [name]
    leafs = []
    for k, sub_d in rec_dict.iteritems():
        sub_leafs = get_leafs(sub_d, k)
        sub_leafs = map(lambda x: ':'.join((name, x)), sub_leafs)
        leafs.extend(sub_leafs)
    return leafs


def remove_non_ascii(s):
    return str("".join(i for i in s if ord(i) < 128))


def show_error(error_message):
    from PyQt4 import QtGui
    app = QtGui.QApplication([])
    dialog = QtGui.QMessageBox(
        QtGui.QMessageBox.Critical, "Braviz", error_message, QtGui.QMessageBox.Abort)
    dialog.show()
    app.exec_()

_child_processes = []
_collect_processes_timer = None

def launch_sub_process(*args,**kwargs):
    """
    Uses :class:`subprocess.Popen` to launch a new process.

    A qtimer is used to periodically collect exit status of finished processes and in this way
    avoid zombie processes. Requires the QT event loop to be running.

    All arguments are passed through to the Popen Constructor.

    """
    global _collect_processes_timer
    p = subprocess.Popen(*args, **kwargs)
    _child_processes.append(p)
    if _collect_processes_timer is None:
        from PyQt4.QtCore import QTimer

        def wait_for_sub_processes():
            finished = []
            log = logging.getLogger(__name__)
            log.info("Checking for finished sub_processes")
            for i, p in enumerate(_child_processes):
                status = p.poll()
                if status is not None:
                    finished.append(i)
                    log.info("process %s terminated",p.pid )
            for i in reversed(finished):
                _child_processes.pop(i)
            if log.isEnabledFor(logging.INFO):
                pids = [str(p.pid) for p in _child_processes]
                log.info("Acttive subprocesses: %s"," ".join(pids))
        _collect_processes_timer = QTimer()
        _collect_processes_timer.timeout.connect(wait_for_sub_processes)
        # timeout each five minutes or 300 seconds
        _collect_processes_timer.start(300000)
