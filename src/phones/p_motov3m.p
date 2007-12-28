### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to Motorola V3m phones"""

from prototypes import *
from prototypes_moto import *
from p_etsi import *
from p_moto import *
from p_motov710 import *

import fnmatch

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

PB_TOTAL_ENTRIES=1000
PB_RANGE=xrange(1,PB_TOTAL_ENTRIES+1)

_WP_EXCLUSION=frozenset(['*.ran', 'customer_opening.gif',
                         'customer_closing.gif'])
_RT_EXCLUSION=frozenset(['*.mp_'])

def valid_wp_filename(filename):
    global _WP_EXCLUSION
    for _name in _WP_EXCLUSION:
        if fnmatch.fnmatch(filename, _name):
            return False
    return True

def valid_rt_filename(filename):
    global _RT_EXCLUSION
    for _name in _RT_EXCLUSION:
        if fnmatch.fnmatch(filename, _name):
            return False
    return True

%}
