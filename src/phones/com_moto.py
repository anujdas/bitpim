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
import sha
import time

# BitPim modules
import commport
import com_brew
import com_gsm
import prototypes
import p_moto

class Phone(com_gsm.Phone, com_brew.BrewProtocol):
    """Talk to a generic Motorola phone.
    """
    desc='Motorola'
    protocolclass=p_moto
    _switch_mode_cmd='\x44\x58\xf4\x7e'
    MODEPHONEBOOK="modephonebook"

    def __init__(self, logtarget, commport):
        com_gsm.Phone.__init__(self, logtarget, commport)
        com_brew.BrewProtocol.__init__(self)
        self.mode=self.MODENONE

    # Common/Support routines
    def set_mode(self, mode):
        """Set the current phone mode"""
        _req=self.protocolclass.modeset()
        _req.mode=mode
        self.sendATcommand(_req, None)
        self.comm.sendatcommand('')
        
    def charset_ascii(self):
        """Set the charset to ASCII (default)"""
        _req=self.protocolclass.charset_set_req()
        _req.charset=self.protocolclass.CHARSET_ASCII
        self.sendATcommand(_req, None)
    def charset_ucs2(self):
        """Set the charset to UCS-2, used for most string values"""
        _req=self.protocolclass.charset_set_req()
        _req.charset=self.protocolclass.CHARSET_UCS2
        self.sendATcommand(_req, None)

    def select_phonebook(self, phonebook=None):
        _req=self.protocolclass.select_phonebook_req()
        if phonebook:
            _req.pb_type=phoneboook
        self.sendATcommand(_req, None)

    def ucs2_to_ascii(self, v):
        """convert an UCS-2 to ASCII string"""
        return v.decode('hex').decode('utf_16be')
    def ascii_to_ucs2(self, v):
        """convert an ascii string to UCS-2"""
        return v.encode('utf_16be').encode('hex').upper()

    def _setmodephonebooktobrew(self):
        self.setmode(self.MODEMODEM)
        self.setmode(self.MODEBREW)
        return True

    def _setmodemodemtobrew(self):
        self.log('Switching from modem to BREW')
        try:
            self.comm.sendatcommand('$QCDMG')
            return True
        except:
            pass
        # give it another try
        self.log('Retry switching from modem to BREW')
        try:
            self.comm.sendatcommand('$QCDMG')
            return True
        except commport.ATError:
	    return False
	except:
            if __debug__:
                self.log('Got an excepetion')
            return False

    def _setmodebrew(self):
        # switch from None to BREW
        self.log('Switching from None to BREW')
        # do it the long, but sure, way: 1st try to switch to modem
        if not self._setmodemodem():
            # can't switch to modem, give up
            return False
        # then switch from modem to BREW
        return self._setmodemodemtobrew()

    def _setmodebrewtomodem(self):
        self.log('Switching from BREW to modem')
        try:
            self.comm.write(self._switch_mode_cmd, False)
            self.comm.readsome(numchars=5, log=False)
            return True
        except:
            pass
        # give it a 2nd try
        try:
            self.comm.write(self._switch_mode_cmd, False)
            self.comm.readsome(numchars=5, log=False)
            return True
        except:
            return False

    def _setmodemodemtophonebook(self):
        self.log('Switching from modem to phonebook')
        self.set_mode(self.protocolclass.MODE_PHONEBOOK)
        return True

    def _setmodemodem(self):
        self.log('Switching to modem')
        try:
            self.comm.sendatcommand('E0V1')
            self.set_mode(self.protocolclass.MODE_MODEM)
            return True
        except:
            pass
        # could be in BREW mode, try switch over
        self.log('trying to switch from BREW mode')
        if not self._setmodebrewtomodem():
            return False
        try:
            self.comm.sendatcommand('E0V1')
            self.set_mode(self.protocolclass.MODE_MODEM)
            return True
        except:
            return False

    def _setmodephonebook(self):
        self.setmode(self.MODEMODEM)
        self.setmode(self.MODEPHONEBOOK)
        return True
        
    def _setmodephonebooktomodem(self):
        self.log('Switching from phonebook to modem')
        self.set_mode(self.protocolclass.MODE_MODEM)
        return True

    def decode_utf16(self, v):
        """Decode a Motorola unicode string"""
        # 1st, find the terminator if exist
        _idx=v.find('\x00\x00')
        # decode the string
        if _idx==-1:
            return v.decode('utf_16le')
        else:
            return v[:_idx+1].decode('utf_16le')
    def encode_utf16(self, v):
        """Encode a unicode/string into a Motorola unicode"""
        return (v+'\x00').encode('utf_16le')
        
    # fundamentals
    def getfundamentals(self, results):
        """Gets information fundamental to interopating with the phone and UI.

        Currently this is:

          - 'uniqueserial'     a unique serial number representing the phone
          - 'groups'           the phonebook groups
          - 'wallpaper-index'  map index numbers to names
          - 'ringtone-index'   map index numbers to ringtone names

        This method is called before we read the phonebook data or before we
        write phonebook data.
        """
        self.log("Retrieving fundamental phone information")
        self.progress(0, 100, 'Retrieving fundamental phone information')
        self.setmode(self.MODEPHONEBOOK)
        self.charset_ascii()
        self.log("Phone serial number")
        results['uniqueserial']=sha.new(self.get_esn()).hexdigest()
        # now read groups
        self.log("Reading group information")
        results['groups']=self._get_groups()
        # ringtone index
        self.setmode(self.MODEBREW)
        self.log('Reading Ringtone Index')
        results['ringtone-index']=self._get_ringtone_index()
        # getting wallpaper-index
        self.log('Reading Wallpaper Index')
        results['wallpaper-index']=self._get_wallpaper_index()
        # Update the group ringtone ID
        self._update_group_ringtone(results)
        # All done
        self.log("Fundamentals retrieved")
        self.setmode(self.MODEMODEM)
        return results

    def _update_group_ringtone(self, results):
        _ringtone_index=results.get('ringtone-index', {})
        _groups=results.get('groups', {})
        for _key,_entry in _groups.items():
            _rt_idx=_entry['ringtone']
            _groups[_key]['ringtone']=_ringtone_index.get(_rt_idx, {}).get('name', None)
        results['groups']=_groups
    def _setup_ringtone_name_dict(self, fundamentals):
        """Create a new ringtone dict keyed by name for lookup"""
        _rt_index=fundamentals.get('ringtone-index', {})
        _rt_name_index={}
        for _key,_entry in _rt_index.items():
            _rt_name_index[_entry['name']]=_key
        return _rt_name_index
    def _setup_group_name_dict(self, fundamentals):
        """Create a new group dict keyed by name for lookup"""
        _grp_name_index={}
        for _key,_entry in fundamentals.get('groups', {}).items():
            _grp_name_index[_entry['name']]=_key
        return _grp_name_index

    # speed dial handling stuff
    def _mark_used_slots(self, entries, sd_slots, key_name):
        """Mark the speed dial slots being used"""
        for _key,_entry in enumerate(entries):
            _sd=_entry.get('speeddial', None)
            if _sd is not None:
                if sd_slots[_sd]:
                    entries[_key]['speeddial']=None
                else:
                    sd_slots[_sd]=_entry[key_name]

    def _get_sd_slot(self, entries, sd_slots, key_name):
        """Populate the next available speed dial"""
        for _index,_entry in enumerate(entries):
            if _entry.get('speeddial', None) is None:
                try:
                    _new_sd=sd_slots.index(False)
                    entries[_index]['speeddial']=_new_sd
                    sd_slots[_new_sd]=_entry[key_name]
                except ValueError:
                    self.log('Failed to allocate speed dial value')
                
    def _ensure_speeddials(self, fundamentals):
        """Make sure that each and every number/email/mail list has a
        speed dial, which is being used as the slot/index number
        """
        _pb_book=fundamentals.get('phonebook', {})
        _sd_slots=[False]*(self.protocolclass.PB_TOTAL_ENTRIES+1)
        _sd_slots[0]=True
        # go through the first round and mark the slots being used
        for _key,_pb_entry in _pb_book.items():
            self._mark_used_slots(_pb_entry.get('numbers', []), _sd_slots,
                                  'number')
            self._mark_used_slots(_pb_entry.get('emails', []), _sd_slots,
                                  'email')
            self._mark_used_slots(_pb_entry.get('maillist', []), _sd_slots,
                                  'entry')
        # go through the 2nd time and populate unknown speed dials
        for _key, _pb_entry in _pb_book.items():
            self._get_sd_slot(_pb_entry.get('numbers', []), _sd_slots,
                              'number')
            self._get_sd_slot(_pb_entry.get('emails', []), _sd_slots,
                              'email')
            self._get_sd_slot(_pb_entry.get('maillist', []), _sd_slots,
                              'entry')
        return _sd_slots

    # subclass needs to define these
    def _get_groups(self):
        raise NotImplementedError
    def _get_ringtone_index(self):
        raise NotImplementedError
    def _get_wallpaper_index(self):
        raise NotImplementedError
    def _save_groups(self, fundamentals):
        raise NotImplementedError
    def _build_pb_entry(self, entry, pb_book, fundamentals):
        raise NotImplementedError

    # Phonebook stuff
    def _build_pb_entry(self, entry, pb_book, fundamentals):
        """Build a BitPim phonebook entry based on phon data.
        Need to to implement in subclass for each phone
        """
        raise NotImplementedError
    def _update_mail_list(self, pb_book, fundamentals):
        raise NotImplementedError

    def getphonebook(self, result):
        """Reads the phonebook data.  The L{getfundamentals} information will
        already be in result."""
        self.log('Getting phonebook')
        self.setmode(self.MODEPHONEBOOK)
        # pick the main phonebook
        self.select_phonebook()
        # setting up
        pb_book={}
        result['pb_list']=[]
        result['sd_dict']={}
        # loop through and read 10 entries at a time
        _total_entries=self.protocolclass.PB_TOTAL_ENTRIES
        _req=self.protocolclass.read_pb_req()
        for _start_idx in range(1, _total_entries+1, 10):
            _end_idx=min(_start_idx+9, _total_entries)
            _req.start_index=_start_idx
            _req.end_index=_end_idx
            self.progress(_total_entries, _end_idx,
                          'Reading conatct entry %d to %d'%(_start_idx, _end_idx))
            _res=self.sendATcommand(_req, self.protocolclass.read_pb_resp)
            for _entry in _res:
                self._build_pb_entry(_entry, pb_book, result)
        self._update_mail_list(pb_book, result)
        self.setmode(self.MODEMODEM)
        del result['pb_list'], result['sd_dict']
        _keys=result['groups'].keys()
        result['categories']=[x['name'] for _,x in result['groups'].items()]
        result['phonebook']=pb_book
        return pb_book

    def savephonebook(self, result):
        "Saves out the phonebook"
        self.log('Writing phonebook')
        self.setmode(self.MODEPHONEBOOK)
        # setting up what we need
        result['ringtone-name-index']=self._setup_ringtone_name_dict(result)
        result['group-name-index']=self._setup_group_name_dict(result)
        result['sd-slots']=self._ensure_speeddials(result)
        # save the group
        self._save_groups(result)
        self._write_pb_entries(result)
        # clean up
        del result['ringtone-name-index'], result['group-name-index']
        del result['sd-slots']
        self.setmode(self.MODEMODEM)
        return result

    # Calendar Stuff------------------------------------------------------------
    def _build_cal_entry(self, entry, calendar, fundamentals):
        """Build a BitPim calendar object from phonebook data"""
        raise NotImplementedError

    def del_calendar_entry(self, index):
        _req=self.protocolclass.calendar_write_ex_req()
        _req.index=index
        _req.nth_event=0
        _req.ex_event_flag=0
        self.sendATcommand(_req, None)

    def lock_calendar(self, lock=True):
        """Lock the calendar to access it"""
        _req=self.protocolclass.calendar_lock_req()
        if lock:
            _req.lock=1
        else:
            _req.lock=0
        self.sendATcommand(_req, None)

    def getcalendar(self,result):
        """Read all calendars from the phone"""
        self.log('Reading calendar entries')
        self.setmode(self.MODEPHONEBOOK)
        self.lock_calendar()
        _total_entries=self.protocolclass.CAL_TOTAL_ENTRIES
        _max_entry=self.protocolclass.CAL_MAX_ENTRY
        _req=self.protocolclass.calendar_read_req()
        _calendar={ 'exceptions': [] }
        for _start_idx in range(0, _total_entries, 10):
            _end_idx=min(_start_idx+9, _max_entry)
            _req.start_index=_start_idx
            _req.end_index=_end_idx
            self.progress(_total_entries, _end_idx,
                          'Reading calendar entry %d to %d'%(_start_idx, _end_idx))
            _res=self.sendATcommand(_req, self.protocolclass.calendar_req_resp)
            for _entry in _res:
                self._build_cal_entry(_entry, _calendar, result)
        self._process_exceptions(_calendar)
        del _calendar['exceptions']
        self.lock_calendar(False)
        self.setmode(self.MODEMODEM)
        result['calendar']=_calendar
        return result

    def savecalendar(self, result, merge):
        """Save calendar entries to the phone"""
        self.log('Writing calendar entries')
        self.setmode(self.MODEPHONEBOOK)
        self.lock_calendar()
        self._write_calendar_entries(result)
        self.lock_calendar(False)
        self.setmode(self.MODEMODEM)
        return result

    # Ringtones & wallpaper sutff------------------------------------------------------------
    def _read_media(self, index_key, fundamentals):
        """Read the contents of media files and return"""
        _media={}
        for _key,_entry in fundamentals.get(index_key, {}).items():
            if _entry.get('filename', None):
                # this one associates with a file, try to read it
                try:
                    _media[_entry['name']]=self.getfilecontents(_entry['filename'])
                except (com_brew.BrewNoSuchFileException,
                        com_brew.BrewBadPathnameException,
                        com_brew.BrewNameTooLongException,
                        ValueError):
                    self.log("Failed to read media file: %s"%_entry['name'])
        return _media

    def getringtones(self, fundamentals):
        """Retrieve ringtones data"""
        self.log('Reading ringtones')
        self.setmode(self.MODEPHONEBOOK)
        self.setmode(self.MODEBREW)
        try:
            fundamentals['ringtone']=self._read_media('ringtone-index',
                                                      fundamentals)
        except:
            if __debug__:
                raise
        self.setmode(self.MODEMODEM)
        return fundamentals

    def getwallpapers(self, fundamentals):
        """Retrieve wallpaper data"""
        self.log('Reading wallpapers')
        self.setmode(self.MODEPHONEBOOK)
        self.setmode(self.MODEBREW)
        try:
            fundamentals['wallpapers']=self._read_media('wallpaper-index',
                                                        fundamentals)
        except:
            if __debug__:
                raise
        self.setmode(self.MODEMODEM)
        return fundamentals

#------------------------------------------------------------------------------
parentprofile=com_gsm.Profile
class Profile(parentprofile):
    BP_Calendar_Version=3
