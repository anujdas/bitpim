### BITPIM
###
### Copyright (C) 2009 Joe Pham<djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to the Samsung SCH-U750 (Alias 2) Phone"""

from prototypes import *
from prototypes_samsung import *
from p_brew import *
from p_samsungschu470 import *

SND_PATH='brew/mod/18067'
SND_INDEX_FILE_NAME=SND_PATH+'/MsInfo.db'
SND_EXCLUDED_FILES=('MsInfo.db',)
SND_PRELOADED_PREFIX=SND_PATH+'/SCH-U750_PRELOADED_'

# phonebook stuff,
PB_WP_CACHE_WIDTH=80
PB_WP_CACHE_HEIGHT=106
PB_MAX_IMNAME_LEN=50
PB_MAX_STREET_LEN=50
PB_MAX_CITY_LEN=50
PB_MAX_STATE_LEN=50
PB_MAX_ZIP_LEN=10
PB_MAX_COUNTRY_LEN=50
# Flag
PB_FLG_IMNAME1=0x8000
# Flag 2
PB_FLG_IMNAME2=0x0001
PB_FLG_STREET=0x0002
PB_FLG_CITY=0x0004
PB_FLG_STATE=0x0008
PB_FLG_ZIP=0x0010
PB_FLG_COUNTRY=0x0020
PB_FLG_ENTRY_WP=0x0100
PB_FLG_ENTRY_RT=0x0080
PB_FLG_ENTRY_CACHED_WP=0x0040
# each number entry flag
PB_FLG_DUNNO1=0x04
%}

# Sounds stuff
PACKET WSoundsIndexEntry:
    P STRING name
    * STRING { 'terminator': None,
               'default': '/ff/' } +path_prefix
    * STRING { 'terminator': None } pathname
    * STRING { 'terminator': None,
               'default': '|0|7\x0A' } +eor
PACKET WSoundsIndexFile:
    * LIST { 'elementclass': WSoundsIndexEntry } +items
PACKET RSoundIndexEntry:
    * STRING { 'terminator': 0x7C } pathname
    * STRING { 'terminator': 0x0A } misc
PACKET RSoundsIndexFile:
    * LIST { 'elementclass': RSoundIndexEntry } +items


# phonebook/contact stuff

PACKET -NumberEntry:
    * STRING { 'terminator': None,
               'pascal': True } number
    1 UINT option
    if self.has_speeddial:
        2 UINT speeddial
    if self.has_dunno1:
        4 DONTCARE
    %{
    @property
    def has_speeddial(self):
        return bool(self.option & PB_FLG_SPEEDDIAL)
    @property
    def has_dunno1(self):
        return bool(self.option & PB_FLG_DUNNO1)
    @property
    def is_primary(self):
        return bool(self.option & PB_FLG_PRIMARY)
    @property
    def has_ringtone(self):
        return False
    %}

