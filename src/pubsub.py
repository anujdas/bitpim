### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

from wxPython.lib.pubsub import Publisher
import weakref
#import wx

###
### A list of topics
###


# Maintain the list of categories
REQUEST_CATEGORIES=( 'request', 'categories' )
ALL_CATEGORIES=( 'response', 'categories') # data is list of strings
SET_CATEGORIES=( 'request', 'setcategories') # data is list of strings
ADD_CATEGORY=( 'request', 'addcategory') # data is list of strings

###
### Actual code using pubsub library
###

class _weaklistener:

    def __init__(self, obj, methodname):
        try:
            getattr(obj, methodname)
        except AttributeError:
            raise "Can't find "+methodname+" when adding listener"
        
        self.obj=weakref.ref(obj)
        self.methodname=methodname

    def __call__(self, *args, **kwargs):
        obj=self.obj()
        if obj is None:
            print "someone was gc'ed"
            try:
                unsubscribe(self.call)
            except:
                # we don't care if unsubscribe fails
                pass
        else:
            return getattr(obj, self.methodname)(*args, **kwargs)

    # The pubsub module does this stupid 'enhancement' where it tries to figure
    # out if we want arguments or not.  Consequently the method below has
    # to be supplied
    def call(self, argument):
        return self.__call__(argument)

def subscribe(topic, object, methodname):
    # by default we use weakrefs, so the subscribers don't
    # have to remember to unsubscribe
    obj=_weaklistener(object, methodname)
    Publisher.subscribe(topic, obj.call)

def subscribepersistent(topic, listener):
    Publisher.subscribe(topic, listener)

def unsubscribe(listener):
    Publisher.unsubscribe(listener)

def publish(topic, data=None):
    Publisher.sendMessage(topic, data)

###
### Builtin managers
###

class CategoryManager:

    # this is only used to prevent the pubsub module
    # from being GC while any instance of this class exists
    __publisher=Publisher

    def __init__(self):
        self.categories=[]
        subscribe(REQUEST_CATEGORIES, self, "OnListRequest")
        subscribe(SET_CATEGORIES, self, "OnSetCategories")
        subscribe(ADD_CATEGORY, self, "OnAddCategory")

    def OnListRequest(self, msg=None):
        print "publish all categories", self.categories
        # nb we publish a copy of the list, not the real
        # thing.  otherwise other code inadvertently modifies it!
        publish(ALL_CATEGORIES, self.categories[:])

    def OnAddCategory(self, msg):
        name=msg.data
        if msg in self.categories:
            return
        self.categories.append(name)
        self.categories.sort()
        self.OnListRequest()

    def OnSetCategories(self, msg):
        cats=msg.data[:]
        self.categories=cats
        self.categories.sort()
        self.OnListRequest()

# same trick as pubsub module
CategoryManager=CategoryManager()
