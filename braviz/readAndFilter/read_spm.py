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


from __future__ import division
from scipy import io as sio
from itertools import izip
from collections import namedtuple
import numpy as np

__author__ = 'Diego'

def get_contrasts_dict(spm_file_path):
    """
    Parse information about existing contrasts from an spm file

    Args:
        spm_file_path (str) : Path to ``spm.mat`` file

    Returns:
        A dictionary with contrast indexes (starting at 1) for keys, and contrast names for values
    """
    spm_file = sio.loadmat(spm_file_path)
    spm_struct = spm_file["SPM"][0,0]
    contrasts_info = spm_struct["xCon"]
    n_contrasts = contrasts_info.shape[1]
    contrast_names = {}
    for i in xrange(n_contrasts):
        contrast_names[i+1] = contrasts_info[0,i]["name"][0]
    return contrast_names

ContrastInfo = namedtuple("ContrastInfo",("name","design"))
ConditionInfo = namedtuple("ConditionInfo",("name","onsets","durations"))

class SpmFileReader(object):
    "Helper class to read data from an SPM file"

    def __init__(self,spm_file_path):
        """
        Helper class to read data from an SPM file"

        Args:
            spm_file_path (str) : Path to ``spm.mat`` file
        """
        self.spm = sio.loadmat(spm_file_path)["SPM"][0,0]
        self.__units = self.spm["xBF"]["UNITS"][0,0][0]
        self.__time_bin= float(self.spm["xBF"][0,0]["dt"][0,0])
        self.__tr_divisions = int(self.spm["xBF"][0,0]["T"][0,0])
        self.__n_scans = int(self.spm["nscan"][0,0])
        self.__tr = float(self.spm["xY"]["RT"][0,0][0,0])
        self.__conditions = None
        self.__constrasts = None
        self.__experiment_samples = None

    def __parse_contrasts(self):
        spm_struct = self.spm
        contrasts_info = spm_struct["xCon"]
        n_contrasts = contrasts_info.shape[1]
        contrasts = {}
        for i in xrange(n_contrasts):
            name = contrasts_info[0,i]["name"][0]
            design = contrasts_info[0,i]["c"].squeeze()
            stat = contrasts_info[0,i]["STAT"][0]
            assert stat == "T"
            contrasts[i+1] = ContrastInfo(name,design)
        self.__constrasts = contrasts

    def __parse_conditions(self):
        session = self.spm["Sess"]
        n_conds = session["U"][0,0].shape[1]
        conditions = []
        for i in xrange(n_conds):
            session_info = session["U"][0, 0][0, i]
            cond_name = session_info["name"][0,0][0]
            cond_onsets = session_info["ons"][:,0].astype(np.int)
            cond_durations = session_info["dur"][:,0]
            cond = ConditionInfo(cond_name,cond_onsets,cond_durations)
            conditions.append(cond)
        self.__conditions = conditions

    @property
    def contrasts(self):
        """
        Existing contrast design arrays

        Returns:
            A named tuple (see :func:`collections.namedtuple`) with contrast name as first component (str), and
            the contrast design array as second component (numpy.array)
        """
        if self.__constrasts is None:
            self.__parse_contrasts()
        return self.__constrasts

    @property
    def tr(self):
        """
        The TR time in the experiment
        """
        return self.__tr

    @property
    def n_scans(self):
        """
        The number of scans in the experiment
        """
        return self.__n_scans

    @property
    def conditions(self):
        """
        Experimental conditions in the paradigm

        Returns:
            A named tuple (see :func:`collections.namedtuple`) with condition name as first component (str),
            onsets (numpy.ndarray) as second argument, and durations (numpy.array) as third argument
        """
        if self.__conditions is None:
            self.__parse_conditions()
        return self.__conditions

    def get_time_vector(self):
        """
        Gets a vector containing time values for the duration of the experiment

        Returns:
            :class:`numpy.ndarray` with time values across the duration of the experiment
        """
        #TODO: Decrease resolution
        tr = self.tr
        n_scans = self.n_scans
        time_bin = self.__time_bin
        time_vec = np.arange(0,tr*n_scans,time_bin)
        #time_vec = np.arange(0,tr*n_scans,TR)
        self.__experiment_samples = time_vec.shape
        return time_vec

    def get_condition_block(self,index):
        """
        Gets a block signal representing a condition

        Returns:
            :class:`numpy.ndarray` of the same length as the one returned by :meth:`get_time_vector`, it will be 1 when
            the condition is active, and 0 otherwise
        """
        cond = self.conditions[index]
        cond_onsets = cond.onsets
        cond_durations = cond.durations
        tr_divisions = self.__tr_divisions
        #tr = self.tr
        units = self.__units
        time_bin = self.__time_bin
        if self.__experiment_samples is None:
            self.get_time_vector()
        condition = np.zeros(self.__experiment_samples)
        for onset,duration in izip(cond_onsets,cond_durations):
            onset_d = onset*tr_divisions if units == "scans" else int(onset/time_bin)
            #onset_d = onset if units == "scans" else int(round(onset/tr))
            dur_d = duration*tr_divisions if units == "scans" else int(duration/time_bin)
            #dur_d = duration if units == "scans" else int(round(duration/tr))
            condition[onset_d:onset_d+dur_d]=1
        return condition

    def get_contrast_names(self):
        """
        A dictionary with contrast names

        Returns:
            A dictionary with contrast indexes (starting at 1) for keys and contrast names for values
        """
        contrasts = self.contrasts
        contrast_names = dict(( (k,v.name) for k,v in contrasts.iteritems()))
        return contrast_names