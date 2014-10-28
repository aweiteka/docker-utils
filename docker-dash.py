#!/usr/bin/env python

import os
import subprocess
import time
import argparse
import threading
import string
import docker
import pty

dellist = []

parser = argparse.ArgumentParser()
parser.add_argument("-a", "--all", help="Work with non-active containers too", action="store_true")
parser.add_argument("-i", "--images", help="Jump into the images interface", action="store_true")

args = parser.parse_args()

allcontains = False
if args.images:
    myscreen = "images"
else:
    myscreen = "containers"


if args.all:
    print "View all containers"
    allcontains = True


class Screen(object):
    # main class
    def __init__(self):
        self.c = docker.Client(base_url='unix://var/run/docker.sock', version='1.12', timeout=10)

    def stopcontainers(self, cid, cpid):
        print "Stopping {0}".format(cid)
        self.c.stop(cid, None)
        lambda: os.waitpid(cpid, 0)

    def startcontainers(self, cid):
        self.c.start(cid)

    def deletecontainer(self, cid):
        try:
            print "Deleting %s" % cid
            self.c.remove_container(cid, v=False, link=False)
        except:
            print "Unable to find that container ..."

    def getcontainer(self, cdetails):
        """returns valid list of container IDs"""
        print " "
        global myscreen
        stopcontainers = raw_input("Which {0}(s)?: ".format(myscreen))
        stopcontainers = self.str2list(stopcontainers)
        if self.containerinrange(cdetails, stopcontainers) == False:
            return False
        return stopcontainers

    def str2list(self, inlist):
        """Converts input string into valid list

        Parses spaces, commas and range of values('-')"""
        delim = " "
        if ',' in inlist:
            delim = ","
        inlist = delim.join(inlist.split(delim))
        containerlist = inlist.split(delim)
        rangelist = [containerlist.pop(r[0]) for r in enumerate(containerlist) if '-' in containerlist[r[0]]]
        for rl in rangelist:
            start, end = rl.split('-')
            containerlist.extend(range(int(start), int(end) + 1))
        return containerlist

    def containerinrange(self, cdetails, stopcontainers):
        for i in stopcontainers:
            foo = int(len(cdetails))
            foo = foo - 1
            if not(self.isInt(i)):
                print " "
                print ("{0} isn't a integer...".format(i))
                time.sleep(2)
                return False
            if (0 <= int(i) <= foo) == False:
                print " "
                print ("{0} isn't a valid container number...".format(i))
                time.sleep(2)
                return False
        return True

    def isInt(self, mystr):
        try:
            int(mystr)
            return True
        except ValueError:
            return False


