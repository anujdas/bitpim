### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$

"""Communicate with the LG VX4400 cell phone"""

# standard modules
import re
import time
import cStringIO
import sha

# my modules
import common
import commport
import copy
import p_lgvx4400
import com_brew
import com_phone
import com_lg
import prototypes



### default groups
##        self.groupdict={0: {'name': 'No Group', 'icon': 0}, 1: {'name': 'Family', 'icon': 1},
##                        2: {'name': 'Friends', 'icon': 2}, 3: {'name': 'Colleagues', 'icon': 3},
##                        4: {'name': 'Business', 'icon': 4}, 5: {'name': 'School', 'icon': 5}, }


numbertypetab=( 'home', 'home2', 'office', 'office2', 'cell', 'cell2',
                    'pager', 'fax', 'fax2', 'none' )

        
class Phone(com_phone.Phone,com_brew.BrewProtocol,com_lg.LGPhonebook):
    "Talk to the LG VX4400 cell phone"

    desc="LG-VX4400"
    
    def __init__(self, logtarget, commport):
        com_phone.Phone.__init__(self, logtarget, commport)
	com_brew.BrewProtocol.__init__(self)
        com_lg.LGPhonebook.__init__(self)
        self.log("Attempting to contact phone")
        self.mode=self.MODENONE

    def getfundamentals(self, results):
        """Gets information fundamental to interopating with the phone and UI.

        Currently this is:

          - 'uniqueserial'     a unique serial number representing the phone
          - 'groups'           the phonebook groups
          - 'wallpaper-index'  map index numbers to names
          - 'ringtone-index'   map index numbers to ringtone names
        """

        # use a hash of ESN and other stuff (being paranoid)
        self.log("Retrieving fundamental phone information")
        self.log("Phone serial number")
        results['uniqueserial']=sha.new(self.getfilecontents("nvm/$SYS.ESN")).hexdigest()
        # now read groups
        self.log("Reading group information")
        buf=prototypes.buffer(self.getfilecontents("pim/pbgroup.dat"))
        g=p_lgvx4400.pbgroups()
        g.readfrombuffer(buf)
        self.logdata("Groups read", buf.getdata(), g)
        groups={}
        for i in range(g.numgroups):
            groups[i]={ 'icon': g.groups[i].icon, 'name': g.groups[i].name }
        results['groups']=groups
        # wallpaper index
        self.log("Reading wallpaper indices")
        results['wallpaper-index']=self.getindex('dloadindex/brewImageIndex.map')
        # ringtone index
        self.log("Reading ringtone indices")
        results['ringtone-index']=self.getindex('dloadindex/brewRingerIndex.map')
        self.log("Fundamentals retrieved")
        return results
        
    def getphonebook(self,result):
        pbook={}
        # Bug in the phone.  if you repeatedly read the phone book it starts
        # returning a random number as the number of entries.  We get around
        # this by switching into brew mode which clears that.
        self.mode=self.MODENONE
        self.setmode(self.MODEBREW)
        self.log("Reading number of phonebook entries")
        req=p_lgvx4400.pbinforequest()
        res=self.sendpbcommand(req, p_lgvx4400.pbinforesponse)
        numentries=res.numentries
        self.log("There are %d entries" % (numentries,))
        for i in range(0, numentries):
            ### Read current entry
            req=p_lgvx4400.pbreadentryrequest()
            res=self.sendpbcommand(req, p_lgvx4400.pbreadentryresponse)
            self.log("Read entry "+`i`+" - "+res.entry.name)
            entry=self.extractphonebookentry(res.entry, result)
            pbook[i]=entry 
            self.progress(i, numentries, res.entry.name)
            #### Advance to next entry
            req=p_lgvx4400.pbnextentryrequest()
            self.sendpbcommand(req, p_lgvx4400.pbnextentryresponse)

        self.progress(numentries, numentries, "Phone book read completed")
        result['phonebook']=pbook
        return pbook

    def savephonebook(self, data):
        # To write the phone book, we scan through all existing entries
        # and record their record number and serials.
        # We then delete any entries that aren't in data
        # We then write out our records, usng overwrite or append
        # commands as necessary
        newphonebook={}
        existingpbook={} # keep track of the phonebook that is on the phone
        self.mode=self.MODENONE
        self.setmode(self.MODEBREW) # see note in getphonebook() for why this is necessary
        self.setmode(self.MODEPHONEBOOK)
        # similar loop to reading
        req=p_lgvx4400.pbinforequest()
        res=self.sendpbcommand(req, p_lgvx4400.pbinforesponse)
        numexistingentries=res.numentries
        progressmax=numexistingentries+len(data['phonebook'].keys())
        progresscur=0
        self.log("There are %d existing entries" % (numexistingentries,))
        for i in range(0, numexistingentries):
            ### Read current entry
            req=p_lgvx4400.pbreadentryrequest()
            res=self.sendpbcommand(req, p_lgvx4400.pbreadentryresponse)
            
            entry={ 'number':  res.entry.entrynumber, 'serial1':  res.entry.serial1,
                    'serial2': res.entry.serial2, 'name': res.entry.name}
            assert entry['serial1']==entry['serial2'] # always the same
            self.log("Reading entry "+`i`+" - "+entry['name'])            
            existingpbook[i]=entry 
            self.progress(progresscur, progressmax, "existing "+entry['name'])
            #### Advance to next entry
            req=p_lgvx4400.pbnextentryrequest()
            self.sendpbcommand(req, p_lgvx4400.pbnextentryresponse)
            progresscur+=1
        # we have now looped around back to begining

        # Find entries that have been deleted
        pbook=data['phonebook']
        dellist=[]
        for i in range(0, numexistingentries):
            ii=existingpbook[i]
            serial=ii['serial1']
            item=self._findserial(serial, pbook)
            if item is None:
                dellist.append(i)

        progressmax+=len(dellist) # more work to do

        # Delete those entries
        for i in dellist:
            progresscur+=1
            numexistingentries-=1  # keep count right
            ii=existingpbook[i]
            self.log("Deleting entry "+`i`+" - "+ii['name'])
            req=p_lgvx4400.pbdeleteentryrequest()
            req.serial1=ii['serial1']
            req.serial2=ii['serial2']
            req.entrynumber=ii['number']
            self.sendpbcommand(req, p_lgvx4400.pbdeleteentryresponse)
            self.progress(progresscur, progressmax, "Deleting "+ii['name'])
            # also remove them from existingpbook
            del existingpbook[i]

        # counter to keep track of record number (otherwise appends don't work)
        counter=0
        # Now rewrite out existing entries
        keys=existingpbook.keys()
        existingserials=[]
        keys.sort()  # do in same order as existingpbook
        for i in keys:
            progresscur+=1
            ii=pbook[self._findserial(existingpbook[i]['serial1'], pbook)]
            self.log("Writing entry "+`i`+" - "+ii['name'])
            self.progress(progresscur, progressmax, "Writing "+ii['name'])
            entry=self.makeentry(counter, ii, data)
            counter+=1
            existingserials.append(existingpbook[i]['serial1'])
            req=p_lgvx4400.pbupdateentryrequest()
            req.entry=entry
            res=self.sendpbcommand(req, p_lgvx4400.pbupdateentryresponse)
            newphonebook[counter-1]=self.extractphonebookentry(entry, data)
            assert ii['serial1']==res.serial1 # serial should stay the same

        # Finally write out new entries
        keys=pbook.keys()
        keys.sort()
        for i in keys:
            ii=pbook[i]
            if ii['serial1'] in existingserials:
                continue # already wrote this one out
            progresscur+=1
            entry=self.makeentry(counter, ii, data)
            counter+=1
            self.log("Appending entry "+ii['name'])
            self.progress(progresscur, progressmax, "Writing "+ii['name'])
            req=p_lgvx4400.pbappendentryrequest()
            req.entry=entry
            res=self.sendpbcommand(req, p_lgvx4400.pbappendentryresponse)
            entry.serial1=res.newserial
            entry.serial2=res.newserial
            newphonebook[counter-1]=self.extractphonebookentry(entry, data)

        data['phonebook']=newphonebook


    def _findserial(self, serial, dict):
        """Searches dict to find entry with matching serial.  If not found,
        returns None"""
        for i in dict:
            if dict[i]['serial1']==serial:
                return i
        return None
            
    def getcalendar(self,result):
        res={}
        # Read exceptions file first
        buf=prototypes.buffer(self.getfilecontents("sch/schexception.dat"))
        ex=p_lgvx4400.scheduleexceptionfile()
        ex.readfrombuffer(buf)
        self.logdata("Calendar exceptions", buf.getdata(), ex)
        exceptions={}
        for i in ex.items:
            try:
                exceptions[i.pos].append( (i.year,i.month,i.day) )
            except KeyError:
                exceptions[i.pos]=[ (i.year,i.month,i.day) ]

        # Now read schedule
        buf=prototypes.buffer(self.getfilecontents("sch/schedule.dat"))
        sc=p_lgvx4400.schedulefile()
        sc.readfrombuffer(buf)
        self.logdata("Calendar", buf.getdata(), sc)
        for event in sc.events:
            entry={}
            entry['pos']=event.pos
            if entry['pos']==-1: continue # blanked entry
            # normal fields
            for field in 'start','end','daybitmap','changeserial','snoozedelay','ringtone','description':
                entry[field]=getattr(event,field)
            # calculated ones
            entry['repeat']=self._calrepeatvalues[event.repeat]
            min=event.alarmminutes
            hour=event.alarmhours
            if min==100 or hour==100:
                entry['alarm']=None # no alarm set
            else:
                entry['alarm']=hour*60+min
            # Exceptions
            if exceptions.has_key(event.pos):
                entry['exceptions']=exceptions[event.pos]
            res[event.pos]=entry

        assert sc.numactiveitems==len(res)
        result['calendar']=res
        return result

    def savecalendar(self, dict, merge):
        # ::TODO:: obey merge param
        # what will be written to the files
        eventsf=p_lgvx4400.schedulefile()
        exceptionsf=p_lgvx4400.scheduleexceptionfile()

        # what are we working with
        cal=dict['calendar']
        newcal={}
        keys=cal.keys()
        keys.sort()

        # number of entries
        eventsf.numactiveitems=len(keys)
        
        # play with each entry
        for k in keys:
            # entry is what we will return to user
            entry=cal[k]
            data=p_lgvx4400.scheduleevent()
            data.pos=eventsf.packetsize()
            entry['pos']=data.pos
            # simple copy of these fields
            for field in 'start', 'end', 'daybitmap', 'changeserial', 'snoozedelay','ringtone','description':
                setattr(data,field,entry[field])
            # And now the special ones
            repeat=None
            for k,v in self._calrepeatvalues.items():
                if entry['repeat']==v:
                    repeat=k
                    break
            assert repeat is not None
            data.repeat=repeat
            # alarm 100 indicates not set
            if entry['alarm'] is None or entry['alarm']<0:
                hour=100
                min=100
            else:
                assert entry['alarm']>=0
                hour=entry['alarm']/60
                min=entry['alarm']%60
            data.alarmminutes=min
            data.alarmhours=hour

            # update exceptions if needbe
            if entry.has_key('exceptions'):
                for y,m,d in entry['exceptions']:
                    de=p_lgvx4400.scheduleexception()
                    de.pos=data.pos
                    de.day=d
                    de.month=m
                    de.year=y
                    exceptionsf.items.append(de)

            # put entry in nice shiny new dict we are building
            entry=copy.copy(entry)
            newcal[data.pos]=entry
            eventsf.events.append(data)

        # scribble everything out
        buf=prototypes.buffer()
        eventsf.writetobuffer(buf)
        self.logdata("Writing calendar", buf.getvalue(), eventsf)
        self.writefile("sch/schedule.dat", buf.getvalue())
        buf=prototypes.buffer()
        exceptionsf.writetobuffer(buf)
        self.logdata("Writing calendar exceptions", buf.getvalue(), exceptionsf)
        self.writefile("sch/schexception.dat", buf.getvalue())

        # fix passed in dict
        dict['calendar']=newcal

        return dict
        

    _calrepeatvalues={
        0x10: None,
        0x11: 'daily',
        0x12: 'monfri',
        0x13: 'weekly',
        0x14: 'monthly',
        0x15: 'yearly'
        }
    
    def writeindex(self, indexfile, index, maxentries=30):
        keys=index.keys()
        keys.sort()
        writing=min(len(keys), maxentries)
        if len(keys)>maxentries:
            self.log("Warning:  You have too many entries (%d) for index %s.  Only writing out first %d." % (len(keys), indexfile, writing))
        ifile=p_lgvx4400.indexfile()
        ifile.maxitems=writing
        for i in keys[:writing]:
            entry=p_lgvx4400.indexentry()
            entry.index=i
            entry.name=index[i]
            ifile.items.append(entry)
        buf=prototypes.buffer()
        ifile.writetobuffer(buf)
        self.logdata("Writing %d index entries to %s" % (writing,indexfile), buf.getvalue(), ifile)
        self.writefile(indexfile, buf.getvalue())

    def getindex(self, indexfile):
        "Read an index file"
        index={}
        buf=prototypes.buffer(self.getfilecontents(indexfile))
        g=p_lgvx4400.indexfile()
        g.readfrombuffer(buf)
        self.logdata("Index file %s read with %d entries" % (indexfile,g.numactiveitems), buf.getdata(), g)
        for i in range(g.maxitems):
            if g.items[i].index!=0xffff:
                index[g.items[i].index]=g.items[i].name
        return index
        
    def getprettystuff(self, result, directory, datakey, indexfile, indexkey):
        """Get wallpaper/ringtone etc"""
        # we have to be careful because files from other stuff could be
        # in the directory.  Consequently we ONLY consult the index.  However
        # the index may be corrupt so we cope with it having entries for
        # files that don't exist
        index=self.getindex(indexfile)
        result[indexkey]=index

        stuff={}
        for i in index:
            try:
                file=self.getfilecontents(directory+"/"+index[i])
                stuff[index[i]]=file
            except com_brew.BrewNoSuchFileException:
                self.log("It was in the index, but not on the filesystem")
        result[datakey]=stuff

        return result

    def getwallpapers(self, result):
        return self.getprettystuff(result, "brew/shared", "wallpaper", "dloadindex/brewImageIndex.map",
                                   "wallpaper-index")

    def saveprettystuff(self, data, directory, indexfile, stuffkey, stuffindexkey, merge):
        f=data[stuffkey].keys()
        f.sort()
        self.log("Saving %s.  Merge=%d.  Files supplied %s" % (stuffkey, merge, ", ".join(f)))
        self.mkdirs(directory)

        # get existing index
        index=self.getindex(indexfile)

        # Now the only files we care about are those named in the index and in data[stuffkey]
        # The operations below are specially ordered so that we don't reuse index keys
        # from existing entries (even those we are about to delete).  This seems like
        # the right thing to do.

        # Get list of existing files
        entries=self.getfilesystem(directory)

        # if we aren't merging, delete all files in index we aren't going to overwrite
        # we do this first to make space for new entrants
        if not merge:
            for i in index:
                if self._fileisin(entries, index[i]) and index[i] not in data[stuffkey]:
                    fullname=directory+"/"+index[i]
                    self.rmfile(fullname)
                    del entries[fullname]

        # Write out the files
        files=data[stuffkey]
        keys=files.keys()
        keys.sort()
        for file in keys:
            fullname=directory+"/"+file
            self.writefile(fullname, files[file])
            entries[fullname]={'name': fullname}
                    
        # Build up the index
        for i in files:
            # entries in the existing index take priority
            if self._getindexof(index, i)<0:
                # Look in new index
                num=self._getindexof(data[stuffindexkey], i)
                if num<0 or num in index: # if already in index, allocate new one
                    num=self._firstfree(index, data[stuffindexkey])
                assert not index.has_key(num)
                index[num]=i

        # Delete any duplicate index entries, keeping lowest numbered one
        seen=[]
        keys=index.keys()
        keys.sort()
        for i in keys:
            if index[i] in seen:
                del index[i]
            else:
                seen.append( index[i] )

        # Verify all index entries are present
        for i in index.keys():
            if not self._fileisin(entries, index[i]):
                del index[i]

        # Write out index
        self.writeindex(indexfile, index)

        data[stuffindexkey]=index
        return data


    def savewallpapers(self, data, merge):
        return self.saveprettystuff(data, "brew/shared", "dloadindex/brewImageIndex.map",
                                    'wallpaper', 'wallpaper-index', merge)
        
    def saveringtones(self,data, merge):
        return self.saveprettystuff(data, "user/sound/ringer", "dloadindex/brewRingerIndex.map",
                                    'ringtone', 'ringtone-index', merge)


    def _fileisin(self, entries, file):
        # see's if file is in entries (entries has full pathname, file is just filename)
        for i in entries:
            if com_brew.brewbasename(entries[i]['name'])==file:
                return True
        return False

    def _getindexof(self, index, file):
        # gets index number of file from index
        for i in index:
            if index[i]==file:
                return i
        return -1

    def _firstfree(self, index1, index2):
        # finds first free index number taking into account both indexes
        l=index1.keys()
        l.extend(index2.keys())
        for i in range(0,255):
            if i not in l:
                return i
        return -1

    def getringtones(self, result):
        return self.getprettystuff(result, "user/sound/ringer", "ringtone", "dloadindex/brewRingerIndex.map",
                                   "ringtone-index")

    def extractphonebookentry(self, entry, fundamentals):
        """Return a phonebook entry in BitPim format"""
        res={}
        # serials
        res['serials']=[ {'sourcetype': 'lgvx4400', 'serial1': entry.serial1, 'serial2': entry.serial2,
                          'sourceuniqueid': fundamentals['uniqueserial']} ] 
        # only one name
        res['names']=[ {'full': entry.name} ]
        # only one category
        res['categories']=[ {'category': entry.group} ] # ::TODO:: turn this into string
        # emails
        res['emails']=[]
        for i in entry.emails:
            if len(i.email):
                res['emails'].append( {'email': i.email} )
        # urls
        res['urls']=[ {'url': entry.url} ]
        # ringtones
        res['ringtones']=[ {'ringtone': entry.ringtone, 'use': 'call'},
                           {'ringtone': entry.msgringtone, 'use': 'message' } ] # ::TODO:: turn these into strings
        # private
        res['flags']=[ {'secret': entry.secret } ]
        # memos
        res['memos']=[ {'memo': entry.memo } ]
        # wallpapers
        res['wallpapers']=[ {'wallpaper': entry.wallpaper, 'use': 'call'} ]
        # numbers
        res['numbers']=[]
        for i in range(entry.numberofphonenumbers):
            num=entry.numbers[i].number
            type=entry.numbertypes[i].numbertype
            if len(num):
                res['numbers'].append({'number': num, 'type': numbertypetab[type]})
        return res
                    
    def makeentry(self, counter, entry, dict):
        # dict is unused at moment, will be used later to convert string ringtone/wallpaper to numbers
        e=p_lgvx4400.pbentry()
        e.entrynumber=counter
        
        for k in entry:
            # special treatment for lists
            if k=='emails' or k=='numbers' or k=='numbertypes':
                l=getattr(e,k)
                for item in entry[k]:
                    if k=='numbers':
                        item=self.phonize(item)
                    l.append(item)
                continue
            # everything else we just set
            setattr(e,k,entry[k])

        return e

            
    def phonize(self, str):
        """Convert the phone number into something the phone understands

        All digits, P, T, * and # are kept, everything else is removed"""
        return re.sub("[^0-9PT#*]", "", str)

    
    tonetab=( 'Default', 'Ring 1', 'Ring 2', 'Ring 3', 'Ring 4', 'Ring 5',
              'Ring 6', 'Voices of Spring', 'Twinkle Twinkle',
              'The Toreadors', 'Badinerie', 'The Spring',
              'Liberty Bell', 'Trumpet Concerto', 'Eine Kleine',
              'Silken Ladder', 'Nocturne', 'Csikos Post', 'Turkish March',
              'Mozart Aria', 'La Traviata', 'Rag Time', 'Radetzky March',
              'Can-Can', 'Sabre Dance', 'Magic Flute', 'Carmen' )

