### BITPIM
###
### Copyright (C) 2005 Andrew Zitnay <drew@zitnay.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to LG VI125"""

import re

from prototypes import *
from prototypeslg import *

# Make all lg stuff available in this module as well
from p_lg import *


# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

NUMSPEEDDIALS=100
FIRSTSPEEDDIAL=1
LASTSPEEDDIAL=99
NUMPHONEBOOKENTRIES=200
MAXCALENDARDESCRIPTION=38

NUMEMAILS=3
NUMPHONENUMBERS=5

NUMGROUPS=20
NUMMAPGROUPS=500

NORINGTONE=0
NOMSGRINGTONE=0
NOWALLPAPER=0

MEMOLENGTH=33
SMS_CANNED_MAX_ITEMS=18
SMS_CANNED_MAX_LENGTH=101
SMS_CANNED_FILENAME="sms/mediacan000.dat"
SMS_PATTERNS={'Inbox': re.compile(r"^.*/inbox[0-9][0-9][0-9]\.dat$"),
             'Sent': re.compile(r"^.*/outbox[0-9][0-9][0-9]\.dat$"),
             'Saved': re.compile(r"^.*/sf[0-9][0-9]\.dat$"),
             }



numbertypetab=( 'cell', 'home', 'office', 'fax', 'pager' )


# Calendar parameters
NUMCALENDARENTRIES=300  # ?? for VI125
CAL_REP_NONE=0x10
CAL_REP_DAILY=0x11
CAL_REP_MONFRI=0x12
CAL_REP_WEEKLY=0x13
CAL_REP_MONTHLY=0x14
CAL_REP_YEARLY=0x15
CAL_DOW_SUN=0x0800
CAL_DOW_MON=0x0400
CAL_DOW_TUE=0x0200
CAL_DOW_WED=0x0100
CAL_DOW_THU=0x0080
CAL_DOW_FRI=0x0040
CAL_DOW_SAT=0x0020
CAL_DOW_EXCEPTIONS=0x0010
CAL_REMINDER_NONE=0
CAL_REMINDER_ONTIME=1
CAL_REMINDER_5MIN=2
CAL_REMINDER_10MIN=3
CAL_REMINDER_1HOUR=4
CAL_REMINDER_1DAY=5
CAL_REMINDER_2DAYS=6
CAL_REPEAT_DATE=(4095, 12, 31)

cal_dir='sch'
cal_data_file_name='sch/schedule.dat'
cal_exception_file_name='sch/schexception.dat'
cal_has_voice_id=False

%}

PACKET firmwareresponse:
    1 UINT command
    11 USTRING {'terminator': None}  date1
    8 USTRING {'terminator': None}  time1
    11 USTRING {'terminator': None}  date2
    8 USTRING {'terminator': None}  time2
    8 USTRING {'terminator': None}  firmwareversion

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

# All STRINGS have raiseonterminatedread as False since the phone does
# occassionally leave out the terminator byte
# Note if you change the length of any of these fields, you also
# need to modify com_lgvi125 to give a different truncateat parameter
# in the convertphonebooktophone method
PACKET pbentry:
    1  UINT serial1
    1  UINT {'constant': 0x00} +unknown3
    1  UINT {'constant': 0x00} +unknown4
    1  UINT {'constant': 0x00} +unknown5
    1  UINT {'constant': 0x72} +unknown6
    1  UINT unknown7
    1  UINT serial2
    1  UINT {'constant': 0x00} +unknown8
    1  UINT {'constant': 0x00} +unknown9
    1  UINT {'constant': 0x00} +unknown10
    33 USTRING {'raiseonunterminatedread': False} name
    1  UINT group
    1  UINT {'constant': 0x00} +unknown11
    1  UINT ringtone                                     "ringtone index for a call"
    1  UINT unknown12						# used to set ringtone to default
    1  UINT {'constant': 0x00} +unknown13
    * USTRING {'raiseonunterminatedread': False, 'sizeinbytes': MEMOLENGTH} memo
    *  LIST {'length': NUMEMAILS} +emails:
        73 USTRING {'raiseonunterminatedread': False} email
    73 USTRING {'raiseonunterminatedread': False} url
    4  UINT avatar							# unknown format
    * LIST {'length': NUMPHONENUMBERS} +numberspeeddials:
        1 UINT numberspeeddial
    * LIST {'length': NUMPHONENUMBERS} +numbertypes:
        1 UINT numbertype
    * LIST {'length': NUMPHONENUMBERS} +numbers:
        49 USTRING {'raiseonunterminatedread': False} number
    1 UINT {'constant': 0x7c} +unknown14

