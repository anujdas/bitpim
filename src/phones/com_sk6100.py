### BITPIM
###
### Copyright (C) 2005 Yosef Meller <mellerf@netvision.net.il>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

import com_phone
import com_brew
import prototypes
import p_sk6100

class Phone(com_phone.Phone, com_brew.BrewProtocol):
    """Talk to SK Music Slider"""
	
    desc="SK Music Slider"
    protocolclass=p_sk6100
    serialsname='sk6100'
	
    # This is ordered by the type id nums the phone uses:
    phonetypes = [ 'cell', 'home', 'office', 'fax' ]
	
    def __init__(self, logtarget, commport):
        com_phone.Phone.__init__(self, logtarget, commport)
        com_brew.BrewProtocol.__init__(self)
	
    def getfundamentals(self, results):
        grbuf = prototypes.buffer(self.getfilecontents('SKY/PBK/group.pbk'))
        groups = self.protocolclass.groups()
        groups.readfrombuffer(grbuf)
        self.logdata("Groups read", grbuf.getdata(), groups)
		
        # decode caharachters to unicode - should use some global setting,
        # hard-coding is bad for you :-)
        grsort = [group for group in groups.pbgroups if group.name != '']
		
        results['groups'] = grsort
        return results
	
    def getphonebook(self, results):
        encoding = 'iso-8859-8' # Should be some global setting
		
        # Get a list of phone numbers:
        phonebuf = prototypes.buffer(self.getfilecontents('SKY/PBK/number.pbk'))
        phones = self.protocolclass.phones()
        phones.readfrombuffer(phonebuf)
		
        # Drop empty phone records, listify:
        phones = [phone for phone in phones.records if phone.owner_id]
		
        # Retrieve people names and groups
        pbook={}
        bookbuf = prototypes.buffer(self.getfilecontents('SKY/PBK/book.pbk'))
        entries = self.protocolclass.wholebook()
        entries.readfrombuffer(bookbuf)
        self.logdata("Names read", bookbuf.getdata(), entries)
		
        for entry in entries.pbentries:
            # Ignore deleted records
            if not entry.record:
                continue
			
            # Find group name:
            group_name = "Group not recognised"
            for group in results['groups']:
                if group.group_id == entry.group_id:
                    group_name = group.name.decode(encoding)
                    break
			
            pbook[entry.slot] = {
                'names': [{'title': '', 'first': '', 
                           'last': '', 'full': entry.name.decode(encoding), 'nickname': ''}],
                'categories': [{'category': group_name}],
                'numbers': [{'number': phone.number, 
                             'type': self.phonetypes[phone.type - 1]}
                            for phone in phones 
                            if phone.owner_id == entry.slot],
            'serials': [{'sourcetype': self.serialsname}]
            }
		
        results['phonebook'] = pbook
        results['categories'] = [group.name.decode(encoding) for group in results['groups']]
        return pbook 
	
    def getcalendar(self, results):
        pass

    def getwallpapers(self, results):
        pass
	
    def getringtones(self, results):
        pass

class Profile(com_phone.Profile):
    deviceclasses=("modem",)
	
    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        )
	
