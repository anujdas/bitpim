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
Communicate with the LG VX9200 cell phone.
"""

# BitPim modules
import common
import com_brew
import prototypes
import com_lgvx11000
import p_lgvx9200
import helpids
import sms

#-------------------------------------------------------------------------------
parentphone=com_lgvx11000.Phone
class Phone(parentphone):
    desc="LG-VX9200 (enV3)"
    helpid=helpids.ID_PHONE_LGVX9200
    protocolclass=p_lgvx9200
    serialsname='lgvx9200'

    my_model='VX9200'
    builtinringtones= ('Low Beep Once', 'Low Beeps', 'Loud Beep Once', 'Loud Beeps', 'Door Bell', 'VZW Default Tone') + \
                      tuple(['Ringtone '+`n` for n in range(1,17)]) + ('No Ring',)

    def setDMversion(self):
        self._DMv5=False
        self._DMv6=True
        self._timeout=5 # Assume a quick timeout on newer phones

    #  - getgroups           - same as LG VX-8700
    #  - getwallpaperindices - LGUncountedIndexedMedia
    #  - getringtoneindices  - LGUncountedIndexedMedia
    #  - DM Version          - 6
    #  - phonebook           - LG Phonebook v1 Extended
    #  - SMS                 - same dir structure as the VX-8800, modified file structure

    def _getoutboxmessage(self, sf):
        entry=sms.SMSEntry()
        entry.folder=entry.Folder_Sent
        entry.datetime="%d%02d%02dT%02d%02d00" % sf.timesent[:5]
        # add all the recipients
        for r in sf.recipients:
            if r.number:
                confirmed=(r.status==5)
                confirmed_date=None
                if confirmed:
                    confirmed_date="%d%02d%02dT%02d%02d00" % r.timereceived
                entry.add_recipient(r.number, confirmed, confirmed_date, r.name)
        entry.subject=sf.subject
        txt=""
        if sf.num_msg_elements==1 and not sf.messages[0].binary:
            txt=self._get_text_from_sms_msg_without_header(sf.messages[0].msg, sf.messages[0].length)
        else:
            for i in range(sf.num_msg_elements):
                txt+=self._get_text_from_sms_msg_with_header(sf.messages[i].msg, sf.messages[i].length)
        entry.text=unicode(txt, errors='ignore')
        if sf.priority==0:
            entry.priority=sms.SMSEntry.Priority_Normal
        else:
            entry.priority=sms.SMSEntry.Priority_High
        entry.locked=sf.locked
        entry.callback=sf.callback
        return entry

    def _getinboxmessage(self, sf):
        entry = sms.SMSEntry()
        entry.folder = entry.Folder_Inbox
        entry.datetime = "%d%02d%02dT%02d%02d%02d" % sf.GPStime
        entry.read = bool(sf.read)
        entry.locked = bool(sf.locked)
        entry.priority = sms.SMSEntry.Priority_High if sf.priority else sms.SMSEntry.Priority_Normal
        entry._from = sf.sender if sf.sender else sf.sender_name
        entry.callback = sf.callback
        entry.subject = self._decode_subject(sf.subject, sf.encoding).encode('utf-8')

        msgs = sf.msgs[0:sf.num_msg_fragments]
        has_udh = sf.has_udh == 2
        entry.text = self._decode_msg(msgs, sf.encoding, has_udh).encode('utf-8')

        return entry

    # encodings:
    # - 0x04 - UTF-16BE
    # - 0x08 - ISO-8859-1
    def _decode_subject(self, subject, encoding):
        if encoding == 0x04:
            return self._decode_ucs16(subject).rstrip('\x00')
        else:
            return self._decode_ascii(subject).rstrip('\x00')

    # encodings:
    # - 0x02 - 7-bit
    # - 0x04 - UTF-16BE
    # - 0x08 - ISO-8859-1
    # - 0x09 - multipart-GSM-07?
    def _decode_msg(self, msgs, encoding, has_udh):
        fragments = ""
        for m in msgs:
            if encoding == 0x02:
                fragments += self._decode_septets(m.msg_data.msg, m.msg_length)
            elif encoding == 0x09:
                fragments += self._decode_septets_with_udh(m.msg_data.msg, m.msg_length)
            else:
                msg_start = m.msg_data.msg[0].byte + 1 if has_udh else 0
                msg = m.msg_data.msg[msg_start:m.msg_length]
                if encoding == 0x04:
                    fragments += self._decode_ucs16(msg)
                elif encoding == 0x08:
                    fragments += self._decode_ascii(msg)

        return fragments #.encode('utf-8', errors='ignore')

    def _udh_len(self, msg):
        return msg[0].byte + 1  # byte 0 is the header length in bytes, not including itself

    def _decode_septets(self, txt, num_septets):
        out = bytearray(num_septets)
        for i in range(num_septets):
            tmp = (txt[(i * 7) / 8].byte << 8) | txt[((i * 7) / 8) + 1].byte
            bit_index = 9 - ((i * 7) % 8)
            out[i] = (tmp >> bit_index) & 0x7f
        return out.decode('ascii')

    def _decode_septets_with_udh(self, msg, num_septets):
        # reverse every seven byte chunk before decoding septets
        reordered = []
        for i in range(0, (num_septets * 7) / 8 + 8, 7):
            reordered += reversed(msg[i:i + 7])

        # extract the 7-bit chars into bytes
        septets = self._decode_septets(reordered, num_septets + 7).encode('ascii')

        # correct the byte order and strip the UDH off the message
        out = bytearray(num_septets - 7)
        for i in range(0, num_septets + 7, 8):
            for j in range(8):
                if 0 <= i - j < num_septets - 7:
                    out[i - j] = septets[i + j]

        return out.decode('ascii')

    def _decode_ascii(self, txt):
        return bytearray(b.byte for b in txt).decode('ascii')

    def _decode_ucs16(self, txt):
        return bytearray(b.byte for b in txt).decode('utf-16be')

#-------------------------------------------------------------------------------
parentprofile=com_lgvx11000.Profile
class Profile(parentprofile):
    BP_Calendar_Version=3

    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname
    phone_model=Phone.my_model
    phone_manufacturer='LG Electronics Inc'

    # inside screen resoluation
    WALLPAPER_WIDTH  = 320
    WALLPAPER_HEIGHT = 240

    imageorigins={}
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "video"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images(sd)"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "video(sd)"))

    # our targets are the same for all origins
    imagetargets={}
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "outsidelcd",
                                      {'width': 190, 'height': 96, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "wallpaper",
                                      {'width': 320, 'height': 240, 'format': "JPEG"}))
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
        ('t9_udb', 'write', 'OVERWRITE'),
        )
    if __debug__:
        _supportedsyncs+=(
        ('t9_udb', 'read', 'OVERWRITE'),
        )
