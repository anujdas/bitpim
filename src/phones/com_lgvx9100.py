### BITPIM
###
### Copyright (C) 2008 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""
Communicate with the LG VX9100 (enV2) cell phone.  This is based on the enV model
"""

# BitPim modules
import common
import com_brew
import com_lg
import com_lgvx8550
import p_lgvx9100
import helpids

#-------------------------------------------------------------------------------
parentphone=com_lgvx8550.Phone
class Phone(parentphone):
    "Talk to the LG VX9100 cell phone"

    desc="LG-VX9100"
##    helpid=helpids.ID_PHONE_LGVX9900
    helpids=None
    protocolclass=p_lgvx9100
    serialsname='lgvx9100'
    my_model='VX9100'

    # rintones and wallpaper info, copy from VX9900, may need to change to match
    # what the phone actually has
    external_storage_root='mmc1/'
    builtinringtones= ('Low Beep Once', 'Low Beeps', 'Loud Beep Once', 'Loud Beeps', 'VZW Default Ringtone') + \
                      tuple(['Ringtone '+`n` for n in range(1,13)]) + \
                      ('No Ring',)

    ringtonelocations= (
        #  type          index file            default dir        external dir    max  type Index
        ( 'ringers',    'dload/myringtone.dat','brew/16452/lk/mr','mmc1/ringers', 100, 0x01, 100),
        ( 'sounds',     'dload/mysound.dat',   'brew/16452/ms',   '',             100, 0x02, None),
        ( 'sounds(sd)', 'dload/sd_sound.dat',  'mmc1/my_sounds',  '',             100, 0x02, None),
        ( 'music',      'dload/efs_music.dat', 'my_music',        '',             100, 0x104, None),
        ( 'music(sd)',  'dload/sd_music.dat',  'mmc1/my_music',   '',             100, 0x14, None),
        )

    wallpaperlocations= (
        #  type          index file            default dir     external dir  max  type Index
        ( 'images',     'dload/image.dat',    'brew/16452/mp', '',           100, 0x00, 100),
        ( 'images(sd)', 'dload/sd_image.dat', 'mmc1/my_pix',   '',           100, 0x10, None),
        ( 'video',      'dload/video.dat',    'brew/16452/mf', '',           100, 0x03, None),
        ( 'video(sd)',  'dload/sd_video.dat', 'mmc1/my_flix',  '',           100, 0x13, None),
        )

    def __init__(self, logtarget, commport):
        parentphone.__init__(self, logtarget, commport)

    def setDMversion(self):
        self._DMv6=True
        self._DMv5=False

    # Fundamentals:
    #  - get_esn             - same as LG VX-8300
    #  - getgroups           - same as LG VX-8100
    #  - getwallpaperindices - LGUncountedIndexedMedia
    #  - getrintoneindices   - LGUncountedIndexedMedia
    #  - DM Version          - T99VZV01: N/A, T99VZV02: 5
        
#-------------------------------------------------------------------------------
parentprofile=com_lgvx8550.Profile
class Profile(parentprofile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname

    BP_Calendar_Version=3
    phone_manufacturer='LG Electronics Inc'
    phone_model='VX9100'

    WALLPAPER_WIDTH=320
    WALLPAPER_HEIGHT=240
    # outside LCD: 160x64

    imageorigins={}
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "video"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images(sd)"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "video(sd)"))
    def GetImageOrigins(self):
        return self.imageorigins


    ringtoneorigins=('ringers', 'sounds', 'sounds(sd)',' music', 'music(sd)')
    excluded_ringtone_origins=('sounds', 'sounds(sd)', 'music', 'music(sd)')

    # our targets are the same for all origins
    imagetargets={}
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "wallpaper",
                                      {'width': 320, 'height': 240, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "outsidelcd",
                                      {'width': 160, 'height': 64, 'format': "JPEG"}))

    def GetTargetsForImageOrigin(self, origin):
        return self.imagetargets

    _supportedsyncs=(
##        ('phonebook', 'read', None),   # all phonebook reading
##        ('calendar', 'read', None),    # all calendar reading
##        ('wallpaper', 'read', None),   # all wallpaper reading
##        ('ringtone', 'read', None),    # all ringtone reading
##        ('call_history', 'read', None),# all call history list reading
##        ('sms', 'read', None),         # all SMS list reading
##        ('memo', 'read', None),        # all memo list reading
##        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
##        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
##        ('wallpaper', 'write', 'MERGE'),      # merge and overwrite wallpaper
##        ('wallpaper', 'write', 'OVERWRITE'),
##        ('ringtone', 'write', 'MERGE'),       # merge and overwrite ringtone
##        ('ringtone', 'write', 'OVERWRITE'),
####        ('sms', 'write', 'OVERWRITE'),        # all SMS list writing
##        ('memo', 'write', 'OVERWRITE'),       # all memo list writing
####        ('playlist', 'read', 'OVERWRITE'),
####        ('playlist', 'write', 'OVERWRITE'),
        )
