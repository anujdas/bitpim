#!/usr/bin/env python

### BITPIM
###
### Copyright (C) 2009 Nathan Hjelm <hjelmn@users.sourceforge.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
###



"""
Communicate with the LG VX11000 cell phone.
"""

# BitPim modules
import common
import com_brew
import prototypes
import com_lgvx9700
import p_lgvx11000
import helpids
import sms
import field_color
import phonenumber
import wx
import database

DEBUG1=False

#-------------------------------------------------------------------------------
parentphone=com_lgvx9700.Phone
class Phone(parentphone):
    desc="LG-VX11000 (enV Touch)"
    helpid=helpids.ID_PHONE_LGVX11000
    protocolclass=p_lgvx11000
    serialsname='lgvx11000'

    my_model='VX11000'
    builtinringtones= ('Low Beep Once', 'Low Beeps', 'Loud Beep Once', 'Loud Beeps', 'Door Bell',
                       'VZW Default Tone', 'Basic Ring', 'Telephone Ring', 'Soft Ring', 'Simple Beep',
                       'Galaxy Beep', 'Bellution', 'Good Morning', 'Rodeo Clown', 'Voice Of The Nature',
                       'Latin Fever', 'Allure', 'Surf The Groove', 'Ride A Tiger', 'This Time',
                       'Deep Blue Calling', 'Fairy Palaces', 'Central Park', 'Balmy Climate', 'Spring Legend',
                       'East of Rain', 'No Ring',)

    ringtonelocations= (
        # type           index file             default dir                 external dir  max  type   index
        ('ringers',     'dload/myringtone.dat','brew/mod/10889/ringtones', '',            100, 0x01,  100),
        ( 'sounds',     'dload/mysound.dat',   'brew/mod/18067',           '',            100, 0x02,  None),
        ( 'sounds(sd)', 'dload/sd_sound.dat',  'mmc1/my_sounds',           '',            100, 0x02,  None),
        ( 'music',      'dload/efs_music.dat', 'my_music',                 '',            100, 0x104, None),
        ( 'music(sd)',  'dload/sd_music.dat',  'mmc1/my_music',            '',            100, 0x14,  None),
        )

    #add picture ids to list of wallpapers, seems to be new for this phone
    wallpaperlocations= (
        #  type          index file                           default dir         external dir  max  type Index
        ( 'images',     'dload/image.dat',                    'brew/mod/10888',    '',          100, 0x00, 100),
        ( 'images(sd)', 'dload/sd_image.dat',                 'mmc1/my_pix',       '',          100, 0x10, None),
        ( 'video',      'dload/video.dat',                    'brew/mod/10890',    '',          100, 0x03, None),
        ( 'video(sd)',  'dload/sd_video.dat',                 'mmc1/my_flix',      '',          100, 0x13, None),
        ( 'picture ids','set_as_pic_id_dir/setas_pic_id.dat', 'set_as_pic_id_dir', '',          999, 0x00, None),
        )
    
    def setDMversion(self):
        self._DMv5=False
        self._DMv6=True
        self._timeout=5 # Assume a quick timeout on newer phones
        
    def getphoneinfo(self, phone_info):
        self.log('Getting Phone Info')
        try:
            s=self.getfilecontents('brew/version.txt')
            if s[:7]==self.my_model:
                phone_info.append('Manufacturer:', Profile.phone_manufacturer)
                phone_info.append('Model:', self.my_model)
                phone_info.append('Name:', self.desc[12:21])
                phone_info.append('ESN:', self.get_brew_esn())
                phone_info.append('Firmware Version:', self.get_firmware_version())
                #get the phone number from 'My Name Card'
                namecard=self.getfilecontents2('pim/pbmyentry.dat', 208, 10)
                phone_info.append('Phone Number:', phonenumber.format(namecard))
        except Exception, e:
            pass
        return

    # Fundamentals:
    #  - get_esn             - same as LG VX-8300
    #  - getgroups           - new implementation here due to group picture ids and no 'No Group' on this phone
    #  - getwallpaperindices - LGUncountedIndexedMedia
    #  - getringtoneindices  - LGUncountedIndexedMedia
    #  - DM Version          - 6
    #  - phonebook           - same as LG VX-8550, with some slight differences with picture ids, speed dials
    #  - SMS                 - same dir structure as the VX-8800

    def getgroups(self, results):
        "Read groups"
        # Reads groups that use explicit IDs
        self.log("Reading group information")
        g=self.readobject(self.protocolclass.pb_group_filename,
                          self.protocolclass.pbgroups,
                          'Reading groups data')
        
        self.log("Reading Group Picture IDs")
        group_picid_pathf=self._get_group_path_index(self.protocolclass.GroupWPPathIndexFile)
        _groupwp_ids=self._build_media_dict(results, group_picid_pathf, 'wallpaper-index')
        
        groups={}
        for i in range(len(g.groups)):
            _group = g.groups[i]
            if _group.name:
                try:
                    if _group.wallpaper == 0x64:
                        #indexes between _groupwp_ids and g.groups correspond to each other
                        #the group id does not match up to anything for group picture id purposes 
                        paper = _groupwp_ids.get(group_picid_pathf.items[i].pathname, None)
                    else:
                        paper = self.protocolclass.NOWALLPAPER
                        
                    if paper is None:
                        raise
                
                    groups[_group.groupid]= { 'name': _group.name, 'user_added': _group.user_added,
                                              'wallpaper': paper } #groups can have wallpaper on this phone
                except:
                    self.log("can't find wallpaper for group index: " + str(_group.groupid) + ": " + str(_group.name))

        results['groups'] = groups
        return groups

    def savegroups(self, data):
        groups=data.get('groups', {})
        keys=groups.keys()
        keys.sort()
        keys.reverse() 
        g=self.protocolclass.pbgroups()
        
        wp_index=data.get('wallpaper-index', {})
        group_picid_pathf=self.protocolclass.GroupPicID_PathIndexFile()
        
        #Don't write the no group entry, it doesn't exist on this phone!
        for i in keys:
            if not i:
                continue #already wrote this one out
            # now write the rest in reverse ID order
            group_entry = groups[i]
            new_entry = self.protocolclass.pbgroup(name=groups[i]['name'], groupid=i, user_added=groups[i].get('user_added', 1), wallpaper=0)
            for key in group_entry:
                if key == 'wallpaper':
                    if group_entry['wallpaper']==self.protocolclass.NOWALLPAPER:
                        new_entry.wallpaper = self._findmediainindex(data['wallpaper-index'], None, group_entry['name'], 'wallpaper')
                    else:
                        new_entry.wallpaper = self._findmediainindex(data['wallpaper-index'], group_entry['wallpaper'], group_entry['name'], 'wallpaper')
                    try:
                        _filename = wp_index[new_entry.wallpaper]['filename']
                        group_picid_pathf.items.append(self.protocolclass.GroupPicID_PathIndexEntry(pathname=_filename))
                        new_entry.wallpaper = 0x64
                    except:
                        group_picid_pathf.items.append(self.protocolclass.GroupPicID_PathIndexEntry())
            
            g.groups.append(new_entry)
        
        #write group picture ids
        self.log("Writing group picture ID")
        self.writeobject(self.protocolclass.GroupWPPathIndexFile, 
                         group_picid_pathf, logtitle='Writing group wallpaper paths',
                         uselocalfs=DEBUG1)             
        #write groups
        self.writeobject(self.protocolclass.pb_group_filename, g,
                         logtitle='Writing phonebook groups',
                         uselocalfs=DEBUG1)

    def _build_favorites_dict(self):
        if hasattr(self.protocolclass, 'favorites'):
            self.log("Reading favorites")
           # Return an favorites dict for building phone entries
            _res={}
            _favorites=self.readobject(self.protocolclass.favorites_file_name,
                                       self.protocolclass.favorites,
                                       logtitle='Reading favorites')
            for _idx,_entry in enumerate(_favorites.items):
                if _entry.has_pbentry ():
                    _res[_entry.pb_index]=_idx
            return _res
        else:
            return None
        
    def _get_group_path_index(self, index_file):
        buf = prototypes.buffer(self.getfilecontents(index_file))
        _path_file=self.protocolclass.GroupPicID_PathIndexFile();
        _path_file.readfrombuffer(buf, logtitle="Read group wallpaper path index: " + index_file)
        return _path_file        

    def getphonebook (self, result):
        """Reads the phonebook data.  The L{getfundamentals} information will
        already be in result."""
        # Read speed dials first -- same file format as the VX-8100
        _speeds=self._get_speeddials()

        # Read the emergency contacts list
        self.log("Reading ICE entries")
        _ices=self._build_ice_dict()

        # Read favorites (if available)
        _favorites=self._build_favorites_dict ()

        self.log("Reading phonebook entries")
        pb_entries=self.readobject(self.protocolclass.pb_file_name,
                                   self.protocolclass.pbfile,
                                   logtitle='Reading phonebook entries')

        self.log("Reading phone numbers")
        pb_numbers=self.readobject(self.protocolclass.pn_file_name,
                                   self.protocolclass.pnfile,
                                   logtitle='Reading phonebook numbers')

        #handle errors people are having when pa_file doesn't exist
        try:
            # check for addresses support
            if hasattr(self.protocolclass, 'pafile'):
                self.log("Reading addresses")
                pb_addresses = self.readobject(self.protocolclass.pa_file_name,
                                               self.protocolclass.pafile,
                                               logtitle='Reading addresses')
            else:
                pb_addresses = None
        except:
            pb_addresses = None

        self.log("Reading Ringtone IDs")
        ring_pathf=self._get_path_index(self.protocolclass.RTPathIndexFile)
        _rt_ids=self._build_media_dict(result, ring_pathf, 'ringtone-index')

        self.log("Reading Picture IDs")
        picid_pathf=self._get_path_index(self.protocolclass.WPPathIndexFile)
        _wp_ids=self._build_media_dict(result, picid_pathf, 'wallpaper-index')

        pbook={}
        for _cnt in range(self.protocolclass.NUMPHONEBOOKENTRIES):
            pb_entry=pb_entries.items[_cnt]
            if not pb_entry.valid():
                continue
            try:
                self.log("Parse entry "+`_cnt`+" - " + pb_entry.name)
                pbook[_cnt]=self.extractphonebookentry(pb_entry, pb_numbers, pb_addresses,
                                                       _speeds, _ices, _favorites, result,
                                                       _rt_ids.get(ring_pathf.items[_cnt].pathname, None),
                                                       _wp_ids.get(picid_pathf.items[_cnt].pathname, None))

                self.progress(_cnt, self.protocolclass.NUMPHONEBOOKENTRIES, pb_entry.name)
            except common.PhoneBookBusyException:
                raise
            except Exception, e:
                # Something's wrong with this entry, log it and skip
                self.log('Failed to parse entry %d'%_cnt)
                self.log('Exception %s raised'%`e`)
                if __debug__:
                    raise
            
        self.progress(self.protocolclass.NUMPHONEBOOKENTRIES,
                      self.protocolclass.NUMPHONEBOOKENTRIES,
                      "Phone book read completed")

        result['phonebook']=pbook
        #add a simple list of categories to result dict
        cats=[]
        for i in result['groups']:
            if result['groups'][i]['name']!='No Group':
                cats.append(result['groups'][i]['name'])
        result['categories']=cats
        #add a simple list of categories with their wallpapers to result dict
        group_wps=[]
        for i in result['groups']:
            groupinfo=result['groups'][i]
            name=str(groupinfo.get('name'))
            wp_name=str(groupinfo.get('wallpaper'))
            group_wps.append(name+":"+wp_name)
        result['group_wallpapers']=group_wps
        return pbook

    def extractphonebookentry(self, entry, numbers, addresses, speeds, ices, favorites, fundamentals,
                              rt_name, wp_name):
        """Return a phonebook entry in BitPim format.  This is called from getphonebook."""
        res={}
        # serials
        res['serials']=[ {'sourcetype': self.serialsname,
                          'sourceuniqueid': fundamentals['uniqueserial'],
                          'serial1': entry.entry_number1,
                          'serial2': entry.entry_number1 } ] 

        # only one name
        res['names']=[ {'full': entry.name} ]

        # only one category
        cat=fundamentals['groups'].get(entry.group, {'name': "No Group"})['name']
        if cat!="No Group":
            res['categories']=[ {'category': cat} ]

        # emails
        res['emails']=[]
        for i in entry.emails:
            if len(i.email):
                res['emails'].append( {'email': i.email} )
        if not len(res['emails']): del res['emails'] # it was empty

        # wallpapers
        if entry.wallpaper!=self.protocolclass.NOWALLPAPER:
            try:
                if entry.wallpaper == 0x64:
                    paper = wp_name
                else:
                    paper = fundamentals['wallpaper-index'][entry.wallpaper]['name']

                if paper is None:
                    raise

                res['wallpapers']=[ {'wallpaper': paper, 'use': 'call'} ]                
            except:
                self.log("can't find wallpaper for index: " + str(entry.wallpaper))
            
        # ringtones
        if entry.ringtone != self.protocolclass.NORINGTONE:
            try:
                if entry.ringtone == 0x64:
                    tone = rt_name
                else:
                    tone = fundamentals['ringtone-index'][entry.ringtone]['name']

                if tone is None:
                    raise

                res['ringtones']=[ {'ringtone': tone, 'use': 'call'} ]
            except:
                self.log("can't find ringtone for index: " + str(entry.ringtone))

        if addresses is not None and entry.addressindex != 0xffff:
            for _address in addresses.items:
                if _address.valid() and _address.index == entry.addressindex:
                    res['addresses'] = [ { 'street': _address.street,
                                           'city': _address.city,
                                           'state': _address.state,
                                           'postalcode': _address.zip_code,
                                           'country': _address.country }]
                    break

        # assume we are like the VX-8100 in this regard -- looks correct
        res=self._assignpbtypeandspeeddialsbytype(entry, numbers, speeds, res)
        
        # assign the ICE entry to the associated contact to keep them in sync
        res=self._assigniceentry(entry, numbers, ices, res)

        # adding the favorite entry
        res=self._assignfavoriteentry(entry, favorites, res)
  
        return res

    def _assignfavoriteentry(self, entry, favorites, res):
        if favorites.has_key(entry.entry_number0):
            # this contact entry is an favorite entry
            res['favorite']=[ { 'favoriteindex': favorites[entry.entry_number0] } ]
        return res

    def savephonebook (self, data):
        "Saves out the phonebook"
        
        #take the simple list of categories with their wallpapers and add it to result dict
        new_group_dict={}
        group_wps=data.get('group_wallpapers', {})
        for i in range(len(group_wps)):
            groupwp_entry=group_wps[i]
            entry_list=groupwp_entry.split(":", 1) #split on colon a maximum of once
            name=entry_list[0]
            wp=entry_list[1]
            for key in data['groups']:
                group_entry=data['groups'][key]
                if name==group_entry.get('name'):
                    group_entry['wallpaper']=wp
                    new_group_dict[key]=group_entry
        data['groups']=new_group_dict
        self.savegroups (data)

        ring_pathf=self.protocolclass.PathIndexFile()
        picid_pathf=self.protocolclass.PathIndexFile()

        # the pbentry.dat will be overwritten so there is no need to delete entries
        pbook = data.get('phonebook', {})
        keys = pbook.keys ()
        keys.sort ()

        _rt_index=data.get('ringtone-index', {})
        _wp_index=data.get('wallpaper-index', {})

        entry_num0 = 0
        entry_num1 = self._get_next_pb_id()
        pb_entries = self.protocolclass.pbfile(model_name=self.my_model)
        pn_entries = self.protocolclass.pnfile()

        # some phones store addresses as well
        if hasattr(self.protocolclass, 'pafile'):
            pa_entries = self.protocolclass.pafile()
        else:
            pa_entries = None

        ice_entries = self.protocolclass.iceentryfile()
        for i in range(self.protocolclass.NUMEMERGENCYCONTACTS):
            ice_entries.items.append (self.protocolclass.iceentry())

        speeddials={}

        # favorites can be groups or contacts. read favorites to preserve group favorites
        if hasattr (self.protocolclass, 'favorites'):
            favorites = self.readobject(self.protocolclass.favorites_file_name,
                                      self.protocolclass.favorites,
                                      logtitle='Reading favorites')
            for _entry in favorites.items:
                # all phonebook favorite will be invalid after writing the phonebook
                # (except for entries we set) so delete all phonebook favorites
                if _entry.fav_type == 1:
                    _entry.fav_type = 0xff
                    _entry.pb_index = 0xffff
        else:
            favorites = None

        for i in keys:
            pb_entries.items.append(self.make_entry (pn_entries, pa_entries, favorites, speeddials,
                                                     ice_entries, entry_num0, entry_num1, pbook[i],
                                                     data, ring_pathf,_rt_index, picid_pathf, _wp_index))
            entry_num0 += 1
            if entry_num0 >= self.protocolclass.NUMPHONEBOOKENTRIES:
                self.log ("Maximum number of phonebook entries reached")
                break
            if entry_num1==0xffffffff:
                entry_num1=0
            else:
                entry_num1+=1

        # write phonebook entries
        self.log ("Writing phonebook entries")
        self.writeobject(self.protocolclass.pb_file_name,
                         pb_entries,
                         logtitle='Writing phonebook entries',
                         uselocalfs=DEBUG1)
        # write phone numbers
        self.log ("Writing phone numbers")
        self.writeobject(self.protocolclass.pn_file_name,
                         pn_entries, logtitle='Writing phonebook numbers',
                         uselocalfs=DEBUG1)

        if pa_entries is not None:
            # write addresses
            self.log ("Writing addresses")
            self.writeobject(self.protocolclass.pa_file_name,
                             pa_entries, logtitle="Writing addresses",
                             uselocalfs=DEBUG1)

        # write ringtone index
        self.log('Writing ringtone ID')
        self.writeobject(self.protocolclass.RTPathIndexFile,
                         ring_pathf, logtitle='Writing ringtone paths',
                         uselocalfs=DEBUG1)
        # write wallpaper index
        self.log('Writing picture ID')
        self.writeobject(self.protocolclass.WPPathIndexFile,
                         picid_pathf, logtitle='Writing wallpaper paths',
                         uselocalfs=DEBUG1)

        # write ICE index
        self.log('Writing ICE entries')
        self.writeobject(self.protocolclass.ice_file_name,
                         ice_entries, logtitle='Writing ICE entries',
                         uselocalfs=DEBUG1)

        # update speed dials
        req=self.protocolclass.speeddials()
        # slot 0 is always unused
        req.speeddials.append(self.protocolclass.speeddial())
        # if empty, slot 1 is for voicemail
        if speeddials.has_key(1):
            answer = wx.MessageBox("You have assigned speed dial #1 in your PhoneBook.\nAre you sure you want to overwrite the 'Voicemail' speed dial?", "Caution overwriting speed dial", wx.YES_NO|wx.ICON_EXCLAMATION|wx.STAY_ON_TOP)
            if answer == wx.YES:
                req.speeddials.append(self.protocolclass.speeddial(entry=speeddials[1]['entry'],number=speeddials[1]['type']))
            else:
                req.speeddials.append(self.protocolclass.speeddial(entry=1000,number=6))                
        else:
            req.speeddials.append(self.protocolclass.speeddial(entry=1000,number=6))
            
        for i in range(2, self.protocolclass.NUMSPEEDDIALS):
            sd=self.protocolclass.speeddial()
            if speeddials.has_key(i):
                if i==411:
                    answer = wx.MessageBox("You have assigned speed dial #411 in your PhoneBook.\nAre you sure you want to overwrite the 'Directory Assistance' speed dial?", "Caution overwriting speed dial", wx.YES_NO|wx.ICON_EXCLAMATION|wx.STAY_ON_TOP)
                    if answer == wx.YES:
                        sd.entry=speeddials[i]['entry']
                        sd.number=speeddials[i]['type']
                    else:
                        req.speeddials.append(sd)
                        continue #they dont want to assign 411 so skip to next iteration                     
                sd.entry=speeddials[i]['entry']
                sd.number=speeddials[i]['type']
            req.speeddials.append(sd)

        self.log('Writing speed dials')
        self.writeobject(self.protocolclass.speed_file_name,
                         req, logtitle='Writing speed dials data',
                         uselocalfs=DEBUG1)

        if favorites is not None:
            self.log('Writing favorites')
            self.writeobject(self.protocolclass.favorites_file_name,
                             favorites, logtitle='Writing favorites',
                             uselocalfs=DEBUG1)

        # update the next pbentries ID
        self._save_next_pb_id(entry_num1)
        data["rebootphone"]=True

        return data

    def make_pa_entry (self, pb_entry, address_index, address):
        new_entry = self.protocolclass.pafileentry(entry_tag=self.protocolclass.PA_ENTRY_SOR)
        new_entry.index = address_index
        new_entry.pb_entry = pb_entry
        new_entry.street   = address['street']
        new_entry.city     = address['city']
        new_entry.state    = address['state']
        new_entry.zip_code = address['postalcode']
        new_entry.country  = address['country']

        return new_entry
        
    def make_entry (self, pn_entries, pa_entries, favorites, speeddials, ice_entries,
                    entry_num0, entry_num1, pb_entry, data,
                    ring_pathf, rt_index, picid_pathf, wp_index):
        """ Create a pbfileentry from a bitpim phonebook entry """
        new_entry = self.protocolclass.pbfileentry(entry_tag=self.protocolclass.PB_ENTRY_SOR)
        # entry IDs
        new_entry.entry_number0 = entry_num0
        new_entry.entry_number1 = entry_num1

        for key in pb_entry:
            if key in ('emails', 'numbertypes'):
                l = getattr (new_entry, key)
                for item in pb_entry[key]:
                    l.append(item)
            elif key == 'numbers':
                l = getattr (new_entry, 'numberindices')
                for i in range(0, self.protocolclass.NUMPHONENUMBERS):
                    new_pn_id = len (pn_entries.items)
                    if new_pn_id == self.protocolclass.NUMPHONENUMBERENTRIES:
                        # this state should not be possible. should this raise an exception?
                        self.log ("Maximum number of phone numbers reached")
                        break

                    try:
                        pn_entries.items.append(self.make_pn_entry (pb_entry[key][i],pb_entry['numbertypes'][i], new_pn_id, i, entry_num0))
                        l.append (new_pn_id)
                    except:
                        l.append (0xffff)
            elif key == 'speeddials':
                for _sd,_num_type in zip(pb_entry['speeddials'], pb_entry['numbertypes']):
                    if _sd is not None:
                        speeddials[_sd]={ 'entry': entry_num0,
                                          'type': _num_type }
            elif key == 'ice':
                # In Case of Emergency
                _ice = pb_entry['ice']
                if _ice is not None and len(_ice) > 0:
                    _ice_entry = _ice[0]['iceindex']
                    ice_entries.items[_ice_entry] = self.make_ice_entry (_ice_entry, entry_num0)
            elif key == 'favorite':
                _favorite = pb_entry['favorite']
                if favorites is not None and _favorite is not None and len(_favorite) > 0:
                    favorites.items[_favorite[0]['favoriteindex']].fav_type = 1 # phone number
                    favorites.items[_favorite[0]['favoriteindex']].pb_index = entry_num0 # phone number
            elif key == 'addresses':
                _addresses = pb_entry['addresses']
                address_id = len (pa_entries.items)
                if pa_entries is not None and _addresses is not None and len(_addresses) > 0:
                    new_entry.addressindex = address_id
                    pa_entries.items.append(self.make_pa_entry (entry_num0, address_id, _addresses[0]))
            elif key == 'ringtone':
                new_entry.ringtone = self._findmediainindex(data['ringtone-index'], pb_entry['ringtone'], pb_entry['name'], 'ringtone')
                try:
                    _filename = rt_index[new_entry.ringtone]['filename']
                    ring_pathf.items.append(self.protocolclass.PathIndexEntry(pathname=_filename))
                    new_entry.ringtone = 0x64
                except:
                    ring_pathf.items.append(self.protocolclass.PathIndexEntry())
            elif key == 'wallpaper':
                new_entry.wallpaper = self._findmediainindex(data['wallpaper-index'], pb_entry['wallpaper'], pb_entry['name'], 'wallpaper')
                try:
                    _filename = wp_index[new_entry.wallpaper]['filename']
                    picid_pathf.items.append(self.protocolclass.PathIndexEntry(pathname=_filename))
                    new_entry.wallpaper = 0x64
                except:
                    picid_pathf.items.append(self.protocolclass.PathIndexEntry())
            elif key in new_entry.getfields():
                setattr (new_entry, key, pb_entry[key])

        return new_entry

