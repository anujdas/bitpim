### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Phonebook conversations with LG phones"""

import com_brew
import com_phone
import p_lg
import prototypes
import common

class LGPhonebook:

    pbterminator="\x7e"
    MODEPHONEBOOK="modephonebook" # can speak the phonebook protocol

    def __init__(self):
        self.pbseq=0
    
    def _setmodelgdmgo(self):
        # see if we can turn on dm mode
        for baud in (0, 115200, 19200, 38400, 230400):
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue
            try:
                self.comm.write("AT$LGDMGO\r\n")
            except:
                self.mode=self.MODENONE
                self.comm.shouldloop=True
                raise
            try:
                if self.comm.readsome().find("OK")>=0:
                    return True
            except com_phone.modeignoreerrortypes:
                self.log("No response to setting DM mode")
        return False
        

    def _setmodephonebook(self):
        req=p_lg.pbinitrequest()
        respc=p_lg.pbinitresponse

        for baud in 0,38400,115200,230400,19200:
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue
            try:
                self.sendpbcommand(req, respc, callsetmode=False)
                return True
            except com_phone.modeignoreerrortypes:
                pass

        self._setmodelgdmgo()

        for baud in 0,38400,115200:
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue
            try:
                self.sendpbcommand(req, respc, callsetmode=False)
                return True
            except com_phone.modeignoreerrortypes:
                pass
        return False
        
    def sendpbcommand(self, request, responseclass, callsetmode=True):
        if callsetmode:
            self.setmode(self.MODEPHONEBOOK)
        buffer=prototypes.buffer()
        request.header.sequence=self.pbseq
        self.pbseq+=1
        if self.pbseq>0xff:
            self.pbseq=0
        request.writetobuffer(buffer)
        data=buffer.getvalue()
        self.logdata("lg phonebook request", data, request)
        data=com_brew.escape(data+com_brew.crcs(data))+self.pbterminator
        firsttwo=data[:2]
        try:
            data=self.comm.writethenreaduntil(data, False, self.pbterminator, logreaduntilsuccess=False)
        except com_phone.modeignoreerrortypes:
            self.mode=self.MODENONE
            self.raisecommsdnaexception("manipulating the phonebook")
        self.comm.success=True

        origdata=data
        # sometimes there is junk at the begining, eg if the user
        # turned off the phone and back on again.  So if there is more
        # than one 7e in the escaped data we should start after the
        # second to last one
        d=data.rfind(self.pbterminator,0,-1)
        if d>=0:
            self.log("Multiple LG packets in data - taking last one starting at "+`d+1`)
            self.logdata("Original LG data", origdata, None)
            data=data[d+1:]

        # turn it back to normal
        data=com_brew.unescape(data)

        # sometimes there is other crap at the begining
        d=data.find(firsttwo)
        if d>0:
            self.log("Junk at begining of LG packet, data at "+`d`)
            self.logdata("Original LG data", origdata, None)
            self.logdata("Working on LG data", data, None)
            data=data[d:]
        # take off crc and terminator
        crc=data[-3:-1]
        data=data[:-3]
        if com_brew.crcs(data)!=crc:
            self.logdata("Original LG data", origdata, None)
            self.logdata("Working on LG data", data, None)
            raise common.CommsDataCorruption("LG packet failed CRC check", self.desc)
        
        # log it
        self.logdata("lg phonebook response", data, responseclass)

        # parse data
        buffer=prototypes.buffer(data)
        res=responseclass()
        res.readfrombuffer(buffer)
        return res

    # This function isn't actually used
    def getphoneinfo(self, results):
        "Extracts manufacturer and version information in modem mode"
        self.setmode(self.MODEMODEM)
        d={}
        self.progress(0,4, "Switching to modem mode")
        self.progress(1,4, "Reading manufacturer")
        self.comm.write("AT+GMI\r\n")  # manuf
        d['Manufacturer']=cleanupstring(self.comm.readsome())[2][6:]
        self.log("Manufacturer is "+d['Manufacturer'])
        self.progress(2,4, "Reading model")
        self.comm.write("AT+GMM\r\n")  # model
        d['Model']=cleanupstring(self.comm.readsome())[2][6:]
        self.log("Model is "+d['Model'])
        self.progress(3,4, "Software version")
        self.comm.write("AT+GMR\r\n")  # software revision
        d['Software']=cleanupstring(self.comm.readsome())[2][6:]
        self.log("Software is "+d['Software'])
        self.progress(4,4, "Done reading information")
        results['info']=d
        return results