class Containers(Screen):

    def getpid(self, cid):
        cinspect = self.c.inspect_container(cid)
        return cinspect['State']['Pid']

    def terminal2(self, cpid):
        """
        This function takes a pid of a running container and opens it in
        xterm if its available
        """
        nsenter = ('sudo nsenter -m -u -n -i -p -t {0} /bin/bash'.format(cpid))
        if os.getenv('DISPLAY', "") == "":
            pty.spawn(nsenter.split())
        else:
            mycommand = "xterm -T {0} -e {1}".format(cpid, nsenter)
            subprocess.Popen([mycommand], stdout=subprocess.PIPE, shell=True)

    def getcontainerinfo(self, containeruids):
        """ This function takes an array of of container uids and
        returns an array of dicts with the inspect info
        """

        cdetails = list()
        for containers in containeruids:
            cdetails.append(self.c.inspect_container(containers['Id']))
        return cdetails

    def returnuid(self, containarray, mynum):
        myuid = containarray[int(mynum)]['Id']
        return myuid[:8]

    def isRunning(self, containarray, mynum):
        if 'Up' in (containarray[int(mynum)]['Status']):
            return True
        else:
            return False

    def getcontainersummary(self, containerinfo):
        """
        This function takes a container and returns its run state
        """

        cuid = containerinfo['Id']
        cimage = containerinfo['Image']
        if 'Up' in containerinfo['Status']:
            crun = "Running"
        else:
            crun = "Not Running"
        return cuid[:8], cimage, crun

    def printsummary(self):
        global allcontains
        mycontainers = screen.c.containers(quiet=False, all=allcontains, trunc=True, latest=False, since=None, before=None, limit=-1)
        if len(mycontainers) != 0:
            print ('{0:2} {1:12} {2:25} {3:8}'.format(" #", "ID", "Image", "Status"))
            for s in range(len(mycontainers)):
                chostname, cimage, crun = self.getcontainersummary(mycontainers[s])
                print ('{0:2} {1:12} {2:25} {3:8}'.format(s, chostname, cimage, crun))
        else:
            print "No active containers ..."
        print " "
        print "GUI Reference: (q)uit (i)mages (re)fresh show (a)ll"
        print "Container Reference: (r)un (s)top (d)elete (p)eek"
        print " "
        containernum = raw_input("Command: ")
        if containernum.upper() == "A":
            if allcontains == True:
                allcontains = False
            else:
                allcontains = True
        if containernum.upper() == "I":
            images.printimagesummary()
        if containernum.upper() == "X":
            self.printsummary()
        if containernum.upper() == "Q":
            quit()
        if containernum.upper() == "S":
            stopcontainer = screen.getcontainer(mycontainers)
            stopthreads = []
            for container in stopcontainer:
                cid = self.returnuid(mycontainers, container)
                if not self.isRunning(mycontainers, container):
                    print "%s is not running" % cid
                    time.sleep(1)
                    break
                cpid = self.getpid(cid)
                t = threading.Thread(target=screen.stopcontainers, args=(cid, cpid,))

                stopthreads.append(t)
                t.start()
            print "Waiting for containers to stop"
            [x.join() for x in stopthreads]
            self.printsummary()

        if containernum.upper() == "R":
            startthreads = []
            runcontainer = screen.getcontainer(mycontainers)
            for container in runcontainer:
                cid = self.returnuid(mycontainers, container)
                cdetails = self.getcontainerinfo(mycontainers)
                if self.isRunning(mycontainers, container):
                    print "%s is already running" % cid
                    time.sleep(1)
                    break
                t = threading.Thread(target=screen.startcontainers, args=(cid,))
                startthreads.append(t)
                t.start()
            print "Waiting for containers to start"
            [x.join() for x in startthreads]

        if containernum.upper() == "D":
            cdetails = self.getcontainerinfo(mycontainers)
            delcontainer = screen.getcontainer(cdetails)
            for container in delcontainer:
                cid = self.returnuid(mycontainers, container)
                screen.deletecontainer(cid)

        if containernum.upper() == "P":
            cdetails = self.getcontainerinfo(mycontainers)
            peekcontainer = screen.getcontainer(cdetails)
            if peekcontainer != False:
                for container in peekcontainer:
                    if not self.isRunning(mycontainers, container):
                        print " "
                        print ("{0} is not a running container".format(self.returnuid(cdetails, container)))
                        time.sleep(2)
                        self.printsummary()
                    cid = self.returnuid(mycontainers, container)
                    cpid = self.getpid(cid)
                    print "Entering container %s" % self.returnuid(cdetails, container)
                    self.terminal2(cpid)
        self.printsummary()