#-------------------------------------------------------------------------------
parentprofile=com_lgvx9700.Profile
class Profile(parentprofile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname

    BP_Calendar_Version=3
    phone_manufacturer='LG Electronics Inc'
    phone_model='VX11000'
    # inside screen resolution
    WALLPAPER_WIDTH  = 800
    WALLPAPER_HEIGHT = 480
    
    ringtoneorigins=('ringers', 'sounds', 'sounds(sd)',' music', 'music(sd)')
    excluded_ringtone_origins=('music', 'music(sd)')  
    
    # wallpaper origins that are not available for the contact assignment
    excluded_wallpaper_origins=('video','video(sd)')  
   
    imageorigins={}
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "video"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images(sd)"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "video(sd)"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "picture ids"))

    # our targets are the same for all origins
    imagetargets={}
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "outsidelcd",
                                      {'width': 480, 'height': 800, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "wallpaper",
                                      {'width': 800, 'height': 480, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "pictureid",
                                      {'width': 320, 'height': 240, 'format': "JPEG"}))

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        ('calendar', 'read', None),   # all calendar reading
        ('wallpaper', 'read', None),  # all wallpaper reading
        ('ringtone', 'read', None),   # all ringtone reading
        ('call_history', 'read', None),# all call history list reading
        ('sms', 'read', None),         # all SMS list reading
        ('memo', 'read', None),        # all memo list reading
##        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('wallpaper', 'write', 'MERGE'),      # merge and overwrite wallpaper
        ('wallpaper', 'write', 'OVERWRITE'),
        ('ringtone', 'write', 'MERGE'),      # merge and overwrite ringtone
        ('ringtone', 'write', 'OVERWRITE'),
        ('sms', 'write', 'OVERWRITE'),        # all SMS list writing
        ('memo', 'write', 'OVERWRITE'),       # all memo list writing
##        ('playlist', 'read', 'OVERWRITE'),
##        ('playlist', 'write', 'OVERWRITE'),
##        ('t9_udb', 'write', 'OVERWRITE'),
        )
    if __debug__:
        _supportedsyncs+=(
        ('t9_udb', 'read', 'OVERWRITE'),
        ('t9_udb', 'write', 'OVERWRITE'),
        ('playlist', 'read', None),
        ('playlist', 'write', 'OVERWRITE'),
        ('playlist', 'write', 'MERGE'),
        )
        
    field_color_data={
    'phonebook': {
        'name': {
            'first': False, 'middle': False, 'last': False, 'full': 1,
            'nickname': False, 'details': 1 },
        'number': {
            'type': 5, 'speeddial': 5, 'number': 5,
            'ringtone': False, 'wallpaper': False, 'details': 5 },
        'email': 2,
        'email_details': {
            'emailspeeddial': False, 'emailringtone': False,
            'emailwallpaper': False },
        'address': {
            'type': False, 'company': False, 'street': 1, 'street2': False,
            'city': 1, 'state': 1, 'postalcode': 1, 'country': 1, 'details': 1 },
        'url': 0,
        'memo': 0,
        'category': 1,
        'wallpaper': 1,
        'group_wallpaper': 1,
        #'wallpaper_type': False,
        'ringtone': 1,
        'storage': False,
        'secret': False,
        'ICE': 1,
        'Favorite': 1,
        },
    'calendar': {
        'description': True, 'location': False, 'allday': False,
        'start': True, 'end': True, 'priority': False,
        'alarm': True, 'vibrate': True,
        'repeat': True,
        'memo': False,
        'category': False,
        'wallpaper': False,
        'ringtone': True,
        },
    'memo': {
        'subject': False,
        'date': True,
        'secret': False,
        'category': False,
        'memo': True,
        },
    'todo': {
        'summary': False,
        'status': False,
        'due_date': False,
        'percent_complete': False,
        'completion_date': False,
        'private': False,
        'priority': False,
        'category': False,
        'memo': False,
        },
    }        


    def convertphonebooktophone(self, helper, data):
        """Converts the data to what will be used by the phone

        @param data: contains the dict returned by getfundamentals
                     as well as where the results go"""
        results={}

        self.normalisegroups(helper, data)

        for pbentry in data['phonebook']:
            if len(results)==self.protocolclass.NUMPHONEBOOKENTRIES:
                break
            e={} # entry out
            entry=data['phonebook'][pbentry] # entry in
            try:
                # serials
                serial1=helper.getserial(entry.get('serials', []), self.serialsname, data['uniqueserial'], 'serial1', 0)
                serial2=helper.getserial(entry.get('serials', []), self.serialsname, data['uniqueserial'], 'serial2', serial1)

                e['serial1']=serial1
                e['serial2']=serial2
                for ss in entry["serials"]:
                    if ss["sourcetype"]=="bitpim":
                        e['bitpimserial']=ss
                assert e['bitpimserial']

                # name
                e['name']=helper.getfullname(entry.get('names', []),1,1,32)[0]

                # ice
                e['ice']=entry.get('ice', None)

                # favorites
                e['favorite']=entry.get('favorite', None)

                # address
                e['addresses']=entry.get('addresses', None)

                # categories/groups
                cat=helper.makeone(helper.getcategory(entry.get('categories', []),0,1,32), None)
                if cat is None:
                    e['group']=0
                else:
                    key,value=self._getgroup(cat, data['groups'])
                    if key is not None:
                        e['group']=key
                    else:
                        # sorry no space for this category
                        e['group']=0

                # email addresses
                emails=helper.getemails(entry.get('emails', []) ,0,self.protocolclass.NUMEMAILS,48)
                e['emails']=helper.filllist(emails, self.protocolclass.NUMEMAILS, "")

                # phone numbers
                # there must be at least one email address or phonenumber
                minnumbers=1
                if len(emails): minnumbers=0
                numbers=helper.getnumbers(entry.get('numbers', []),minnumbers,self.protocolclass.NUMPHONENUMBERS)
                e['numbertypes']=[]
                e['numbers']=[]
                e['speeddials']=[]
                for numindex in range(len(numbers)):
                    num=numbers[numindex]
                    # deal with type
                    b4=len(e['numbertypes'])
                    type=num['type']
                    for i,t in enumerate(self.protocolclass.numbertypetab):
                        if type==t:
                            # some voodoo to ensure the second home becomes home2
                            if i in e['numbertypes'] and t[-1]!='2':
                                type+='2'
                                continue
                            e['numbertypes'].append(i)
                            break
                        if t=='none': # conveniently last entry
                            e['numbertypes'].append(i)
                            break
                    if len(e['numbertypes'])==b4:
                        # we couldn't find a type for the number
                        helper.add_error_message('Number %s (%s/%s) not supported and ignored.'%
                                                 (num['number'], e['name'], num['type']))
                        continue 
                    # deal with number
                    number=self.phonize(num['number'])
                    if len(number)==0:
                        # no actual digits in the number
                        continue
                    if len(number) > 48: # get this number from somewhere sensible
                        # ::TODO:: number is too long and we have to either truncate it or ignore it?
                        number=number[:48] # truncate for moment
                    e['numbers'].append(number)
                    # deal with speed dial
                    sd=num.get("speeddial", None)
                    if sd is not None and \
                       sd>=self.protocolclass.FIRSTSPEEDDIAL and \
                       sd<=self.protocolclass.LASTSPEEDDIAL:
                        e['speeddials'].append(sd)
                    else:
                        e['speeddials'].append(None)

                if len(e['numbers'])<minnumbers:
                    # we couldn't find any numbers
                    # for this entry, so skip it, entries with no numbers cause error
                    helper.add_error_message("Name: %s. No suitable numbers or emails found" % e['name'])
                    continue 
                e['numbertypes']=helper.filllist(e['numbertypes'], self.protocolclass.NUMPHONENUMBERS, 0)
                e['numbers']=helper.filllist(e['numbers'], self.protocolclass.NUMPHONENUMBERS, "")
                e['speeddials']=helper.filllist(e['speeddials'], self.protocolclass.NUMPHONENUMBERS, None)

                # ringtones, wallpaper
                e['ringtone']=helper.getringtone(entry.get('ringtones', []), 'call', None)
                e['wallpaper']=helper.getwallpaper(entry.get('wallpapers', []), 'call', None)

                results[pbentry]=e
                
            except helper.ConversionFailed:
                continue

        data['phonebook']=results
        return data