def cleanupstring(str):
    str=str.replace("\r", "\n")
    str=str.replace("\n\n", "\n")
    str=str.strip()
    return str.split("\n")

class LGIndexedMedia:
    "Implements media for LG phones that use index files"
    
    def __init__(self):
        pass

    def getmediaindex(self, builtins, maps, results, key):
        """Gets the media (wallpaper/ringtone) index

        @param builtins: the builtin list on the phone
        @param results: places results in this dict
        @param maps: the list of index files and locations
        @param key: key to place results in
        """

        self.log("Reading "+key)
        media={}

        # builtins
        c=1
        for name in builtins:
            media[c]={'name': name, 'origin': 'builtin' }
            c+=1

        # the maps
        type=None
        for offset,indexfile,location,type,maxentries in maps:
            if type=="camera": break
            index=self.getindex(indexfile)
            for i in index:
                media[i+offset]={'name': index[i], 'origin': type}

        # camera must be last
        if type=="camera":
            index=self.getcameraindex()
            for i in index:
                media[i+offset]=index[i]

        results[key]=media
        return media

    def getindex(self, indexfile):
        "Read an index file"
        index={}
        try:
            buf=prototypes.buffer(self.getfilecontents(indexfile))
        except com_brew.BrewNoSuchFileException:
            # file may not exist
            return index
        g=self.protocolclass.indexfile()
        g.readfrombuffer(buf)
        self.logdata("Index file %s read with %d entries" % (indexfile,g.numactiveitems), buf.getdata(), g)
        for i in g.items:
            if i.index!=0xffff:
                index[i.index]=i.name
        return index
        
    def getmedia(self, maps, result, key):
        """Returns the contents of media as a dict where the key is a name as returned
        by getindex, and the value is the contents of the media"""
        media={}
        # the maps
        type=None
        for offset,indexfile,location,type,maxentries in maps:
            if type=="camera": break
            index=self.getindex(indexfile)
            for i in index:
                try:
                    media[index[i]]=self.getfilecontents(location+"/"+index[i])
                except (com_brew.BrewNoSuchFileException,com_brew.BrewBadPathnameException):
                    self.log("It was in the index, but not on the filesystem")
                    
        if type=="camera":
            # now for the camera stuff
            index=self.getcameraindex()
            for i in index:
                try:
                    media[index[i]['name']]=self.getfilecontents("cam/pic%02d.jpg" % (i,))
                except com_brew.BrewNoSuchFileException:
                    self.log("It was in the index, but not on the filesystem")
                    
        result[key]=media
        return result

    def savemedia(self, mediakey, mediaindexkey, maps, results, merge, reindexfunction):
        """Actually saves out the media

        @param mediakey: key of the media (eg 'wallpapers' or 'ringtones')
        @param mediaindexkey:  index key (eg 'wallpaper-index')
        @param maps: list index files and locations
        @param results: results dict
        @param merge: are we merging or overwriting what is there?
        @param reindexfunction: the media is re-indexed at the end.  this function is called to do it
        """
        print results.keys()
        # I humbly submit this as the longest function in the bitpim code ...
        # wp and wpi are used as variable names as this function was originally
        # written to do wallpaper.  it works just fine for ringtones as well
        wp=results[mediakey].copy()
        wpi=results[mediaindexkey].copy()
        # remove builtins
        for k in wpi.keys():
            if wpi[k]['origin']=='builtin':
                del wpi[k]

        # sort results['mediakey'+'-index'] into origin buckets

        # build up list into init
        init={}
        for offset,indexfile,location,type,maxentries in maps:
            init[type]={}
            for k in wpi.keys():
                if wpi[k]['origin']==type:
                    index=k-offset
                    name=wpi[k]['name']
                    data=None
                    del wpi[k]
                    for w in wp.keys():
                        if wp[w]['name']==name:
                            data=wp[w]['data']
                            del wp[w]
                    if not merge and data is None:
                        # delete the entry
                        continue
                    init[type][index]={'name': name, 'data': data}

        # init now contains everything from wallpaper-index
        print init.keys()
        # now look through wallpapers and see if anything remaining was assigned a particular
        # origin
        for w in wp.keys():
            o=wp[w].get("origin", "")
            if o is not None and len(o) and o in init:
                idx=-1
                while idx in init[o]:
                    idx-=1
                init[o][idx]=wp[w]
                del wp[w]
            
        # we now have init[type] with the entries and index number as key (negative indices are
        # unallocated).  Proceed to deal with each one, taking in stuff from wp as we have space
        for offset,indexfile,location,type,maxentries in maps:
            if type=="camera": break
            index=init[type]
            try:
                dirlisting=self.getfilesystem(location)
            except com_brew.BrewNoSuchDirectoryException:
                self.mkdirs(location)
                dirlisting={}
            # rename keys to basename
            for i in dirlisting.keys():
                dirlisting[i[len(location)+1:]]=dirlisting[i]
                del dirlisting[i]
            # what we will be deleting
            dellist=[]
            if not merge:
                # get existing wpi for this location
                wpi=results[mediaindexkey]
                for i in wpi:
                    entry=wpi[i]
                    if entry['origin']==type:
                        # it is in the original index, are we writing it back out?
                        delit=True
                        for idx in index:
                            if index[idx]['name']==entry['name']:
                                delit=False
                                break
                        if delit:
                            if entry['name'] in dirlisting:
                                dellist.append(entry['name'])
                            else:
                                self.log("%s in %s index but not filesystem" % (entry['name'], type))
            # go ahead and delete unwanted files
            print "deleting",dellist
            for f in dellist:
                self.rmfile(location+"/"+f)
            #  slurp up any from wp we can take
            while len(index)<maxentries and len(wp):
                idx=-1
                while idx in index:
                    idx-=1
                k=wp.keys()[0]
                index[idx]=wp[k]
                del wp[k]
            # normalise indices
            index=self._normaliseindices(index)  # hey look, I called a function!
            # move any overflow back into wp
            if len(index)>maxentries:
                keys=index.keys()
                keys.sort()
                for k in keys[maxentries:]:
                    idx=-1
                    while idx in wp:
                        idx-=1
                    wp[idx]=index[k]
                    del index[k]
            # write out the new index
            keys=index.keys()
            keys.sort()
            ifile=self.protocolclass.indexfile()
            ifile.numactiveitems=len(keys)
            for k in keys:
                entry=self.protocolclass.indexentry()
                entry.index=k
                entry.name=index[k]['name']
                ifile.items.append(entry)
            while len(ifile.items)<maxentries:
                ifile.items.append(self.protocolclass.indexentry())
            buffer=prototypes.buffer()
            ifile.writetobuffer(buffer)
            self.logdata("Updated index file "+indexfile, buffer.getvalue(), ifile)
            self.writefile(indexfile, buffer.getvalue())
            # Write out files - we compare against existing dir listing and don't rewrite if they
            # are the same size
            for k in keys:
                entry=index[k]
                data=entry.get("data", None)
                if data is None:
                    if entry['name'] not in dirlisting:
                        self.log("Index error.  I have no data for "+entry['name']+" and it isn't already in the filesystem")
                    continue
                if entry['name'] in dirlisting and len(data)==dirlisting[entry['name']]['size']:
                    self.log("Skipping writing %s/%s as there is already a file of the same length" % (location,entry['name']))
                    continue
                self.writefile(location+"/"+entry['name'], data)
        # did we have too many
        if len(wp):
            for k in wp:
                self.log("Unable to put %s on the phone as there weren't any spare index entries" % (wp[k]['name'],))
                
        # Note that we don't write to the camera area

        # tidy up - reread indices
        del results[mediakey] # done with it
        reindexfunction(results)
        return results


