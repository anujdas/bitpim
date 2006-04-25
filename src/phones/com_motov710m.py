### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id: $

"""Communicate with Motorola phones using AT commands"""
# system modules
import time

# BitPim modules
import bp_obex
import com_motov710
import p_motov710

##import bpcalendar
##import common
##import com_brew
##import com_moto
##import fileinfo
##import nameparser
##import prototypes

parentphone=com_motov710.Phone
class Phone(parentphone):
    """ Talk to a Motorola V710 phone"""
    desc='Moto-V710m'
    protocolclass=p_motov710
    serialsname='motov710m'
    MODEOBEX='modeobex'

    def __init__(self, logtarget, commport):
        parentphone.__init__(self, logtarget, commport)
        self.obex=None

    # mode routines
    def _setmodeobex(self):
        self.setmode(self.MODEMODEM)
        self.log('Switching OBEX')
        _req=self.protocolclass.modeset()
        _req.mode=self.protocolclass.MODE_OBEX
        self.sendATcommand(_req, None)
        time.sleep(0.5)
        self.obex=bp_obex.FolderBrowsingService(self, self.comm)
        if self.obex.connect():
            return True
        del self.obex
        self.obex=None
        return False

    def _setmodeobextomodem(self):
        if self.obex:
            self.log('Switching from OBEX to modem')
            self.obex.disconnect()
            del self.obex
            self.obex=None
        return True

    # Ringtones stuff----------------------------------------------------------
    def _get_del_new_list(self, index_key, media_key, merge, fundamentals):
        """Return a list of media being deleted and being added"""
        _index=fundamentals.get(index_key, {})
        _media=fundamentals.get(media_key, {})
        _index_file_list=[_entry['name'] for _,_entry in _index.items() \
                          if _entry.has_key('filename')]
        _bp_file_list=[_entry['name'] for _,_entry in _media.items()]
        if merge:
            # just add the new files, don't delete anything
            _del_list=[]
            _new_list=_bp_file_list
        else:
            # Delete specified files and add everything
            _del_list=[x for x in _index_file_list if x not in _bp_file_list]
            _new_list=_bp_file_list
        return _del_list, _new_list

    def _del_files(self, index_key, media_path, _del_list, fundamentals):
        """Delete specified media files, need to be in OBEX mode"""
        _index=fundamentals.get(index_key, {})
        for _file in _del_list:
            _file_name=media_path+'/'+_file
            try:
                self.obex.rmfile(_file_name)
            except Exception, e:
                self.log('Failed to delete OBEX file %s: %s'%(_file_name, `e`))

    def _replace_files(self, index_key, media_key, new_list, fundamentals):
        """Replace existing files with new contents using BREW"""
        _index=fundamentals.get(index_key, {})
        _media=fundamentals.get(media_key, {})
        for _file in new_list:
            _data=self._item_from_index(_file, 'data', _media)
            if not _data:
                self.log('Failed to write file %s due to no data'%_file)
                continue
            _file_name=self._item_from_index(_file, 'filename', _index)
            if _file_name:
                # existing file, check if the same one
                _stat=self.statfile(_file_name)
                if _stat and _stat['size']!=len(_data):
                    # different size, replace it
                    try:
                        self.writefile(_file_name, _data)
                    except:
                        self.log('Failed to write BREW file '+_file_name)
                        if __debug__:
                            raise
        
    def _add_files(self, index_key, media_key, media_path,
                   new_list, fundamentals):
        """Add new file using OBEX"""
        _index=fundamentals.get(index_key, {})
        _media=fundamentals.get(media_key, {})
        for _file in new_list:
            _data=self._item_from_index(_file, 'data', _media)
            if not _data:
                self.log('Failed to write file %s due to no data'%_file)
                continue
            if self._item_from_index(_file, None, _index) is None:
                # new file
                _file_name=media_path+'/'+_file
                try:
                    self.obex.writefile(_file_name, _data)
                except:
                    self.log('Failed to write OBEX file '+_file_name)
                    if __debug__:
                        raise
        
    def saveringtones(self, fundamentals, merge):
        """Save ringtones to the phone"""
        self.log('Writing ringtones to the phone')
        self.setmode(self.MODEPHONEBOOK)
        self.setmode(self.MODEBREW)
        try:
            _del_list, _new_list=self._get_del_new_list('ringtone-index',
                                                        'ringtone',
                                                        merge,
                                                        fundamentals)
            # replace files, need to be in BREW mode
            self._replace_files('ringtone-index', 'ringtone',
                                _new_list, fundamentals)
            # delete files, need to be in OBEX mode
            self.setmode(self.MODEOBEX)
            self._del_files('ringtone-index', 'audio',
                            _del_list, fundamentals)
            # and add new files, need to be in OBEX mode
            self._add_files('ringtone-index', 'ringtone', 'audio',
                                    _new_list, fundamentals)
        except:
            if __debug__:
                self.setmode(self.MODEMODEM)
                raise
        self.setmode(self.MODEMODEM)
        return fundamentals

    def savewallpapers(self, fundamentals, merge):
        """Save wallpapers to the phone"""
        self.log('Writing ringtones to the phone')
        self.setmode(self.MODEPHONEBOOK)
        self.setmode(self.MODEBREW)
        try:
            _del_list, _new_list=self._get_del_new_list('wallpaper-index',
                                                        'wallpapers',
                                                        merge,
                                                        fundamentals)
            # replace files, need to be in BREW mode
            self._replace_files('wallpaper-index', 'wallpapers',
                                _new_list, fundamentals)
            # delete files, need to be in OBEX mode
            self.setmode(self.MODEOBEX)
            self._del_files('wallpaper-index', 'picture',
                            _del_list, fundamentals)
            # and add new files, need to be in OBEX mode
            self._add_files('wallpaper-index', 'wallpapers', 'picture',
                                    _new_list, fundamentals)
        except:
            if __debug__:
                self.setmode(self.MODEMODEM)
                raise
        self.setmode(self.MODEMODEM)
        return fundamentals

#------------------------------------------------------------------------------
parentprofile=com_motov710.Profile
class Profile(parentprofile):

    serialsname=Phone.serialsname
    phone_model='V710M'

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('calendar', 'read', None),   # all calendar reading
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('ringtone', 'read', None),   # all ringtone reading
        ('ringtone', 'write', None),
        ('ringtone', 'write', 'OVERWRITE'),
        ('wallpaper', 'read', None),  # all wallpaper reading
        ('wallpaper', 'write', None),
        ('wallpaper', 'write', 'OVERWRITE'),
        ('sms', 'read', None),
        )
