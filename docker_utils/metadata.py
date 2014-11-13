# Copyright (C) 2014 Brent Baude <bbaude@redhat.com>, Aaron Weitekamp <aweiteka@redhat.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import os
import subprocess
import json
import re
from string import Template
import docker

USER_TEMPLATE_DIR = "/var/container-template/user/"
SYSTEM_TEMPLATE_DIR = "/var/container-template/system/"
CONTAINER_METADATA_DIR = "/container-metadata"

class Create(object):
    def __init__(self, **kwargs):
        self.cuid = kwargs['cuid']
        self.force = kwargs['force']
        self.outfile = kwargs['outfile']
        self.directory = kwargs['directory']
        self.c = docker.Client(base_url='unix://var/run/docker.sock', version='1.12', timeout=10)

    def outfileexists(self, outname):
        if os.path.isfile(outname):
            return True
        else:
            return False

    def assembledict(self, mykeys, dockjson):
        # not used
        # instead of re-building the json, we take the whole thing
        userdict = {'UserParams': {'restart': '', 'rm': '', 'dockercommand': '',
                                   'sig-proxy': ''
                                   }}
        mydict = []
        for desc in mykeys:
            newdict = {desc: {}}
            for keys in mykeys[desc]:
                newdict[desc][keys] = dockjson[desc][keys]
            mydict.append(newdict)
        if dockjson['Name'] != "":
            namedict = {'Name': dockjson['Name']}
            mydict.append(namedict)
        mydict.append(userdict)
        return mydict

    def checkcontaineruid(self):
        """Checks ID and returns valid containeruid. Accepts partial UID"""
        containers = self.c.containers(all=True)
        containeruids = []

        # Create container list, keeps ABI with previous use without API

        for container in containers:
            containeruids.append(container['Id'])
        if not len(self.cuid) >= 3:
            print "Container ID must be at least 3 characters"
            quit(1)
        else:
            match = [containeruid for containeruid in containeruids if re.match(self.cuid, containeruid)]
            if match:
                return match[0]
            else:
                print "Unable to find container ID '%s'. Try 'docker ps'." % self.cuid
                quit(1)

    def writeoutput(self, vals, outname, filetype="json"):
        if not self.directory:
            outname = USER_TEMPLATE_DIR + outname
        else:
            outname = self.directory + outname
        if (not self.force) and (self.outfileexists(outname)):
            print ("{0} already exists. Pass -f or --force to override".format(outname))
            quit(1)
        with open(outname, "w") as outfile:
            if filetype is "json":
                json.dump(vals, outfile, indent=2)
            else:
                outfile.write(vals)
        outfile.closed
        print outname

    @property
    def outname(self):
        out = None
        if self.outfile:
            out = self.outfile
        else:
            name = self.container_json['Name']
            if "/" in name:
                name = name.replace('/', '', 1)
            if '_' in name:
                lname, rname = name.split('_')
                lmatch = [s for s in self.docker_names['left'] if lname == s]
                rmatch = [s for s in self.docker_names['right'] if rname == s]
                if len(lmatch) == 0 and len(rmatch) == 0:
                    out = "{0}.json".format(name)
                else:
                    out = "{0}.json".format(self.cuid)
            else:
                out = "{0}.json".format(name)
        return out

    @property
    def docker_names(self):
        '''Return dict from docker name generator

        See docker/pkg/namesgenerator/names-generator.go'''

        left = [ "happy", "jolly", "dreamy", "sad", "angry", "pensive",
                 "focused", "sleepy", "grave", "distracted", "determined",
                 "stoic", "stupefied", "sharp", "agitated", "cocky",
                 "tender", "goofy", "furious", "desperate", "hopeful",
                 "compassionate", "silly", "lonely", "condescending",
                 "naughty", "kickass", "drunk", "boring", "nostalgic",
                 "ecstatic", "insane", "cranky", "mad", "jovial", "sick",
                 "hungry", "thirsty", "elegant", "backstabbing", "clever",
                 "trusting", "loving", "suspicious", "berserk", "high",
                 "romantic", "prickly", "evil", "admiring", "adoring",
                 "reverent", "serene", "fervent", "modest", "gloomy", "elated"]

        right = [ "albattani", "almeida", "archimedes", "ardinghelli",
                  "babbage", "bardeen", "bartik", "bell", "blackwell",
                  "bohr", "brattain", "brown", "carson", "colden", "cori",
                  "curie", "darwin", "davinci", "einstein", "elion",
                  "engelbart", "euclid", "fermat", "fermi", "feynman",
                  "franklin", "galileo", "goldstine", "goodall", "hawking",
                  "heisenberg", "hodgkin", "hoover", "hopper", "hypatia",
                  "jang", "jones", "kirch", "kowalevski", "lalande", "leakey",
                  "lovelace", "lumiere", "mayer", "mccarthy", "mcclintock",
                  "mclean", "meitner", "mestorf", "morse", "newton", "nobel",
                  "pare", "pasteur", "perlman", "pike", "poincare", "ptolemy",
                  "ritchie", "rosalind", "sammet", "shockley", "sinoussi",
                  "stallman", "tesla", "thompson", "torvalds", "turing",
                  "wilson", "wozniak", "wright", "yalow", "yonath" ]

        return { "left": left, "right": right }

    @property
    def container_json(self):
        self.cuid = self.checkcontaineruid()
        cins = self.c.inspect_container(self.cuid)

        # Remove certain entries
        cins['HostsPath'] = ""
        cins['Image'] = ""
        cins['State']['FinishedAt'] = ""
        cins['State']['StartedAt'] = ""
        cins['ResolvConfPath'] = ""
        cins['HostnamePath'] = ""
        cins['Config']['Hostname'] = ""
        cins['Id'] = ""
        # cins['Name'] = ""

        return cins


    def metadata_file(self):
        # FIXME: populate these values
        userdict = {'UserParams': {'restart': '', 'rm': '', 'dockercommand': '',
                                   'sig-proxy': ''
                                   }}

        vals = [self.container_json, userdict]
        self.writeoutput(vals, self.outname)

    def kubernetes_file(self):
        # FIXME: support list of containers
        kube_file = self.outname.replace('.json', '-pod.json')
        env = []
        for e in self.container_json['Config']['Env']:
            k,v = e.split('=')
            env.append({ "name": k, "value": v })

        volumeMounts = []
        vols = []
        for k,v in self.container_json['Volumes'].iteritems():
            name = v.replace('/', '')
            volumeMounts.append({ "name": name,
                                  "readOnly": self.container_json["VolumesRW"][k],
                                  "mountPath": k })
            vols.append({ "name": name,
                          "source": { "hostDir": { "path": v }}})

        ports = []
        if type(self.container_json["HostConfig"]["PortBindings"]) == dict:
            if len(self.container_json["HostConfig"]["PortBindings"]) > 0 :
                for k,v in self.container_json["HostConfig"]["PortBindings"].iteritems():
                    port, protocol = k.split('/')
                    # FIXME: support list of host ports
                    ports.append({ "containerPort": port,
                                   "hostPort": v[0]['HostPort'] })
        pod = self.kube_pod(env=env, volumeMounts=volumeMounts, vols=vols, ports=ports)
        self.writeoutput(pod, kube_file)

    def kube_pod(self, **kwargs):
    #def kube_pod(self, env=None, volumeMounts=None, vols=None, ports=None):
        return {
            "kind": "Pod",
            "id": self.container_json['Name'],
            "labels": { "name": self.container_json['Name']},
            "apiVersion": "v1beta1",
            "namespace": None,
            "creationTimestamp": None,
            "selfLink": None,
            "desiredState": {
              "manifest": {
                "version": "v1beta1",
                "id": None,
                "containers": [{
                  "name": self.container_json['Name'],
                  "image": self.container_json['Config']['Image'],
                  "command": self.container_json['Config']['Cmd'],
                  "env": kwargs['env'],
                  "ports": kwargs['ports'],
                  "volumeMounts": kwargs['volumeMounts']
                }],
                "volumes": kwargs['vols']
              }
            }
        }

    @property
    def sysd_unit_template(self):
        return """[Unit]
Description=$name
After=docker.service
Requires=docker.service

[Service]
TimeoutStartSec=0
ExecStartPre=-/usr/bin/docker kill $name
ExecStartPre=-/usr/bin/docker rm $name
ExecStartPre=/usr/bin/docker pull $name
ExecStart=/usr/bin/docker run --name  $name $cmd

[Install]
WantedBy=multi-user.target
"""

    def sysd_unit_file(self):
        confcmd = "" if self.container_json['Config']['Cmd'] is None else self.container_json['Config']['Cmd']
        cmd = ' '.join(confcmd)
        repl_dict = {'name': self.container_json['Name'],
                     'cmd': cmd}
        template = Template(self.sysd_unit_template)
        template = template.substitute(repl_dict)
        unit_filename = self.outname.replace('.json', '.service')
        self.writeoutput(template, unit_filename, "text")

    def write_files(self):
        self.metadata_file()
        self.kubernetes_file()
        self.sysd_unit_file()