PACKET -PBEntry:
    2 UINT info
    2 UINT info2
    if self.has_name:
        * USTRING { 'terminator': None,
                    'encoding': ENCODING,
                    'pascal': True } name
    if self.has_email:
        * USTRING { 'terminator': None,
                    'encoding': ENCODING,
                    'pascal': True } email
    if self.has_email2:
        * USTRING { 'terminator': None,
                    'encoding': ENCODING,
                   'pascal': True } email2
    if self.has_home:
        * NumberEntry home
    if self.has_work:
        * NumberEntry work
    if self.has_cell:
        * NumberEntry cell
    if self.has_fax:
        * NumberEntry fax
    if self.has_cell2:
        * NumberEntry cell2
    if self.has_note:
        * STRING { 'terminator': None,
                   'pascal': True } note
    if self.has_date:
        4 DateTime datetime
    if self.has_group:
        4 UINT group
    if self.has_im_name:
        * STRING { 'terminator': None,
                   'pascal': True } im_name
        1 UINT im_type
    if self.has_street:
        * STRING { 'terminator': None,
                   'pascal': True } street
    if self.has_city:
        * STRING { 'terminator': None,
                   'pascal': True } city
    if self.has_state:
        * STRING { 'terminator': None,
                   'pascal': True } state
    if self.has_zipcode:
        * STRING { 'terminator': None,
                   'pascal': True } zipcode
    if self.has_country:
        * STRING { 'terminator': None,
                   'pascal': True } country
    if self.has_cached_wp:
        * STRING { 'terminator': None,
                   'pascal': True } cached_wp
        4 UINT cached_wp_num
    if self.has_ringtone:
        * STRING { 'terminator': None,
                   'pascal': True } ringtone
    if self.has_wallpaper:
        * STRING { 'terminator': None,
                   'pascal': True } wallpaper
    %{
    @property
    def has_name(self):
        return bool(self.info & PB_FLG_NAME)
    @property
    def has_email(self):
        return bool(self.info & PB_FLG_EMAIL)
    @property
    def has_email2(self):
        return bool(self.info & PB_FLG_EMAIL2)
    @property
    def has_home(self):
        return bool(self.info & PB_FLG_HOME)
    @property
    def has_work(self):
        return bool(self.info & PB_FLG_WORK)
    @property
    def has_cell(self):
        return bool(self.info & PB_FLG_CELL)
    @property
    def has_fax(self):
        return bool(self.info & PB_FLG_FAX)
    @property
    def has_cell2(self):
        return bool(self.info & PB_FLG_CELL2)
    @property
    def has_note(self):
        return bool(self.info & PB_FLG_NOTE)
    @property
    def has_date(self):
        return bool(self.info & PB_FLG_DATE)
    @property
    def has_group(self):
        return bool(self.info & PB_FLG_GROUP)
    @property
    def has_im_name(self):
        return bool((self.info & PB_FLG_IMNAME1) and (self.info2 & PB_FLG_IMNAME2))
    @property
    def has_street(self):
        return bool(self.info2 & PB_FLG_STREET)
    @property
    def has_city(self):
        return bool(self.info2 & PB_FLG_CITY)
    @property
    def has_state(self):
        return bool(self.info2 & PB_FLG_STATE)
    @property
    def has_zipcode(self):
        return bool(self.info2 & PB_FLG_ZIP)
    @property
    def has_country(self):
        return bool(self.info2 & PB_FLG_COUNTRY)
    @property
    def has_cached_wp(self):
        return bool(self.info2 & PB_FLG_ENTRY_CACHED_WP)
    @property
    def has_ringtone(self):
        return bool(self.info2 & PB_FLG_ENTRY_RT)
    @property
    def has_wallpaper(self):
        return bool(self.info2 & PB_FLG_ENTRY_WP)
    @property
    def has_address(self):
        # return True if this has at least one valid address item
        return self.has_street or self.has_city or self.has_state or \
               self.has_zipcode or self.has_country
    @property
    def address(self):
        # return the address in a BitPim phonebook addresses dict
        _addr={}
        if self.has_street:
            _addr['street']=self.street
        if self.has_city:
            _addr['city']=self.city
        if self.has_state:
            _addr['state']=self.state
        if self.has_zipcode:
            _addr['postalcode']=self.zipcode
        if self.has_country:
            _addr['country']=self.country
        return _addr
    %}

PACKET -LenEntry:
    2 UINT { 'default': 0 } +itemlen

PACKET -PBFile:
    * LIST { 'elementclass': LenEntry,
             'length': 8,
             'createdefault': True } +lens
    * LIST { 'elementclass': PBEntry } +items

PACKET -PBFileHeader:
    * LIST { 'elementclass': LenEntry,
             'length': 8,
             'createdefault': True } +lens

PACKET ss_cmd_hdr:
    4 UINT { 'default': 0xfb4b } +commandcode
    1 UINT command

PACKET ss_cmd_resp:
    * ss_cmd_hdr cmd_hdr
    * DATA data

PACKET ss_sw_req:
    * ss_cmd_hdr { 'command': SS_CMD_SW_VERSION } +hdr
PACKET -ss_sw_resp:
    * ss_cmd_hdr hdr
    * STRING { 'terminator': 0 } sw_version
PACKET ss_hw_req:
    * ss_cmd_hdr { 'command': SS_CMD_HW_VERSION } +hdr
PACKET -ss_hw_resp:
    * ss_cmd_hdr hdr
    * STRING { 'terminator': 0 } hw_version

PACKET ss_pb_count_req:
    * ss_cmd_hdr { 'command': SS_CMD_PB_COUNT } +hdr
PACKET -ss_pb_count_resp:
    * ss_cmd_hdr hdr
    1 DONTCARE
    2 UINT count
