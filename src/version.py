### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Information about BitPim version number"""

import time

name="BitPim"
version="0.7"
release=0  # when rereleases of the same version happen, this gets incremented
testver=12  # value of zero is non-test build
extrainfo="" # More gunk should it be test version
contact="The BitPim home page is at http://bitpim.sf.net.  You can post any " \
         "questions or feedback to the mailing list detailed on that page." # where users are sent to contact with feedback

if testver:
    # Different strings in test versions
    extrainfo="This is a test build of BitPim which provides a work in progress.  You can find official releases at http://bitpim.sf.net"
    contact="For questions or feedback, please use the bitpim developer mailing list.  Details " \
             "are at the BitPim web site."

versionstring=version
if testver>0:
    versionstring+="-test"+`testver`
if release>0:
    versionstring+="-"+`release`

# dotted quad version as used on Windows (a.b.c.d where all must be digits only)
# we use major.minor.point.last
# last is <1000 for test releases, and 1000+release for real releases
x=[int(x) for x in version.split(".")]
if x[1]<10:  # ie .6 not .62
    x[1]=x[1]*10
assert x[1]>=10 and x[1]<=99
x.append(x[1]%10)
# we don't normalise (ie 0.6 is left as 0.60 because 0.62 was shipped as 0.62.0.0 and 0.7 as 0.7.0.0 is less than that)
# we can only fix this once the major version number changes
# x[1]=x[1]/10
if testver:
    x.append(testver)
else:
    x.append(1000+release)
dqver=x[:]
del x
dqverstr=".".join([`x` for x in dqver])

author="Roger Binns"
author_email="rogerb@users.sourceforge.net"
url="http://bitpim.sourceforge.net"

description="BitPim "+versionstring
copyright="(C) 2003-2004 Roger Binns <rogerb@users.sf.net> and others - see http://bitpim.sf.net"

if __name__=='__main__':
    # generated for the benefit of the help
    # purposely missing " around values
    print "#define VERSION", versionstring
    print "#define DATENOW", time.strftime("%d %B %Y")
