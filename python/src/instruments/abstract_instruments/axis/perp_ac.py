#!/usr/bin/python
# -*- coding: utf-8 -*-
##
# perp_ac.py: AxisCollection (AC) that contains a list of perpendicular ACs
##
# © 2013 Steven Casagrande (scasagrande@galvant.ca).
#
# This file is a part of the InstrumentKit project.
# Licensed under the AGPL version 3.
##
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
##
##

## FEATURES ####################################################################

from __future__ import division

## IMPORTS #####################################################################

import time
import quantities as pq
import numpy as np
from itertools import izip
from axis_collection import AxisCollection
from instruments.util_fns import assume_units

## CLASSES #####################################################################

class PerpendicularAC(AxisCollection):
    """
    Joins two sets of `AxisCollection` into a perpindicular axes system. In a 
    raster, the minor axis is the one that scans rapidly. If you want more 
    than two perpindicular axes, simply nest instances of this class.
    
    Note that `scan` cannot in general be implemented more cleverly then just 
    calling a whole bunch of `move` commands, whereas `raster` can be 
    implemented with calls to `raster` on the minor axis and `move` on the 
    major axis.
    
    In all methods and properties, this combined axis system places the major 
    axis first, and the minor axis second. For example, if the major axes has
    two axes, and the minor axes has one axis, then move((1,2,3)) will send 
    the major axis to (1,2) and the minor axis to (3).
    
    :param AxisCollection major_axes: The axis that scans slowly in a raster.
    :param AxisCollection minor_axes: The axis that scans quickly in a raster.
    """

    def __init__(self, major_axes, minor_axes):
        
        super(PerpendicularAC, self).__init__()
                                
        self._major_axes = major_axes
        self._minor_axes = minor_axes
        
        self._n_major_axes = len(major_axes)
        self._n_minor_axes = len(minor_axes)
        
    ## PROPERTIES ##
    
    @property
    def finest_axes(self):
        self._minor_axes    
    
    @property
    def is_hardware_scannable(self):
        return self._major_axes.is_hardware_scannable + self._minor_axes.is_hardware_scannable
            
    @property
    def limits(self):
        return self._major_axes.limits + self._minor_axes.limits
        
    @property
    def position(self):
        return self._major_axes.position + self._minor_axes.position
        
    @property
    def units(self):
        return self._major_axes.units + self._minor_axes.units
            
    ## METHODS ##
    
    def _move(self, position, absolute=True):
        # separate the positions into the major and minor positions
        major_pos = position[:self._n_major_axes]
        minor_pos = position[self._n_major_axes:]
        self._major_axes.move(major_pos, absolute=absolute)
        self._minor_axes.move(minor_pos, absolute=absolute)
    
    def _scan(self, coords, dwell_time=None):
        # Unfortunately, can't do this more efficiently in general
        self.on_scan_start((coords, dwell_time))
        
        for coord in izip(*coords):
            # Call _move so we don't bloat the move history
            self._move(coord)
            self.on_scan_step(((coord, ), dwell_time))
                
        self.on_scan_complete((coords, dwell_time))
    
    def _raster(self, start, stop, num, dwell_time=None, strict=True):
        
        # Separate the major from the minor arguments...
        major_start = start[:self._n_major_axes ]
        major_stop = stop[:self._n_major_axes]
        major_num = num[:self._n_major_axes]
        
        minor_start = start[self._n_major_axes:]
        minor_stop = stop[self._n_major_axes:]
        minor_num = num[self._n_major_axes:]
        
        # Start by discretizing along each major axis.
        major_axis_steps = [
            np.linspace(
                assume_units(m_start, unit),
                assume_units(m_stop, unit),
                num = m_num
            )
            for m_start, m_stop, m_num, unit in izip(major_start, major_stop, major_num, self._major_axes.units)
        ]

        # Now call meshgrid and flatten to make a list of coordinates
        # This will make a typewriter-like raster
        major_axes_grid = np.array(np.meshgrid(*major_axis_steps)).transpose()
        major_axes_grid = major_axes_grid.reshape((np.prod(major_num), self._n_major_axes))
        
        # Loop through the major axis coordinates and raster the minor axis.
        for coord in major_axes_grid:
            self._major_axis.move(coord)
            self._minor_axis.raster(minor_start, minor_stop, minor_num, dwell_time=dwell_time)
        
        
    def __repr__(self):
        return 'Perpindicular({}, {})'.format(self._major_axes.__repr__(), self._minor_axes.__repr__())
        
    def __len__(self):
        return self._n_major_axes + self._n_minor_axes