PACKET ss_pb_read_req:
    * ss_cmd_hdr { 'command': SS_CMD_PB_READ } +hdr
    1 DONTCARE +
    2 UINT index
PACKET -ss_pb_read_resp:
    * ss_cmd_hdr hdr
    1 DONTCARE
    2 UINT index
    1 DONTCARE
    * DATA data
PACKET ss_pb_voicemail_read_req:
    * ss_cmd_hdr { 'command': SS_CMD_PB_VOICEMAIL_READ } +hdr
    1 UINT { 'constant': SS_CMD_PB_VOICEMAIL_PARAM } +param
PACKET -ss_pb_voicemail_resp:
    * ss_cmd_hdr hdr
    1 UINT param
    * STRING { 'terminator': 0 } number
PACKET ss_pb_voicemail_write_req:
    * ss_cmd_hdr { 'command': SS_CMD_PB_VOICEMAIL_WRITE } +hdr
    1 UINT { 'constant': SS_CMD_PB_VOICEMAIL_PARAM } +param
    * STRING { 'terminator': 0,
               'default': PB_DEFAULT_VOICEMAIL_NUMBER } +number
PACKET ss_pb_clear_req:
    * ss_cmd_hdr { 'command': SS_CMD_PB_CLEAR } +hdr
PACKET -ss_pb_clear_resp:
    * ss_cmd_hdr hdr
    2 UINT flg

PACKET ss_number_entry:
    * STRING { 'terminator': 0,
               'default': '',
               'maxsizeinbytes': PB_MAX_NUMBER_LEN,
               'raiseontruncate': False } +number
    2 UINT { 'default': 0 } +speeddial
    1 UINT { 'default': 0 } +primary
    8 DONTCARE +
    * STRING { 'terminator': 0,
               'default': '' } +ringtone

PACKET ss_pb_entry:
    * USTRING { 'terminator': 0,
                'maxsizeinbytes': PB_MAX_NAME_LEN,
                'encoding': ENCODING,
                'raiseontruncate': False } name
    * USTRING { 'terminator': 0,
                'encoding': ENCODING,
                'default': '',
                'maxsizeinbytes': PB_MAX_EMAIL_LEN,
                'raiseontruncate': False } +email
    * USTRING { 'terminator': 0,
                'encoding': ENCODING,
                'default': '',
                'maxsizeinbytes': PB_MAX_EMAIL_LEN,
                'raiseontruncate': False } +email2
    2 DONTCARE +
    * USTRING { 'terminator': 0,
                'encoding': ENCODING,
                'maxsizeinbytes': PB_MAX_NOTE_LEN,
                'raiseontruncate': False,
                'default': '' } +note
    1 DONTCARE +
    * STRING { 'terminator': 0,
               'default': '' } +wallpaper
    1 UINT { 'default': 0 } +wallpaper_range
    * ss_number_entry +home
    * ss_number_entry +work
    * ss_number_entry +cell
    * ss_number_entry +dummy
    * ss_number_entry +fax
    * ss_number_entry +cell2
    4 DONTCARE +
    1 UINT { 'default': 0 } +group
    2 DONTCARE +
    * USTRING { 'terminator': 0,
                'encoding': ENCODING,
                'maxsizeinbytes': PB_MAX_STREET_LEN,
                'raiseontruncate': False,
                'default': '' } +street
    * USTRING { 'terminator': 0,
                'encoding': ENCODING,
                'maxsizeinbytes': PB_MAX_CITY_LEN,
                'raiseontruncate': False,
                'default': '' } +city
    * USTRING { 'terminator': 0,
                'encoding': ENCODING,
                'maxsizeinbytes': PB_MAX_STATE_LEN,
                'raiseontruncate': False,
                'default': '' } +state
    * USTRING { 'terminator': 0,
                'encoding': ENCODING,
                'maxsizeinbytes': PB_MAX_ZIP_LEN,
                'raiseontruncate': False,
                'default': '' } +zipcode
    * USTRING { 'terminator': 0,
                'encoding': ENCODING,
                'maxsizeinbytes': PB_MAX_COUNTRY_LEN,
                'raiseontruncate': False,
                'default': '' } +country
    * USTRING { 'terminator': 0,
                'encoding': ENCODING,
                'maxsizeinbytes': PB_MAX_IMNAME_LEN,
                'raiseontruncate': False,
                'default': '' } +im_name
    2 UINT { 'default': 0 } +im_type
    %{
    def _set_address(self, addr):
        # set address fields based on BitPim phonebook address dict
        if not isinstance(addr, dict):
            raise TypeError('addr must be of type dict')
        self.street=addr.get('street', '')
        self.city=addr.get('city', '')
        self.state=addr.get('state', '')
        self.zipcode=addr.get('postalcode', '')
        self.country=addr.get('country', '')
    def _get_address(self):
        # return address items in BitPim phonebook address dict
        return { 'street': self.street, 'city': self.city,
                 'state': self.state, 'postalcode': self.zipcode,
                 'country': self.country }
    address=property(fget=_get_address, fset=_set_address)
    %}

