### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Implements the "Brew" filesystem protocol"""

import p_brew
import time
import cStringIO
import com_phone
import prototypes
import common

class BrewNotSupported(Exception):
    """This phone not supported"""
    pass

class BrewCommandException(Exception):
    def __init__(self, errnum, str=None):
        if str is None:
            str="Brew Error 0x%02x" % (errnum,)
        Exception.__init__(self, str)
        self.errnum=errnum

class BrewNoMoreEntriesException(BrewCommandException):
    def __init__(self, errnum=0x1c):
        BrewCommandException.__init__(self, errnum, "No more directory entries")

class BrewNoSuchDirectoryException(BrewCommandException):
    def __init__(self, errnum=0x08):
        BrewCommandException.__init__(self, errnum, "No such directory")

class BrewNoSuchFileException(BrewCommandException):
    def __init__(self, errnum=0x06):
        BrewCommandException.__init__(self, errnum, "No such file")

class BrewBadPathnameException(BrewCommandException):
    def __init__(self, errnum=0x1a):
        BrewCommandException.__init__(self, errnum, "Bad pathname")

class BrewFileLockedException(BrewCommandException):
    def __init__(self, errnum=0x0b):
        BrewCommandException.__init__(self, errnum, "File is locked")

class BrewNameTooLongException(BrewCommandException):
    def __init__(self, errnum=0x0d):
        BrewCommandException.__init__(self, errnum, "Name is too long")

class BrewDirectoryExistsException(BrewCommandException):
    def __init__(self, errnum=0x07):
        BrewCommandException.__init__(self, errnum, "Directory already exists")


modeignoreerrortypes=com_phone.modeignoreerrortypes+(BrewCommandException,common.CommsDataCorruption)