class LGNewIndexedMedia:
    "Implements media for LG phones that use the new index format"
    
    def __init__(self):
        pass

    def getmediaindex(self, builtins, maps, results, key):
        """Gets the media (wallpaper/ringtone) index

        @param builtins: the builtin list on the phone
        @param results: places results in this dict
        @param maps: the list of index files and locations
        @param key: key to place results in
        """

        self.log("Reading "+key)
        media={}

        # builtins
        for i,n in enumerate(builtins): # nb zero based index whereas previous phones used 1
            media[i]={'name': n, 'origin': 'builtin'}

        # maps
        for type, location, _ in maps:
            for item in self.getindex(location):
                media[item.index]={
                    'name': basename(item.filename),
                    'filename': item.filename
                    }
                if item.date!=0:
                    media[item.index]['date']=item.date

        # finish
        results[key]=media

    def getindex(self, filename):
        "read an index file"
        try:
            buf=prototypes.buffer(self.getfilecontents(filename))
        except com_brew.BrewNoSuchFileException:
            return []

        g=self.protocolclass.indexfile()
        g.readfrombuffer(buf)
        self.logdata("Index file %s read with %d entries" % (filename, len(g.items)), buf.getdata(), g)
        return g.items

    def getmedia(self, maps, results, key):
        media={}

        for _,location, _ in maps:
            for item in self.getindex(location):
                try:
                    media[basename(item.filename)]=self.getfilecontents(item.filename)
                except (com_brew.BrewNoSuchFileException,com_brew.BrewBadPathnameException):
                    self.log("It was in the index, but not on the filesystem")

        results[key]=media
        return results
        

    def getwallpaperindices(self, results):
        return self.getmediaindex(self.builtinwallpapers, self.wallpaperlocations, results, 'wallpaper-index')

    def getringtoneindices(self, results):
        return self.getmediaindex(self.builtinringtones, self.ringtonelocations, results, 'ringtone-index')

    def getwallpapers(self, result):
        return self.getmedia(self.wallpaperlocations, result, 'wallpapers')

    def getringtones(self, result):
        return self.getmedia(self.ringtonelocations, result, 'ringtone')
            