class List(object):
    def __init__(self):
        self.pattern = 'service|json$'

    def list_all(self):
        dirlist = [USER_TEMPLATE_DIR, SYSTEM_TEMPLATE_DIR]
        files = self.metadata_files(dirlist)
        for f in files:
            print f

    def metadata_files(self, dirlist):
        files = [d + f for d in dirlist for f in os.listdir(d) if re.search(self.pattern, f)]
        return files


class Pull(object):
    def __init__(self, **kwargs):
        self.force = kwargs['force']
        self.directory = kwargs['directory']
        self.outfile = kwargs['outfile']
        self.response = None

    def get_url_filename(self):
        import cgi
        _, params = cgi.parse_header(self.response.headers.get('Content-Disposition', ''))
        return params['filename']

    @property
    def outname(self):
        filename = None
        if self.outfile:
            filename = self.outfile
        else:
            filename = self.get_url_filename()
        if not self.directory:
            return "{0}/{1}".format(USER_TEMPLATE_DIR, filename)
        else:
            return "{0}/{1}".format(self.directory, filename)

    def pull_url(self, url):
        from urllib2 import Request, urlopen, URLError
        req = Request(url)
        try:
            response = urlopen(req)
        except URLError as e:
            if hasattr(e, 'reason'):
                print 'We failed to reach a server.'
                print 'Reason: ', e.reason
            elif hasattr(e, 'code'):
                print 'The server couldn\'t fulfill the request.'
                print 'Error code: ', e.code
        else:
            self.response = response
            self.writeoutput()

    @property
    def outfileexists(self):
        return os.path.isfile(self.outname)

    def writeoutput(self):
        if (not self.force) and (self.outfileexists):
            print ("{0} already exists. Pass -f or --force to override".format(self.outname))
            quit(1)
        else:
            with open(self.outname, "w") as outfile:
                outfile.write(self.response.read())
            outfile.closed
            print self.outname