class BrewProtocol:
    "Talk to a phone using the 'brew' protocol"

    MODEBREW="modebrew"
    brewterminator="\x7e"

    # phone uses Jan 1, 1980 as epoch.  Python uses Jan 1, 1970.  This is difference
    # plus a fudge factor of 4 days, 17 hours for no reason I can find
    _brewepochtounix=315532800+406800

    def __init__(self):
        pass

    def getfirmwareinformation(self):
        self.log("Getting firmware information")
        req=p_brew.firmwarerequest()
        res=self.sendbrewcommand(req, p_brew.firmwareresponse)

    def explore0c(self):
        self.log("Trying stuff with command 0x0c")
        req=p_brew.testing0crequest()
        res=self.sendbrewcommand(req, p_brew.testing0cresponse)

    def offlinerequest(self, reset=False):
        req=p_brew.setmoderequest()
        req.request=1
        self.log("Taking phone offline")
        self.sendbrewcommand(req, p_brew.setmoderesponse)
        if reset:
            req=p_brew.setmoderequest()
            req.request=2
            self.log("Resetting phone")
            self.sendbrewcommand(req, p_brew.setmoderesponse)
            
    def modemmoderequest(self):
        # Perhaps we should modify sendbrewcommand to have an option to
        # not wait for a response
        self.log("Attempting to put phone in modem mode")
        req=p_brew.setmodemmoderequest()
        buffer=prototypes.buffer()
        req.writetobuffer(buffer)
        data=buffer.getvalue()
        self.logdata("brew request", data, req)
        data=escape(data+crcs(data))+self.brewterminator
        self.comm.write(data)

    def mkdir(self, name):
        self.log("Making directory '"+name+"'")
	req=p_brew.mkdirrequest()
	req.dirname=name
        self.sendbrewcommand(req, p_brew.mkdirresponse)

    def mkdirs(self, directory):
        if len(directory)<1:
            return
        dirs=directory.split('/')
        for i in range(0,len(dirs)):
            try:
                self.mkdir("/".join(dirs[:i+1]))  # basically mkdir -p
            except:
                pass


    def rmdir(self,name):
        self.log("Deleting directory '"+name+"'")
	req=p_brew.rmdirrequest()
	req.dirname=name
        self.sendbrewcommand(req, p_brew.rmdirresponse)

    def rmfile(self,name):
        self.log("Deleting file '"+name+"'")
	req=p_brew.rmfilerequest()
	req.filename=name
        self.sendbrewcommand(req, p_brew.rmfileresponse)

    def rmdirs(self, path):
        self.progress(0,1, "Listing child files and directories")
        all=self.getfilesystem(path, 100)
        keys=all.keys()
        keys.sort()
        keys.reverse()
        count=0
        for k in keys:
            self.progress(count, len(keys), "Deleting "+k)
            count+=1
            if all[k]['type']=='directory':
                self.rmdir(k)
            else:
                self.rmfile(k)
        self.rmdir(path)


    def getfilesystem(self, dir="", recurse=0):
        results={}

        self.log("Listing dir '"+dir+"'")
        
        # self.log("file listing 0x0b command")
        for i in xrange(10000):
            try:
                req=p_brew.listfilerequest()
                req.entrynumber=i
                req.dirname=dir
                res=self.sendbrewcommand(req,p_brew.listfileresponse)
                results[res.filename]={ 'name': res.filename, 'type': 'file',
                                'size': res.size }
                if res.date==0:
                    results[res.filename]['date']=(0, "")
                else:
                    try:
                        date=res.date+self._brewepochtounix
                        results[res.filename]['date']=(date, time.strftime("%x %X", time.gmtime(date)))
                    except:
                        # invalid date - see SF bug #833517
                        results[res.filename]['date']=(0, "")
                    
            except BrewNoMoreEntriesException:
                break

        # i tried using 0x0a command to list subdirs but that fails when
        # mingled with 0x0b commands
        req=p_brew.listdirectoriesrequest()
        req.dirname=dir

        res=self.sendbrewcommand(req, p_brew.listdirectoriesresponse)
        for i in range(res.numentries):
            subdir=res.items[i].subdir
            # sometimes subdir can already include the parent directory
            f=subdir.rfind("/")
            if f>=0: subdir=subdir[f+1:]
            if len(dir):
                subdir=dir+"/"+subdir
            results[subdir]={ 'name': subdir, 'type': 'directory' }
            if recurse>0:
                results.update(self.getfilesystem(subdir, recurse-1))
        return results

    def writefile(self, name, contents):
        start=time.time()
        self.log("Writing file '"+name+"' bytes "+`len(contents)`)
        desc="Writing "+name
	req=p_brew.writefilerequest()
	req.filesize=len(contents)
	req.data=contents[:0x100]
	req.filename=name
        self.sendbrewcommand(req, p_brew.writefileresponse)
        # do remaining blocks
        numblocks=len(contents)/0x100
        count=0
        for offset in range(0x100, len(contents), 0x100):
	    req=p_brew.writefileblockrequest()
            count+=1
            if count>=0x100: count=1
            if count % 5==0:
                self.progress(offset>>8,numblocks,desc)
	    req.blockcounter=count
	    req.thereismore=offset+0x100<len(contents)
            block=contents[offset:]
            l=min(len(block), 0x100)
            block=block[:l]
	    req.data=block
            self.sendbrewcommand(req, p_brew.writefileblockresponse)
        end=time.time()
        if end-start>3:
            self.log("Wrote "+`len(contents)`+" bytes at "+`int(len(contents)/(end-start))`+" bytes/second")


    def getfilecontents(self, file):
        start=time.time()
        self.log("Getting file contents '"+file+"'")
        desc="Reading "+file

        data=cStringIO.StringIO()

        req=p_brew.readfilerequest()
        req.filename=file
        
        res=self.sendbrewcommand(req, p_brew.readfileresponse)
        
        filesize=res.filesize
        data.write(res.data)

        counter=0
        while res.thereismore:
            counter+=1
            if counter>0xff:
                counter=0x01
            if counter%5==0:
                self.progress(data.tell(), filesize, desc)
            req=p_brew.readfileblockrequest()
            req.blockcounter=counter
            res=self.sendbrewcommand(req, p_brew.readfileblockresponse)
            data.write(res.data)

        self.progress(1,1,desc)
        
        data=data.getvalue()

        # give the download speed if we got a non-trivial amount of data
        end=time.time()
        if end-start>3:
            self.log("Read "+`filesize`+" bytes at "+`int(filesize/(end-start))`+" bytes/second")
        
        if filesize!=len(data):
            self.log("expected size "+`filesize`+"  actual "+`len(data)`)
            self.raisecommsexception("Brew file read is incorrect size", common.CommsDataCorruption)
        return data

    class DirCache:
        """This is a class that lets you do various filesystem manipulations and
        it remembers the data.  Typical usage would be if you make changes to
        files (adding, removing, rewriting) and then have to keep checking if
        files exist, add sizes etc.  This class saves the hassle of rereading
        the directory every single time.  Note that it will only see changes
        you make via this class.  If you go directly to the Brew class then
        those won't be seen.
        """
        def __init__(self, target):
            "@param target: where operations should be done after recording them here"
            self.__target=target
            self.__cache={}

        def rmfile(self, filename):
            res=self.__target.rmfile(filename)
            node=self._getdirectory(brewdirname(filename))
            if node is None: # we didn't have it
                return
            del node[brewbasename(filename)]
            return res

        def stat(self, filename):
            node=self._getdirectory(brewdirname(filename), ensure=True)
            return node.get(brewbasename(filename), None)

        def writefile(self, filename, contents):
            res=self.__target.writefile(filename, contents)
            node=self._getdirectory(brewdirname(filename))
            if node is None:
                return
            # we can't put the right date in since we have no idea
            # what the timezone (or the time for that matter) on the
            # phone is
            stat=node.get(brewbasename(filename), {'name': filename, 'type': 'file', 'date': (0, "")})
            stat['size']=len(contents)
            node[brewbasename(filename)]=stat
            return res

        def _getdirectory(self, dirname, ensure=False):
            if not ensure:
                return self.__cache.get(dirname, None)
            node=self.__cache.get(dirname, None)
            if node is not None: return node
            node={}
            fs=self.__target.getfilesystem(dirname)
            for filename in fs.keys():
                node[brewbasename(filename)]=fs[filename]
            self.__cache[dirname]=node
            return node

    def _setmodebrew(self):
        req=p_brew.memoryconfigrequest()
        respc=p_brew.memoryconfigresponse
        
        for baud in 0, 38400,115200:
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue
            try:
                self.sendbrewcommand(req, respc, callsetmode=False)
                return True
            except modeignoreerrortypes:
                pass

        # send AT$CDMG at various speeds
        for baud in (0, 115200, 19200, 230400):
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue
            print "Baud="+`baud`

            try:
                for line in self.comm.sendatcommand("+GMM"):
                    if line.find("SPH-A700")>0:
                        raise BrewNotSupported("This phone is not supported by BitPim", self.desc)
            except modeignoreerrortypes:
                self.log("No response to AT+GMM")
            except:
                print "GMM Exception"
                self.mode=self.MODENONE
                self.comm.shouldloop=True
                raise

            try:
                self.comm.write("AT$QCDMG\r\n")
            except:
                # some issue during writing such as user pulling cable out
                self.mode=self.MODENONE
                self.comm.shouldloop=True
                raise
            try:
                # if we got OK back then it was success
                if self.comm.readsome().find("OK")>=0:
                    break
            except modeignoreerrortypes:
                self.log("No response to setting QCDMG mode")

        # verify if we are in DM mode
        for baud in 0,38400,115200:
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue
            try:
                self.sendbrewcommand(req, respc, callsetmode=False)
                return True
            except modeignoreerrortypes:
                pass
        return False

    def sendbrewcommand(self, request, responseclass, callsetmode=True):
        if callsetmode:
            self.setmode(self.MODEBREW)
        buffer=prototypes.buffer()
        request.writetobuffer(buffer)
        data=buffer.getvalue()
        self.logdata("brew request", data, request)
        data=escape(data+crcs(data))+self.brewterminator
        firsttwo=data[:2]
        try:
            # we logged above, and below
            data=self.comm.writethenreaduntil(data, False, self.brewterminator, logreaduntilsuccess=False) 
        except modeignoreerrortypes:
            self.mode=self.MODENONE
            self.raisecommsdnaexception("manipulating the filesystem")
        self.comm.success=True
        origdata=data
        
        # sometimes there is junk at the begining, eg if the user
        # turned off the phone and back on again.  So if there is more
        # than one 7e in the escaped data we should start after the
        # second to last one
        d=data.rfind(self.brewterminator,0,-1)
        if d>=0:
            self.log("Multiple packets in data - taking last one starting at "+`d+1`)
            self.logdata("Original data", origdata, None)
            data=data[d+1:]

        # turn it back to normal
        data=unescape(data)

        # sometimes there is other crap at the begining
        d=data.find(firsttwo)
        if d>0:
            self.log("Junk at begining of packet, data at "+`d`)
            self.logdata("Original data", origdata, None)
            self.logdata("Working on data", data, None)
            data=data[d:]
        # take off crc and terminator
        crc=data[-3:-1]
        data=data[:-3]
        if crcs(data)!=crc:
            self.logdata("Original data", origdata, None)
            self.logdata("Working on data", data, None)
            raise common.CommsDataCorruption("Brew packet failed CRC check", self.desc)
        
        # log it
        self.logdata("brew response", data, responseclass)

        if firsttwo=="Y\x0c" and data==firsttwo:
            # we are getting an echo - the modem port has been selected
            # instead of diagnostics port
            raise common.CommsWrongPort("The port you are using is echoing data back, and is not valid for Brew data.  Most likely you have selected the modem interface when you should be using the diagnostic interface.", self.desc)

        # look for errors
        if data[0]=="Y" and data[2]!="\x00":  # Y is 0x59 which is brew command prefix
                err=ord(data[2])
                if err==0x1c:
                    raise BrewNoMoreEntriesException()
                if err==0x08:
                    raise BrewNoSuchDirectoryException()
                if err==0x06:
                    raise BrewNoSuchFileException()
                if err==0x1a:
                    raise BrewBadPathnameException()
                if err==0x0b:
                    raise BrewFileLockedException()
                if err==0x0d:
                    raise BrewNameTooLongException()
                if err==0x07:
                    raise BrewDirectoryExistsException()
                raise BrewCommandException(err)
        # parse data
        buffer=prototypes.buffer(data)
        res=responseclass()
        try:
            res.readfrombuffer(buffer)
        except:
            # we had an exception so log the data even if protocol log
            # view is not available
            self.log(formatpacketerrorlog("Error decoding response", origdata, data, responseclass))
            raise
        return res

