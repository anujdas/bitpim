### BITPIM ( -*- python -*- )
###
### Copyright (C) 2009-2010 Nathan Hjelm <hjelmn@users.sourceforge.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
###

%{

"""Various descriptions of data specific to LG VX9200"""

# groups     - same as VX-8700
# phonebook  - LG Phonebook v1.0 Extended (same as VX-11K)
# schedule   - same as VX-8550
# memos      - same as VX-8550
# sms        - same as VX-9100
# index file - same as VX-9700
from p_lgvx11000 import *

# SMS index files
inbox_index     = "dload/inbox.dat"
outbox_index    = "dload/outbox.dat"
drafts_index    = "dload/drafts.dat"

%}

# Call history

PACKET call:
    4 GPSDATE GPStime    # no. of seconds since 0h 1-6-80, based off local time.
    4 UINT  unk0         # different for each call
    4 UINT  duration     # seconds, not certain about length of this field
    49 USTRING {'raiseonunterminatedread': False} number
    36 USTRING {'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False} name
    1 UINT  numberlength # length of phone number
    1 UINT  status       # 0=outgoing, 1=incoming, 2=missed, etc
    1 UINT  pbnumbertype # 1=cell, 2=home, 3=office, 4=cell2, 5=fax, 6=vmail, 0xFF=not in phone book
    4 UINT  unk1         # always seems to be 0
    2 UINT  pbentrynum   # entry number in phonebook
    75 DATA number_location # set by pay software

PACKET callhistory:
    4 UINT { 'default': 0x00020000 } unk0
    4 UINT numcalls
    1 UINT unk1
    * LIST {'elementclass': call, 'length': self.numcalls} +calls

# Index files
PACKET indexentry:
    256 USTRING {'encoding': PHONE_ENCODING,
                 'raiseonunterminatedread': False,
                 'raiseontruncate': False } filename  "full pathname"
    4 UINT size
    4 UINT {'default': 0} +date
    4 UINT type
    4 UINT {'default': 0} +unk0

PACKET indexfile:
    "Used for tracking wallpaper and ringtones"
    * LIST {'elementclass': indexentry, 'createdefault': True} +items
                    
# /pim/pbnumber.dat format
PACKET pnfileentry:
    4   STRING { 'terminator': None,
                 'raiseonunterminatedread': False,
                 'raiseontruncate': False,
                 'default': '\xff\xff\xff\xff'} +entry_tag # some entries don't have this??
    if self.entry_tag != '\xff\xff\xff\xff':
        # this is a valid slot
        2 UINT { 'default': 0 } +pad00
        # year, month, day, hour, min, sec
        * PBDateTime {'defaulttocurrenttime': True } +mod_date
        6   STRING { 'default': '', 'raiseonunterminatedread': False } +unk0
        2   UINT pn_id # 0 based
        2   UINT pe_id # 0 based
        1   UINT { 'default': 0 } +unknown00
        1   UINT pn_order "0-based order of this phone within this contact"
        25  LGHEXPN phone_number
        1   UINT { 'default': 1 } +unknown01
        1   UINT ntype
        1   UINT { 'default': 0 } +unknown02
        6   USTRING { 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False, 'default': '</PN>'} +exit_tag # some entries don't have this??
    else:
        # empty slot: all 0xFF
        60 DATA { 'default': '\xFF'*60 } +blanks
    %{
    def valid(self):
         return self.phone_number != None
    def malformed(self):
         # malformed (yet valid) entries have been seen on several phones including the VX-8550 and VX-10000
         return self.entry_tag != PB_NUMBER_SOR
    %}

PACKET pnfile:
    * LIST { 'elementclass': pnfileentry,
             'createdefault': True,
             'length': NUMPHONENUMBERENTRIES } +items

# pbgroup.dat
# The VX9100 has a fixed size pbgroup.dat, hence the need to fill up with
# unused slots.
PACKET pbgroup:
    34 USTRING {'encoding': PHONE_ENCODING,
                'raiseonunterminatedread': False,
                'raiseontruncate': False,
                'default': '' } +name
    2  UINT { 'default': 0 } +groupid
    1  UINT { 'default': 0 } +user_added "=1 when was added by user -- not really"
    2  UINT { 'default': 0 } +unk0

PACKET pbgroups:
    "Phonebook groups"
    * LIST {'elementclass': pbgroup,
            'length': MAX_PHONEBOOK_GROUPS,
            'createdefault': True} +groups

# sms/inbox/inbox****.dat format
PACKET SMSINBOXMSGFRAGMENT:
    * LIST { 'length': 222 } +msg:
        1 UINT byte "individual byte of message"

PACKET sms_in:
    4  UINT    unk0      # zero
    4  UINT    index
    4  UINT    unk1      # always ends in 02 00?
    4  GPSDATE GPStime   # num seconds since 0h 1-6-80, time message received by phone
    6  SMSDATE timesent  # as BCD, year-month-day-hour-minute-second
    2  UINT    unk2      # zero
    4  GPSDATE gtimesent # num seconds since 0h 1-6-80, time message received by phone
    1  UINT    read      # boolean, 0 = unread, 1 = read
    1  UINT    locked    # boolean, 0 = unread, 1 = read
    1  UINT    priority  # 0 = normal, 1 = high
    5  UNKNOWN unk3
    1  UINT    encoding  # 02 = 7-bit, 04 = UTF-16BE, 08 = ISO-8859-1, 09 = multipart-7-bit
    7  UNKNOWN unk4
    1  UINT    has_udh   # 0 = no, 2 = yes binary UDH header
    1  UINT    num_msg_fragments # up to 20
    *  LIST { 'length': 60 } +subject:
        1 UINT byte "individual byte of subject"
    4  UINT     unk5      # zero
    *  LIST { 'length': 20 } +msgs:
        1 UINT msg_id
        1 UINT msg_length
        * SMSINBOXMSGFRAGMENT msg_data
    24 USTRING sender
    33 USTRING sender_name
    49 USTRING callback
    4  UINT    unk6      # sender id?