PACKET ss_pb_write_req:
    * ss_cmd_hdr { 'command': SS_CMD_PB_WRITE } +hdr
    1 DONTCARE +
    * ss_pb_entry entry

PACKET -ss_pb_write_resp:
    * ss_cmd_hdr hdr
    1 DONTCARE
    2 UINT index

# Call History
PACKET -cl_list:
    2 UINT index

PACKET -cl_index_file:
    * LIST { 'length': CL_MAX_ENTRIES,
             'elementclass': cl_list } incoming
    * LIST { 'length': CL_MAX_ENTRIES,
             'elementclass': cl_list } outgoing
    * LIST { 'length': CL_MAX_ENTRIES,
             'elementclass': cl_list } missed
    1374 DONTCARE
    4 UINT incoming_count
    4 UINT outgoing_count
    4 UINT missed_count

PACKET -cl_file:
    1 UINT cl_type
    51 STRING { 'terminator': 0 } number
    4 DateTime2 datetime
    4 DONTCARE
    4 UINT duration
    %{
    @property
    def valid(self):
        global CL_VALID_TYPE
        return bool(self.cl_type in CL_VALID_TYPE and self.number)
    %}

# Calendar and notes stuff
PACKET CalIndexEntry:
    2 UINT { 'default': 0 } +index
PACKET CalIndexFile:
    2 UINT next_index
    12 DONTCARE +
    2 UINT numofevents
    6 DONTCARE +
    2 UINT numofnotes
    6 DONTCARE +
    2 UINT numofactiveevents
    112 DONTCARE +
    * LIST { 'elementclass': CalIndexEntry,
             'length': 103,
             'createdefault': True } +events
    * LIST { 'elementclass': CalIndexEntry,
             'length': 35,
             'createdefault': True } +notes
    * LIST { 'elementclass': CalIndexEntry,
             'length': 319,
             'createdefault': True } +activeevents

PACKET CalEntry:
    2 UINT titlelen
    * USTRING { 'sizeinbytes': self.titlelen,
                'encoding': ENCODING,
                'terminator': None } title
    4 DateTime2 start
    4 DateTime2 { 'default': self.start } +start2
    4 DateTime2 end
    1 DONTCARE { 'default': '\x01' } +
    1 UINT repeat
    1 DONTCARE { 'default': '\x03' } +
    1 UINT alarm
    1 UINT alert
    1 UINT { 'default': 0 } +reminder
    5 DONTCARE +
    4 UINT duration
    1 UINT timezone
    4 DateTime2 creationtime
    4 DateTime2 { 'default': self.creationtime } +modifiedtime
    2 UINT ringtonelen
    * STRING { 'sizeinbytes': self.ringtonelen,
               'terminator': None } ringtone
    2 DONTCARE +

PACKET NotePadEntry:
    2 UINT textlen
    * USTRING { 'terminator': None,
                'encoding': ENCODING,
                'sizeinbytes': self.textlen } text
    4 DateTime2 creation
    4 DateTime2 { 'default': self.creation } +creation2
    6 DONTCARE +
    1 DONTCARE { 'default': '\x05' } +
    12 DONTCARE +
    1 DONTCARE { 'default': '\x30' } +
    4 DateTime2 { 'default': self.creation } +modified
    4 DateTime2 { 'default': self.modified } +modified2
    4 DONTCARE +

# SMS Stuff
PACKET pBOOL:
    P BOOL value

