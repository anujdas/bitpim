### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
### Copyright (C) 2004 John O'Shaughnessy <oshinfo@comcast.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with the LG VX6100 cell phone

The VX6100 is substantially similar to the VX4400 except that it supports more
image formats, has wallpapers in no less than 5 locations and puts things in
slightly different directories.

The code in this file mainly inherits from VX4400 code and then extends where
the 6100 has extra functionality

"""

# standard modules
import time
import cStringIO
import sha

# my modules
import common
import copy
import p_lgvx6100
import com_lgvx4400
import com_brew
import com_phone
import com_lg
import prototypes

class Phone(com_lgvx4400.Phone):
    "Talk to the LG VX6100 cell phone"

    desc="LG-VX6100"

    protocolclass=p_lgvx6100
    serialsname='lgvx6100'

    # more VX6100 indices
    imagelocations=(
        # offset, index file, files location, type, maximumentries
        ( 50, "download/dloadindex/brewImageIndex.map", "brew/shared", "images", 30) ,
        ( 100, "download/dloadindex/mmsImageIndex.map", "brew/shared/mms", "mms", 20),
        ( 220, "download/dloadindex/mmsDrmImageIndex.map", "brew/shared/mms/d", "drm", 20), 
        ( 130, None, None, "camera", 20) # nb camera must be last
        )

    ringtonelocations=(
        # offset, index file, files location, type, maximumentries
        ( 50, "download/dloadindex/brewRingerIndex.map", "user/sound/ringer", "ringers", 30),
        ( 150, "download/dloadindex/mmsRingerIndex.map", "mms/sound", "mms", 20),
        ( 180, "download/dloadindex/mmsDrmRingerIndex.map", "mms/sound/drm", "drm", 20)
        )

    builtinimages= ('Sport', 'Butterfly', 'Cake', 'Niagara Falls', 'Rockefeller', 
    				'Statue of Liberty', 'The Capital', 'Scenary','White Bear', 'Yacht' ) 
    
    builtinringtones= ('Ring 1', 'Ring 2', 'Ring 3', 'Ring 4', 'Ring 5', 'VZW Default Tone',
                       'Farewell', 'Arabesque',
                       'Piano Sonata', 'Latin', 'When The Saints', 'Bach Cello Suite',
                       'Speedy Way', 'Cancan', 'Sting', 'Toccata and Fugue',
                       'Mozart Symphony 40', 'Nutcracker March', 'Funiculi', 'Polka', 	
                       'Hallelujah', 'Mozart Aria',
                       'Leichte', 'Spring', 'Slavonic', 'Fantasy', 'Chimes High',
                       'Chimes Low', 'Ding', 'Tada', 'Notify', 'Drum', 'Claps', 'Fanfare', 
                       'Chord High', 'Chord Low')
                       
    
    def __init__(self, logtarget, commport):
        com_lgvx4400.Phone.__init__(self,logtarget,commport)
        self.mode=self.MODENONE
        
    def makeentry(self, counter, entry, dict):
        e=com_lgvx4400.Phone.makeentry(self, counter, entry, dict)
        e.entrysize=0x202
        return e

    def getcameraindex(self):
        buf=prototypes.buffer(self.getfilecontents("cam/pics.dat"))
        index={}
        g=self.protocolclass.campicsdat()
        g.readfrombuffer(buf)
        for i in g.items:
            if len(i.name):
                # index[i.index]={'name': i.name, 'date': i.taken, 'origin': 'camera' }
                # we currently use the filesystem name rather than rename in camera
                # since the latter doesn't include the file extension which then makes
                # life less pleasant once the file ends up on the computer
                index[i.index]={'name': "pic%02d.jpg"%(i.index,), 'date': i.taken, 'origin': 'camera' }
        return index

class Profile(com_lgvx4400.Profile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname

    WALLPAPER_WIDTH=132
    WALLPAPER_HEIGHT=148
    MAX_WALLPAPER_BASENAME_LENGTH=36
    WALLPAPER_FILENAME_CHARS="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwyz0123456789 ."
    WALLPAPER_CONVERT_FORMAT="jpg"
   
    MAX_RINGTONE_BASENAME_LENGTH=36
    RINGTONE_FILENAME_CHARS="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwyz0123456789 ."
 
    def __init__(self):
        com_lgvx4400.Profile.__init__(self)