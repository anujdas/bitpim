### BITPIM
###
### Copyright (C) 2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to LG VX4500"""

from prototypes import *

# Make all lg stuff available in this module as well
from p_lg import *

# we are the same as lgvx4400 except as noted
# below
from p_lgvx4400 import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

%}

# desc file used for wallpaper and ringtone indices
PACKET mediadesc:
    4 UINT totalsize  "media file size with size of this file (156 bytes) added"
    4 UINT {'constant': 0} +dunno1
    4 UINT index      "index number"
    4 UINT {'default': 0x7824c97a} +magic1 "probably a date"
    4 UINT {'default': 0x7824c97a} +magic2 "probably a date"
    4 UINT {'default': 0x7824c97a} +magic3 "probably a date"
    4 UINT {'constant': 0} +dunno2
    32 STRING {'default': 'body'} filename
    32 STRING {'default': 'identity'} +whoknows
    32 STRING mimetype
    32 STRING {'default': ""} +whoknows2

# All STRINGS have raiseonterminatedread as False since the phone does
# occassionally leave out the terminator byte
# Note if you change the length of any of these fields, you also
# need to modify com_lgvx4600 to give a different truncateat parameter
# in the convertphonebooktophone method
PACKET pbentry:
    P  UINT {'constant': 3} numberofemails
    P  UINT {'constant': 5} numberofphonenumbers
    4  UINT serial1
    2  UINT {'constant': 0x0222} +entrysize
    4  UINT serial2
    2  UINT entrynumber 
    23 STRING {'raiseonunterminatedread': False} name
    2  UINT group
    *  LIST {'length': self.numberofemails} +emails:
        49 STRING {'raiseonunterminatedread': False} email
    49 STRING {'raiseonunterminatedread': False} url
    1  UINT ringtone                                     "ringtone index for a call"
    1  UINT msgringtone                                  "ringtone index for a text message"
    1  BOOL secret
    65 STRING {'raiseonunterminatedread': False} memo
    1  UINT wallpaper
    * LIST {'length': self.numberofphonenumbers} +numbertypes:
        1 UINT numbertype
    * LIST {'length': self.numberofphonenumbers} +numbers:
        49 STRING {'raiseonunterminatedread': False} number
    * UNKNOWN +unknown20c

PACKET pbreadentryresponse:
    "Results of reading one entry"
    *  pbheader header
    *  pbentry  entry

PACKET pbupdateentryrequest:
    * pbheader {'command': 0x04, 'flag': 0x01} +header
    * pbentry entry

PACKET pbappendentryrequest:
    * pbheader {'command': 0x03, 'flag': 0x01} +header
    * pbentry entry