class Deploy(object):
    def __init__(self, **kwargs):
        self.image = kwargs['image']
        self.metafile = kwargs['metafile']
        self.client = docker.Client(base_url='unix://var/run/docker.sock', version='1.12', timeout=10)

    def pull(self):
        for line in self.client.pull(repository=self.image, stream=True):
            j = json.loads(line)
            if not "errorDetail" in j.keys():
                print j['status']
            else:
                print j['errorDetail']['message']
                return False

    def rm_container(self, container):
        r = self.client.remove_container(container)
        print r

    def get_file(self):
        if self.pull():
            # create the container with a bogus command since it's required
            container = self.client.create_container(image=self.image, command="bash")
            response = self.client.copy(container=container['Id'],
                                  resource=self.container_file)
            with open(self.installed_file, "w") as outfile:
                # FIXME: there's a docker-py bug where the initial line has junk in it
                # we need to remove stuff like...
                # cockpit.json0100644000000000000000000000456312431134152011600 0ustar0000000000000000[
                # and remove junk at end of file
                pattern1 = re.compile(r'^.+\[')
                pattern2 = re.compile(r'^\].+', re.MULTILINE)
                text = pattern1.sub('[', response.read(), 1)
                text = pattern2.sub(']\n', text)
                outfile.write(text)
            outfile.closed
            print "Wrote %s" % self.installed_file
            self.rm_container(container['Id'])

    @property
    def container_file(self):
        return '/'.join([CONTAINER_METADATA_DIR, self.metafile])

    @property
    def installed_file(self):
        return '/'.join([SYSTEM_TEMPLATE_DIR, self.metafile])