def formatpacketerrorlog(str, origdata, data, klass):
    # copied from guiwidgets.LogWindow.logdata
    hd=""
    if data is not None:
        hd="Data - "+`len(data)`+" bytes\n"
        if klass is not None:
            try:
                hd+="<#! %s.%s !#>\n" % (klass.__module__, klass.__name__)
            except:
                klass=klass.__class__
                hd+="<#! %s.%s !#>\n" % (klass.__module__, klass.__name__)
        hd+=common.datatohexstring(data)
    if origdata is not None:
        hd+="\nOriginal Data - "+`len(data)`+" bytes\n"+common.datatohexstring(origdata)
    return str+" "+hd

# The CRC and escaping mechanisms are the same as used in PPP, HDLC and
# various other standards.

def escape(data):
    return data.replace("\x7d", "\x7d\x5d") \
           .replace("\x7e", "\x7d\x5e")

def unescape(d):
    if d.find("\x7d")<0: return d
    res=list(d)
    try:
        start=0
        while True:
            p=res.index("\x7d", start)
            res[p:p+2]=chr(ord(res[p+1])^0x20)
            start=p+1
    except ValueError:
        return "".join(res)

# See http://www.repairfaq.org/filipg/LINK/F_crc_v35.html for more info
# on CRC
_crctable=(
    0x0000, 0x1189, 0x2312, 0x329b, 0x4624, 0x57ad, 0x6536, 0x74bf,   # 0 - 7
    0x8c48, 0x9dc1, 0xaf5a, 0xbed3, 0xca6c, 0xdbe5, 0xe97e, 0xf8f7,   # 8 - 15
    0x1081, 0x0108, 0x3393, 0x221a, 0x56a5, 0x472c, 0x75b7, 0x643e,   # 16 - 23
    0x9cc9, 0x8d40, 0xbfdb, 0xae52, 0xdaed, 0xcb64, 0xf9ff, 0xe876,   # 24 - 31
    0x2102, 0x308b, 0x0210, 0x1399, 0x6726, 0x76af, 0x4434, 0x55bd,   # 32 - 39
    0xad4a, 0xbcc3, 0x8e58, 0x9fd1, 0xeb6e, 0xfae7, 0xc87c, 0xd9f5,   # 40 - 47
    0x3183, 0x200a, 0x1291, 0x0318, 0x77a7, 0x662e, 0x54b5, 0x453c,   # 48 - 55
    0xbdcb, 0xac42, 0x9ed9, 0x8f50, 0xfbef, 0xea66, 0xd8fd, 0xc974,   # 56 - 63
    0x4204, 0x538d, 0x6116, 0x709f, 0x0420, 0x15a9, 0x2732, 0x36bb,   # 64 - 71
    0xce4c, 0xdfc5, 0xed5e, 0xfcd7, 0x8868, 0x99e1, 0xab7a, 0xbaf3,   # 72 - 79
    0x5285, 0x430c, 0x7197, 0x601e, 0x14a1, 0x0528, 0x37b3, 0x263a,   # 80 - 87
    0xdecd, 0xcf44, 0xfddf, 0xec56, 0x98e9, 0x8960, 0xbbfb, 0xaa72,   # 88 - 95
    0x6306, 0x728f, 0x4014, 0x519d, 0x2522, 0x34ab, 0x0630, 0x17b9,   # 96 - 103
    0xef4e, 0xfec7, 0xcc5c, 0xddd5, 0xa96a, 0xb8e3, 0x8a78, 0x9bf1,   # 104 - 111
    0x7387, 0x620e, 0x5095, 0x411c, 0x35a3, 0x242a, 0x16b1, 0x0738,   # 112 - 119
    0xffcf, 0xee46, 0xdcdd, 0xcd54, 0xb9eb, 0xa862, 0x9af9, 0x8b70,   # 120 - 127
    0x8408, 0x9581, 0xa71a, 0xb693, 0xc22c, 0xd3a5, 0xe13e, 0xf0b7,   # 128 - 135
    0x0840, 0x19c9, 0x2b52, 0x3adb, 0x4e64, 0x5fed, 0x6d76, 0x7cff,   # 136 - 143
    0x9489, 0x8500, 0xb79b, 0xa612, 0xd2ad, 0xc324, 0xf1bf, 0xe036,   # 144 - 151
    0x18c1, 0x0948, 0x3bd3, 0x2a5a, 0x5ee5, 0x4f6c, 0x7df7, 0x6c7e,   # 152 - 159
    0xa50a, 0xb483, 0x8618, 0x9791, 0xe32e, 0xf2a7, 0xc03c, 0xd1b5,   # 160 - 167
    0x2942, 0x38cb, 0x0a50, 0x1bd9, 0x6f66, 0x7eef, 0x4c74, 0x5dfd,   # 168 - 175
    0xb58b, 0xa402, 0x9699, 0x8710, 0xf3af, 0xe226, 0xd0bd, 0xc134,   # 176 - 183
    0x39c3, 0x284a, 0x1ad1, 0x0b58, 0x7fe7, 0x6e6e, 0x5cf5, 0x4d7c,   # 184 - 191
    0xc60c, 0xd785, 0xe51e, 0xf497, 0x8028, 0x91a1, 0xa33a, 0xb2b3,   # 192 - 199
    0x4a44, 0x5bcd, 0x6956, 0x78df, 0x0c60, 0x1de9, 0x2f72, 0x3efb,   # 200 - 207
    0xd68d, 0xc704, 0xf59f, 0xe416, 0x90a9, 0x8120, 0xb3bb, 0xa232,   # 208 - 215
    0x5ac5, 0x4b4c, 0x79d7, 0x685e, 0x1ce1, 0x0d68, 0x3ff3, 0x2e7a,   # 216 - 223
    0xe70e, 0xf687, 0xc41c, 0xd595, 0xa12a, 0xb0a3, 0x8238, 0x93b1,   # 224 - 231
    0x6b46, 0x7acf, 0x4854, 0x59dd, 0x2d62, 0x3ceb, 0x0e70, 0x1ff9,   # 232 - 239
    0xf78f, 0xe606, 0xd49d, 0xc514, 0xb1ab, 0xa022, 0x92b9, 0x8330,   # 240 - 247
    0x7bc7, 0x6a4e, 0x58d5, 0x495c, 0x3de3, 0x2c6a, 0x1ef1, 0x0f78,   # 248 - 255
    )