class Profile:

    def makeone(self, list, default):
        "Returns one item long list"
        if len(list)==0:
            return default
        assert len(list)==1
        return list[0]

    def filllist(self, list, numitems, blank):
        "makes list numitems long appending blank to get there"
        l=list[:]
        for dummy in range(len(l),numitems):
            l.append(blank)
        return l

    def convertphonebooktophone(self, helper, data):
        "Converts the data to what will be used by the phone"
        results={}

        for pbentry in data['phonebook']:
            e={} # entry out
            entry=data['phonebook'][pbentry] # entry in
            try:
                e['name']=helper.getfullname(entry['names'],1,1,22)[0]

                e['group']=self.makeone(helper.getcategory(entry['categories'],0,1), 0)

                e['emails']=self.filllist(helper.getemails(entry['emails'],0,3,48), 3, "")

                e['url']=self.makeone(helper.geturls(entry['urls'], 0,1,48), "")

                e['memo']=self.makeone(helper.getmemos(entry['memos'], 0, 1, 32), "")

                numbers=helper.getnumbers(entry['numbers'],1,5)
                e['numbertypes']=[]
                e['numbers']=[]
                for num in numbers:
                    type=num['type']
                    for i,t in zip(range(100),numbertypetab):
                        if type==t:
                            e['numbertypes'].append(i)
                            break
                        if t=='none': # conveniently last entry
                            e['numbertypes'].append(i)
                            break
                    e['numbers'].append(num['number'])
                e['numbertypes']=self.filllist(e['numbertypes'], 5, 0)
                e['numbers']=self.filllist(e['numbers'], 5, "")

                serial1=helper.getserial(entry['serials'], 'lgvx4400', data['uniqueserial'], 'serial1', 0)
                serial2=helper.getserial(entry['serials'], 'lgvx4400', data['uniqueserial'], 'serial2', serial1)

                e['serial1']=serial1
                e['serial2']=serial2
                
                e['ringtone']=helper.getringtone(entry['ringtones'], 'call', 0)
                e['msgringtone']=helper.getringtone(entry['ringtones'], 'message', 0)

                e['wallpaper']=helper.getwallpaper(entry['wallpapers'], 'call', 0)

                e['secret']=helper.getflag(entry['flags'], 'secret', False)

                results[pbentry]=e
                
            except helper.ConversionFailed:
                continue

        data['phonebook']=results
        return data