PACKET -sms_header:
    2 UINT index
    1 DONTCARE
    1 UINT msg_len
    1 DONTCARE
    1 UINT callback_len
    1 UINT bitmap1
    1 UINT bitmap2
    6 DONTCARE
    2 UINT body_len
    2 UINT file_type
    1 UINT msg_type
    1 UINT enhance_delivery
    * pBOOL { 'value': self.file_type==SMS_TXT_TYPE and self.msg_type in SMS_VALID_TYPE } is_txt_msg
    * pBOOL { 'value': self.msg_type==SMS_TYPE_IN } in_msg
    * pBOOL { 'value': self.msg_type==SMS_TYPE_SENT } sent_msg
    * pBOOL { 'value': self.msg_type==SMS_TYPE_DRAFT } draft_msg
    if self.is_txt_msg.value:
        * sms_body {
            'msg_len': self.msg_len,
            'has_callback': self.bitmap2 & SMS_FLG2_CALLBACK,
            'has_priority': self.bitmap2 & SMS_FLG2_PRIORITY,
            'has_1byte': (self.bitmap2 & SMS_FLG2_SOMETHING) or (not self.bitmap2),
            'has_1byte2': self.bitmap2 & SMS_FLG2_MSG,
            'has_40bytes': self.bitmap1 & SMS_FLG1_HAS40 } body

PACKET -sms_msg_stat_list:
    1 UINT status
PACKET -sms_datetime_list:
    4 DateTime2 datetime
PACKET -sms_delivered_datetime:
    * LIST { 'elementclass': sms_datetime_list,
             'length': 10 } datetime
    20 DONTCARE
PACKET -sms_body:
    P UINT msg_len
    P BOOL { 'default': True } +has_callback
    P BOOL { 'default': False } +has_priority
    P BOOL { 'default': False } +has_1byte
    P BOOL { 'default': True } +has_1byte2
    P BOOL { 'default': False } +has_40bytes
    if self.msg_len:
        54 DONTCARE
        * USTRING { 'sizeinbytes': self.msg_len,
                    'encoding': ENCODING,
                    'terminator': None } msg
    else:
        53 DONTCARE
        P USTRING {'default': '' } +msg
    if self.has_callback:
        4 DONTCARE
        1 UINT callback_len
        * STRING { 'sizeinbytes': self.callback_len,
                   'terminator': None } callback
    if self.has_priority:
        1 UINT priority
    if self.has_1byte:
        1 DONTCARE
    40 DONTCARE
    4 DateTime1 datetime
    13 DONTCARE
    1 UINT addr_len0
    1 UINT addr_len1
    1 UINT addr_len2
    1 UINT addr_len3
    1 UINT addr_len4
    1 UINT addr_len5
    1 UINT addr_len6
    1 UINT addr_len7
    1 UINT addr_len8
    1 UINT addr_len9
    if self.addr_len0:
        * STRING { 'sizeinbytes': self.addr_len0,
                   'terminator': None } addr0
    if self.addr_len1:
        * STRING { 'sizeinbytes': self.addr_len1,
                   'terminator': None } addr1
    if self.addr_len2:
        * STRING { 'sizeinbytes': self.addr_len2,
                   'terminator': None } addr2
    if self.addr_len3:
        * STRING { 'sizeinbytes': self.addr_len3,
                   'terminator': None } addr3
    if self.addr_len4:
        * STRING { 'sizeinbytes': self.addr_len4,
                   'terminator': None } addr4
    if self.addr_len5:
        * STRING { 'sizeinbytes': self.addr_len5,
                   'terminator': None } addr5
    if self.addr_len6:
        * STRING { 'sizeinbytes': self.addr_len6,
                   'terminator': None } addr6
    if self.addr_len7:
        * STRING { 'sizeinbytes': self.addr_len7,
                   'terminator': None } addr7
    if self.addr_len8:
        * STRING { 'sizeinbytes': self.addr_len8,
                   'terminator': None } addr8
    if self.addr_len9:
        * STRING { 'sizeinbytes': self.addr_len9,
                   'terminator': None } addr9
    if not self.has_1byte and self.has_1byte2:
        1 DONTCARE
    if self.has_1byte2:
        1 DONTCARE
    81 DONTCARE
    if self.has_40bytes:
        40 DONTCARE
    * LIST { 'elementclass': sms_msg_stat_list,
             'length': 10 } msg_stat
    # too hard to do it here.  Will be handled by the phone code
##    if self.msg_stat[0].status==SMS_STATUS_DELIVERED:
##        4 DateTime1 delivered_datetime
##        96 UNKNOWN dunno10
##    4 UINT locked
