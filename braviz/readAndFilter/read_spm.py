from __future__ import division
from scipy import io as sio
from itertools import izip
from collections import namedtuple
import numpy as np

__author__ = 'Diego'

def get_contrasts_dict(spm_file_path):
    spm_file = sio.loadmat(spm_file_path)
    spm_struct = spm_file["SPM"][0,0]
    contrasts_info = spm_struct["xCon"]
    n_contrasts = contrasts_info.shape[1]
    contrast_names = {}
    for i in xrange(n_contrasts):
        contrast_names[i+1] = contrasts_info[0,i]["name"][0]
    return contrast_names

ContrastInfo = namedtuple("ContrastInfo",("name","design"))
ConditionInfo = namedtuple("CondisionInfo",("name","onsets","durations"))

class SpmFileReader(object):
    def __init__(self,spm_file_path):
        self.spm = sio.loadmat(spm_file_path)["SPM"][0,0]
        self.__units = self.spm["xBF"]["UNITS"][0,0][0]
        self.__time_bin= float(self.spm["xBF"][0,0]["dt"][0,0])
        self.__tr_divisions = int(self.spm["xBF"][0,0]["T"][0,0])
        self.__n_scans = int(self.spm["nscan"][0,0])
        self.__tr = float(self.spm["xY"]["RT"][0,0][0,0])
        self.__conditions = None
        self.__constrasts = None

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
        if self.__constrasts is None:
            self.__parse_contrasts()
        return self.__constrasts

    @property
    def tr(self):
        return self.__tr

    @property
    def n_scans(self):
        return self.__n_scans

    @property
    def conditions(self):
        if self.__conditions is None:
            self.__parse_conditions()
        return self.__conditions

    def get_time_vector(self):
        TR = self.tr
        n_scans = self.n_scans
        time_bin = self.__time_bin
        return np.arange(0,TR*n_scans,time_bin)

    def get_condition_block(self,index):
        cond = self.conditions[index]
        cond_onsets = cond.onsets
        cond_durations = cond.durations
        tr_divisions = self.__tr_divisions
        units = self.__units
        time_bin = self.__time_bin
        condition = np.zeros(self.__n_scans*tr_divisions)
        for onset,duration in izip(cond_onsets,cond_durations):
            onset_d = onset*tr_divisions if units == "scans" else int(onset/time_bin)
            dur_d = duration*tr_divisions if units == "scans" else int(duration/time_bin)
            condition[onset_d:onset_d+dur_d]=1
        return condition