class Images(Screen):
    # image specific stuffs

    def getimage(self, containerinfo):
        return string.replace(containerinfo[0]['Config']['Image'], "/", "")

    def returnfulluid(self, iid):
        i = self.c.images(name=None, quiet=False, all=True, viz=False)
        for f in i:
            if f['Id'].startswith(iid):
                return f['Id']

    def convertsize(self, kbytes):
        if kbytes > 1000000000:
            ksize = str(round(float(kbytes / 1000000000), 2)) + " GB"
        else:

            ksize = str((int(kbytes / 1000000))) + " MB"

        return ksize

    def findchild(self, imageid, images):
        imagenode = []
        for i in images:
            if i['ParentId'] == imageid:
                imagenode.append(i['Id'])
        if len(imagenode) == 0:
            # No more children
            return False
        elif len(imagenode) == 1:
            return imagenode
        else:
            return imagenode

    def crawl(self, nodeid, images):
        global dellist
        imagechild = ""
        imagechild = self.findchild(nodeid, images)
        if imagechild is not False:
            dellist.append(imagechild)
            if type(imagechild) == list:
                for i in imagechild:
                    if self.crawl(i, images) is False:
                        break
        return dellist

    def deleteimage(self, iid):
        if type(iid) == list:
            for i in iid:
                self.deleteimage(i)
        else:
            print "Deleting {0}".format(iid)
            self.c.remove_image(iid)

    def checkforcontainers(self, imagelist):
        delcontainers = []
        mycontainers = self.c.containers(quiet=False, all=True, trunc=True, latest=False, since=None, before=None, limit=-1)
        # Get all of the image inspect information
        inspectinfo = []
        for j in mycontainers:
            myinspect = self.c.inspect_container(j['Id'])
            inspectinfo.append(myinspect)

        for i in imagelist:
            if type(i) == list:
                for s in i:
                    myid = s
            else:
                myid = i
            for d in inspectinfo:
                if d['Image'] == myid:
                    print "Look for {0} and found {1}".format(myid, d['Image'])
                    state = "Off"
                    if d['State']['Running'] == True:
                        state = "Running"

                    mydict = {'Id': d['Id'][:25], 'Image': d['Config']['Image'], 'Name': d['Name'], 'State': state, 'Pid': d['State']['Pid']}
                    delcontainers.append(mydict)
        return delcontainers

    def printimagesummary(self):
        global myscreen
        global allcontains
        myscreen = "images"
        images = self.c.images(name=None, quiet=False, all=allcontains, viz=False)
        # Map is: Created, VirtualSize, RepoTags[], Id
        print " "
        if len(images) > 1:
            print ('{0:2} {1:20} {2:10} {3:18} {4:8}'.format(" #", "Repo", "Image ID ", "Created", "Size"))
            for s in range(len(images)):
                imagedesc = images[s]['RepoTags'][0].split(':')[0]
                if len(images[s]['RepoTags']) > 1:
                    imagedesc = imagedesc + ":" + images[s]['RepoTags'][0].split(':')[1]
                created = time.strftime("%d %b %y %H:%M", time.localtime(images[s]['Created']))
                isize = self.convertsize(float(images[s]['VirtualSize']))
                print ('{0:2} {1:20} {2:10} {3:18} {4:8}'.format(s, imagedesc, images[s]['Id'][:8], created, isize))
        else:
            print "No images ..."
        print " "
        print "GUI Reference: (c) containers (q)uit (re)fresh"
        print "Image Reference: (r)un (d)elete"
        print " "
        containernum = raw_input("Command: ")
        if containernum.upper() == "A":
            if allcontains == True:
                allcontains = False
            else:
                allcontains = True
        if containernum.upper() == "RE":
            self.printimagesummary()
        if containernum.upper() == "C":
            containers.printsummary()
        if containernum.upper() == "Q":
            quit()
        if containernum.upper() == "D":
            global dellist
            delimages = screen.getcontainer(images)
            allimages = screen.c.images(name=None, quiet=False, all=True, viz=False)
            for d in delimages:
                imagelist = []
                iid = images[int(d)]['Id']
                dellist.append(iid)
                imagelist = self.crawl(iid, allimages)
                delcontainers = self.checkforcontainers(imagelist)
                if delcontainers > 0:
                    print "The following containers would also be stopped and deleted."
                    print " "
                    for cons in delcontainers:
                        print "{0:12} {1:15} {2:15} {3:10}".format(cons['Id'], cons['Image'], cons['Name'], cons['State'])
                    print " "
                    confirm = raw_input("Continue?  (y/n) : ")
                    if confirm.upper() == "Y":
                        for dels in delcontainers:
                            if dels['State'] == "Running":
                                screen.stopcontainers(dels['Id'], dels['Pid'])
                            screen.deletecontainer(dels['Id'])
                    else:
                        print "Not deleting ..."
                        time.sleep(2)
                        self.printimagesummary()

                for i in reversed(imagelist):
                    self.deleteimage(i)
                del imagelist[:]
        self.printimagesummary()


if __name__ == '__main__':

    screen = Screen()

    containers = Containers()
    images = Images()
    if myscreen == "containers":
        containers.printsummary()
    elif myscreen == "images":
        images.printimagesummary()