def crc(data, initial=0xffff):
    "CRC calculation - returns 16 bit integer"
    res=initial
    for byte in data:
        curres=res
        res=res>>8  # zero extended
        val=(ord(byte)^curres) & 0xff
        val=_crctable[val]
        res=res^val

    res=(~res)&0xffff
    return res

def crcs(data, initial=0xffff):
    "CRC calculation - returns 2 byte string LSB"
    r=crc(data, initial)
    return "%c%c" % ( r& 0xff, (r>>8)&0xff)

def brewbasename(str):
    "returns basename of str"
    if str.rfind("/")>0:
        return str[str.rfind("/")+1:]
    return str

def brewdirname(str):
    "returns dirname of str"
    if str.rfind("/")>0:
        return str[:str.rfind("/")]
    return str


class SPURIOUSZERO(prototypes.BaseProtogenClass):
    """This is a special class used to consume the spurious zero in some p_brew.listfileresponse

    The three bytes are formatted as follows:

       - An optional 'null' byte (this class)
       - A byte specifying how long the directory name portion is, including trailing slash
       - A byte specifying the length of the whole name
       - The bytes of the filename (which includes the full directory name)

    Fun and games ensue because files in the root directory have a zero length directory
    name, so we have some heuristics to try and distinguish if the first byte is the
    spurious zero or not
    """
    def __init__(self, *args, **kwargs):
        super(SPURIOUSZERO,self).__init__(*args, **kwargs)
        
        self._value=None
        if self._ismostderived(SPURIOUSZERO):
            self._update(args, kwargs)

    def _update(self, args, kwargs):
        super(SPURIOUSZERO, self)._update(args, kwargs)
        
        self._complainaboutunusedargs(SPURIOUSZERO, kwargs)

        if len(args):
            raise TypeError("Unexpected arguments "+`args`)

    def readfrombuffer(self, buf):
         self._bufferstartoffset=buf.getcurrentoffset()

         # there are several cases this code has to deal with
         #
         # The data is ordered like this:
         #
         # optional spurious zero (sz)
         # dirlen
         # fulllen
         # name
         #
         # These are the various possibilities.  The first two
         # are a file in the root directory (dirlen=0), with the other
         # two being a file in a subdirectory  (dirlen>0). fulllen
         # is always >0
         #
         # A:    dirlen=0 fulllen name
         # B: sz dirlen=0 fulllen name
         # C:    dirlen>0 fulllen name
         # D: sz dirlen>0 fulllen name

         while True:  # this is just used so we can break easily

             # CASE C
             if buf.peeknextbyte()!=0:
                 self._value=-1
                 break

             # CASE B
             if buf.peeknextbyte(1)==0:
                 self._value=buf.getnextbyte() # consume sz
                 break
             
             # A & D are harder to distinguish since they both consist of a zero
             # followed by non-zero.  Consequently we examine the data for
             # consistency

             all=buf.peeknextbytes(min(max(2+buf.peeknextbyte(1), 3+buf.peeknextbyte(2)), buf.howmuchmore()))

             # are the values consistent for D?
             ddirlen=ord(all[1])
             dfulllen=ord(all[2])

             if ddirlen<dfulllen and ddirlen<len(all)-3 and all[3+ddirlen-1]=='/':
                 self._value=buf.getnextbyte() # consume sz
                 break

             # case C, do nothing
             self._value=-2
             break
             
         self._bufferendoffset=buf.getcurrentoffset()

    def writetobuffer(self, buf):
        raise NotImplementedError()

    def packetsize(self):
         raise NotImplementedError()

    def getvalue(self):
        "Returns the string we are"

        if self._value is None:
            raise prototypes.ValueNotSetException()
        return self._value