class LGDirectoryMedia:
    """The media is stored one per directory with .desc and body files"""

    def __init__(self):
        pass

    def getmediaindex(self, builtins, maps, results, key):
        """Gets the media (wallpaper/ringtone) index

        @param builtins: the builtin list on the phone
        @param results: places results in this dict
        @param maps: the list of index files and locations
        @param key: key to place results in
        """
        self.log("Reading "+key)
        media={}

        # builtins
        c=1
        for name in builtins:
            media[c]={'name': name, 'origin': 'builtin' }
            c+=1

        # directory
        for offset,location,origin,maxentries in maps:
            index=self.getindex(location)
            for i in index:
                media[i+offset]={'name': index[i], 'origin': origin}

        results[key]=media
        return media

    __mimetoextensionmapping={
        'image/jpg': '.jpg',
        'image/bmp': '.bmp',
        'image/png': '.png',
        'image/gif': '.gif',
        'image/bci': '.bci',
        'audio/mp3': '.mp3',
        'audio/mid': '.mid',
        'audio/qcp': '.qcp'
        }
    
    def _createnamewithmimetype(self, name, mt):
        name=basename(name)
        if mt=="image/jpeg":
            mt="image/jpg"
        try:
            return name+self.__mimetoextensionmapping[mt]
        except KeyError:
            self.log("Unable to figure out extension for mime type "+mt)
            return name
                     
    def _getmimetype(self, name):
        ext=getext(name.lower())
        if len(ext): ext="."+ext
        if ext==".jpeg":
            return "image/jpg" # special case
        for mt,extension in self.__mimetoextensionmapping.items():
            if ext==extension:
                return mt
        self.log("Unable to figure out a mime type for "+name)
        assert False, "No idea what type "+ext+" is"
        return "x-unknown/x-unknown"

    def getindex(self, location, getmedia=False):
        """Returns an index based on the sub-directories of location.
        The key is an integer, and the value is the corresponding name"""
        index={}
        try:
            dirlisting=self.getfilesystem(location)
        except com_brew.BrewNoSuchDirectoryException:
            return index
        
        for item in dirlisting:
            if dirlisting[item]['type']!='directory':
                continue
            try:
                buf=prototypes.buffer(self.getfilecontents(dirlisting[item]['name']+"/.desc"))
            except com_brew.BrewNoSuchFileException:
                self.log("No .desc file in "+dirlisting[item]['name']+" - ignoring directory")
                continue
            desc=self.protocolclass.mediadesc()
            desc.readfrombuffer(buf)
            self.logdata(".desc file %s/.desc read" % (dirlisting[item]['name'],), buf.getdata(), desc)
            filename=self._createnamewithmimetype(dirlisting[item]['name'], desc.mimetype)
            if not getmedia:
                index[desc.index]=filename
            else:
                try:
                    # try to read it using name in desc file
                    contents=self.getfilecontents(dirlisting[item]['name']+"/"+desc.filename)
                except (com_brew.BrewNoSuchFileException,com_brew.BrewNoSuchDirectoryException):
                    try:
                        # then try using "body"
                        contents=self.getfilecontents(dirlisting[item]['name']+"/body")
                    except (com_brew.BrewNoSuchFileException,com_brew.BrewNoSuchDirectoryException):
                        self.log("Can't find the actual content in "+dirlisting[item]['name'])
                        continue
                index[filename]=contents
        return index

    def getmedia(self, maps, result, key):
        """Returns the contents of media as a dict where the key is a name as returned
        by getindex, and the value is the contents of the media"""
        media={}
        for offset,location,origin,maxentries in maps:
            media.update(self.getindex(location, getmedia=True))
        result[key]=media
        return result

    def savemedia(self, mediakey, mediaindexkey, maps, results, merge, reindexfunction):
        """Actually saves out the media

        @param mediakey: key of the media (eg 'wallpapers' or 'ringtones')
        @param mediaindexkey:  index key (eg 'wallpaper-index')
        @param maps: list index files and locations
        @param results: results dict
        @param merge: are we merging or overwriting what is there?
        @param reindexfunction: the media is re-indexed at the end.  this function is called to do it
        """
        # this is based on the IndexedMedia function and they are frustratingly similar
        print results.keys()
        # I humbly submit this as the longest function in the bitpim code ...
        # wp and wpi are used as variable names as this function was originally
        # written to do wallpaper.  it works just fine for ringtones as well
        wp=results[mediakey].copy()
        wpi=results[mediaindexkey].copy()
        # remove builtins
        for k in wpi.keys():
            if wpi[k]['origin']=='builtin':
                del wpi[k]

        # sort results['mediakey'+'-index'] into origin buckets

        # build up list into init
        init={}
        for offset,location,type,maxentries in maps:
            init[type]={}
            for k in wpi.keys():
                if wpi[k]['origin']==type:
                    index=k-offset
                    name=wpi[k]['name']
                    data=None
                    del wpi[k]
                    for w in wp.keys():
                        if wp[w]['name']==name:
                            data=wp[w]['data']
                            del wp[w]
                    if not merge and data is None:
                        # delete the entry
                        continue
                    init[type][index]={'name': name, 'data': data}

        # init now contains everything from wallpaper-index
        print init.keys()
        # now look through wallpapers and see if anything remaining was assigned a particular
        # origin
        for w in wp.keys():
            o=wp[w].get("origin", "")
            if o is not None and len(o) and o in init:
                idx=-1
                while idx in init[o]:
                    idx-=1
                init[o][idx]=wp[w]
                del wp[w]
            
        # we now have init[type] with the entries and index number as key (negative indices are
        # unallocated).  Proceed to deal with each one, taking in stuff from wp as we have space
        for offset,location,type,maxentries in maps:
            if type=="camera": break
            index=init[type]
            try:
                dirlisting=self.getfilesystem(location)
            except com_brew.BrewNoSuchDirectoryException:
                self.mkdirs(location)
                dirlisting={}
            # rename keys to basename
            for i in dirlisting.keys():
                dirlisting[i[len(location)+1:]]=dirlisting[i]
                del dirlisting[i]
            # what we will be deleting
            dellist=[]
            if not merge:
                # get existing wpi for this location
                wpi=results[mediaindexkey]
                for i in wpi:
                    entry=wpi[i]
                    if entry['origin']==type:
                        # it is in the original index, are we writing it back out?
                        delit=True
                        for idx in index:
                            if index[idx]['name']==entry['name']:
                                delit=False
                                break
                        if delit:
                            if stripext(entry['name']) in dirlisting:
                                dellist.append(entry['name'])
                            else:
                                self.log("%s in %s index but not filesystem" % (entry['name'], type))
            # go ahead and delete unwanted directories
            print "deleting",dellist
            for f in dellist:
                self.rmdirs(location+"/"+f)
            #  slurp up any from wp we can take
            while len(index)<maxentries and len(wp):
                idx=-1
                while idx in index:
                    idx-=1
                k=wp.keys()[0]
                index[idx]=wp[k]
                del wp[k]
            # normalise indices
            index=self._normaliseindices(index)  # hey look, I called a function!
            # move any overflow back into wp
            if len(index)>maxentries:
                keys=index.keys()
                keys.sort()
                for k in keys[maxentries:]:
                    idx=-1
                    while idx in wp:
                        idx-=1
                    wp[idx]=index[k]
                    del index[k]
                    
            # write out the content

            ####  index is dict, key is index number, value is dict
            ####  value['name'] = filename
            ####  value['data'] is contents
            listing=self.getfilesystem(location, 1)

            for key in index:
                efile=index[key]['name']
                content=index[key]['data']
                if content is None:
                    continue # in theory we could rewrite .desc file in case index number has changed
                mimetype=self._getmimetype(efile)
                dirname=stripext(efile)
                desc=self.protocolclass.mediadesc()
                desc.index=key
                desc.filename="body"
                desc.mimetype=mimetype
                desc.totalsize=0
                desc.totalsize=desc.packetsize()+len(content)
                buf=prototypes.buffer()
                desc.writetobuffer(buf)
                descfile="%s/%s/.desc" % (location, dirname)
                self.logdata("Desc file at "+descfile, buf.getvalue(), desc)
                try:
                    self.mkdir("%s/%s" % (location,dirname))
                except com_brew.BrewDirectoryExistsException:
                    pass
                self.writefile(descfile, buf.getvalue())
                bodyfile="%s/%s/body" % (location, dirname)
                if bodyfile in listing and len(content)==listing[bodyfile]['size']:
                    self.log("Skipping writing %s as there is already a file of the same length" % (bodyfile,))
                else:
                    self.writefile(bodyfile, content)

        # did we have too many
        if len(wp):
            for k in wp:
                self.log("Unable to put %s on the phone as there weren't any spare index entries" % (wp[k]['name'],))
                
        # Note that we don't write to the camera area

        # tidy up - reread indices
        del results[mediakey] # done with it
        reindexfunction(results)
        return results


def basename(name):
    if name.rfind('\\')>=0 or name.rfind('/')>=0:
        pos=max(name.rfind('\\'), name.rfind('/'))
        name=name[pos+1:]
    return name

def stripext(name):
    if name.rfind('.')>=0:
        name=name[:name.rfind('.')]
    return name

def getext(name):
    if name.rfind('.')>=0:
        return name[name.rfind('.')+1:]
    return ''