# one of the constant unknowns below is most likely the animation, and thus will except
# when someone has a group with a non-default animation (i have none other than the
# default on my phone, so i can't easily figure out which one)
PACKET pbgroup:
    "A single group"
    1 UINT number
    1 UINT unknown1							# 0xff when deleted, 0x30 otherwise
    1 UINT ring
    1 UINT {'constant': 0x00} +unknown2
    1 UINT {'constant': 0x00} +unknown3
    1 UINT {'constant': 0x01} +unknown4
    1 UINT {'constant': 0x00} +unknown5
    1 UINT {'constant': 0x00} +unknown6
    1 UINT unknown7							# sometimes 0x00, sometimes same as number
    1 UINT unknown8							# sometimes 0x00, sometimes 0x01
    33 USTRING name

PACKET pbgroups:
    "Phonebook groups"
    * LIST {'elementclass': pbgroup} +groups

PACKET pbseqgroup:
   1 UINT number
   1 UINT unknown							# 0x00 when deleted, 0x30 otherwise

PACKET pbseqgroups:
  * LIST {'elementclass': pbseqgroup, 'length': NUMGROUPS} +seqgroups

PACKET pbmapgroup:
   1 UINT number
   1 UINT unknown							# 0xFF when deleted, 0x30 otherwise

PACKET pbmapgroups:
  * LIST {'elementclass': pbmapgroup, 'length': NUMMAPGROUPS} +mapgroups

PACKET indexentry:
    2 UINT {'default': 0xffff} +index
    40 USTRING {'default': ""} +name

PACKET indexfile:
    "Used for tracking wallpaper and ringtones"
    # A bit of a silly design again.  Entries with an index of 0xffff are
    # 'blank'.  Thus it is possible for numactiveitems and the actual
    # number of valid entries to be mismatched.
    P UINT {'constant': 30} maxitems
    2 UINT numactiveitems
    * LIST {'length': self.maxitems, 'elementclass': indexentry, 'createdefault': True} +items

###
### The calendar
###
#
#   The calendar consists of one file listing events and an exception
#   file that lists exceptions.  These exceptions suppress a particular
#   instance of a repeated event.  For example, if you setup something
#   to happen monthly, but changed the 1st february event, then the
#   schedule will contain the repeating event, and the 1st feb one,
#   and the suppresions/exceptions file will point to the repeating
#   event and suppress the 1st feb.
#   The phone uses the position within the file to give an event an id

PACKET scheduleexception:
    4 UINT pos "Refers to event id (position in schedule file) that this suppresses"
    1 UINT day
    1 UINT month
    2 UINT year

PACKET scheduleexceptionfile:
    * LIST {'elementclass': scheduleexception} +items

PACKET scheduleevent:
    P UINT { 'constant': 60 } packet_size "Faster than packetsize()"
    4 UINT pos "position within file, used as an event id"
    4 LGCALDATE start
    4 LGCALDATE end
    1 UINT repeat
    2 UINT daybitmap  "which days a weekly repeat event happens on"
    1 UINT { 'default': 0 } +pad2
    1 UINT alarmminutes  "a value of 100 indicates not set"
    1 UINT alarmhours    "a value of 100 indicates not set"
    1 UINT alarmtype    "preset alarm reminder type"
    1 UINT { 'default': 0 } +snoozedelay   "in minutes, not for this phone"
    1 UINT ringtone
    39 USTRING {'raiseontruncate': False } description

PACKET schedulefile:
    2 UINT numactiveitems
    * LIST {'elementclass': scheduleevent} +events

PACKET call:
    4 GPSDATE GPStime #no. of seconds since 0h 1-6-80, based off local time.
    4 UINT unknown1 # different for each call
    4 UINT duration #seconds, not certain about length of this field
    49 USTRING {'raiseonunterminatedread': False} number
    36 USTRING {'raiseonunterminatedread': False} name
    1 UINT numberlength # length of phone number
    1 UINT unknown2 # set to 1 on some calls
    1 UINT pbnumbertype # 1=cell, 2=home, 3=office, 4=cell2, 5=fax, 6=vmail, 0xFF=not in phone book
    2 UINT unknown3 # always seems to be 0
    1 UINT pbentrynum #entry number in phonebook

PACKET callhistory:
    4 UINT numcalls
    1 UINT unknown1
    * LIST {'elementclass': call} +calls

###
### SMS 
###
#
#   There are 3 types of SMS records, The inbox, outbox and unsent (pending)
#   Unlike other records in the phone each message is stored in a separate file
#   All messages are in the 'sms' directory in the root of the phone
#   Inbox messages are in files called 'inbox000.dat', the number 000 varies for
#   each message, typically there are no gaps in the numbering, but gaps can appear
#   if a message is deleted.
#   Outbox message are named 'outbox000.dat', unsent messages are named 'sf00.dat',
#   only two digit file name that suggests a max of 100 message for this type.
#   Messages in the outbox get updated when the message is received by the recipient,
#   they contain a delivery flag and a delivery time for all the possible 10 recipients.
#   The vx8100 supports SMS contatination, this allows you to send text messages that are
#   longer than 160 characters. The format is different for these type of messages, but
#   it is supported by this implementation.
#   The vx8100 also allows you to put small graphics, sounds and animations in a message.
#   This implementation does not support these, if they are contained in a message they
#   will be ignored and just the text will be shown when you view the message in bitpim.
#   The text in the the messages is stored in 7-bit characters, so they have
#   to be unpacked, in concatinated messages and messages with embeded graphics etc. the
#   format uses the GSM 03.38 specified format, a good example of this can be found at
#   "http://www.dreamfabric.com/sms/hello.html".
#   For simple messages less than 161 characters with no graphics the format is simpler, 
#   the 7-bit characters are just packed into memory in the order they appear in the
#   message.

