from __future__ import division
import braviz


__author__ = 'da.angulo39'

SUBJ=119
reader = braviz.readAndFilter.BravizAutoReader()

scalars = ['curv',
 'area',
 'avg_curv',
 'thickness',
 'volume',
 'sulc',
 ]

partitions = [
 'aparc.DKTatlas40',
 'aparc',
 'BA',
 'aparc.a2009s']