PACKET msg_record:
    # the first few fields in this packet have something to do with the type of SMS
    # message contained. EMS and concatinated text are coded differently than a
    # simple text message
    1 UINT unknown1 # 0
    1 UINT binary   # 0=simple text, 1=binary/concatinated
    1 UINT unknown3 # 0=simple text, 1=binary/concatinated
    1 UINT unknown4 # 0
    1 UINT unknown6 # 2=simple text, 9=binary/concatinated
    1 UINT length
    * LIST {'length': 219} +msg:
        1 UINT byte "individual byte of message"

PACKET recipient_record:
    2 UINT unknown1
    49 USTRING number
    1 UINT status   # 1 when sent, 5 when received, 2 failed to send
    4 LGCALDATE timesent
    4 LGCALDATE timereceived
    8 DATA unknown2

PACKET sms_saved:
    4 UINT outboxmsg
    4 UNKNOWN pad # used for GPStime on some phones
    if self.outboxmsg:
        * sms_out outbox
    if not self.outboxmsg:
        * sms_in inbox

PACKET sms_out:
    4 UINT index # starting from 1, unique
    1 UINT locked # 1=locked
    3 UINT unknown1 # zero
    4 LGCALDATE timesent # time the message was sent
    21 USTRING subject
    151 DATA unknown2
    1 UINT num_msg_elements # up to 10
    * LIST {'elementclass': msg_record, 'length': 10} +messages
    1 UINT unknown5
    1 UINT priority # 0=normal, 1=high
    14 DATA unknown7
    49 USTRING callback 
    * LIST {'elementclass': recipient_record,'length': 10} +recipients 

PACKET SMSINBOXMSGFRAGMENT:
    * LIST {'length': 181} +msg: # this size could be wrong
        1 UINT byte "individual byte of message"

PACKET sms_in:
    4 UINT msg_index1
    4 UINT msg_index2 # equal to the numerical part of the filename eg inbox002.dat
    2 UINT unknown2 # set to 0 for simple message and 3 for binary, 9 for page
    4 UINT unknown3 # set to 0
    6 SMSDATE timesent
    3 UINT unknown
    1 UINT callback_length # 0 for no callback number
    38 USTRING callback
    1 UINT sender_length
    * LIST {'length': 38} +sender:
        1 UINT byte "individual byte of senders phone number"
    15 DATA unknown4 # set to zeros
    4 LGCALDATE lg_time # time the message was sent
    4 GPSDATE GPStime # num seconds since 0h 1-6-80, time message received by phone
    2 UINT unknown5 # zero
    1 UINT read # 1 if message has been read, 0 otherwise
    1 UINT locked # 1 if the message is locked, 0 otherwise
    2 UINT unknown8 # zero
    1 UINT priority # 1 if the message is high priority, 0 otherwise
    5 DATA flags # message flags, read, priority, locked etc
    21 USTRING subject
    1 UINT bin_header1 # 0 in simple message 1 if the message contains a binary header
    1 UINT bin_header2 # 0 in simple message 9 if the message contains a binary header
    2 UINT unknown6 # zeros
    2 UINT multipartID # multi-part message ID, used for concatinated messages only
    1 UINT bin_header3 # 0 in simple message 2 if the message contains a binary header
    1 UINT num_msg_elements # max 10 elements (guessing on max here)
    * LIST {'length': 10} +msglengths:
        1 UINT msglength "lengths of individual messages in septets"
    * LIST {'length': 10, 'elementclass': SMSINBOXMSGFRAGMENT} +msgs 
                # 181 bytes per message, uncertain on this, no multipart message available
                # 20 messages, 7-bit ascii for simple text. for binary header 
                # first byte is header length not including the length byte
                # rest depends on content of header, not known at this time.
                # text alway follows the header although the format it different
                # than a simple SMS
    437 DATA unknown5
    33 USTRING senders_name
    169 DATA unknown6   # ?? inlcudes senders phone number in ascii

PACKET sms_quick_text:
# the vi125 has variable length NULL terminated strings null terminated in it's canned messages
# file sms/mediacan000.dat, not sure about the max
    * LIST {} +msgs:
        * USTRING {} msg #


