"""A PoC for the libmodulemd API as part of Uyuni modular repositories support"""

__author__ = "Can Bulut Bayburt <cbbayburt@suse.com>"

import gi
gi.require_version('Modulemd', '2.0')
from gi.repository import Modulemd
from rpmUtils.miscutils import splitFilename

enabledStreams = {}

def enable(stream):
    """Enable a module"""
    enabledStreams[stream.get_module_name()] = stream
    print("Enabled {} ({})".format(stream.get_module_name(), stream.get_NSVCA()))

def disable(name):
    """Disable a module. Reverts enable()"""
    if name in enabledStreams:
        stream = enabledStreams[name]
        del enabledStreams[name]
        print("Disabled {} ({})".format(name, stream.get_NSVCA()))

def getAllStreams(name):
    """Get all available stream names of a module"""
    global index
    module = index.get_module(name)
    if not module:
        return None
    streams = set()
    for s in module.get_all_streams():
        streams.add(s.get_stream_name())
    return list(streams)

def getDefaultStream(name):
    """Get the default stream name of a module"""
    global index
    module = index.get_module(name)
    if not module:
        raise ValueError("Module '{}' not found".format(name))
    defaults = module.get_defaults()

    if defaults:
        return defaults.get_default_stream()

    return module.get_all_streams()[0].get_stream_name()

def getEnabledOrDefault(name):
    """Get the enabled stream name of a module, or the default stream if not enabled"""
    if name == 'platform':
        return 'el8'

    if name not in enabledStreams:
        return getDefaultStream(name)

    enabled = enabledStreams[name]
    return enabled.get_stream_name()

def getDeps(stream):
    """Get module names that a stream depends on"""
    return stream.get_dependencies()[0].get_runtime_modules()

def getDepStreams(stream):
    """Get the streams that a stream depends on as name, stream name tuples"""
    dep = stream.get_dependencies()[0]
    allDeps = []
    for m in dep.get_runtime_modules():
        deps = dep.get_runtime_streams(m)
        if deps:
            allDeps.append((m, deps[0]))
    return allDeps

def getAllContexts(name, stream):
    """Get all available context for a module and a stream name"""
    global index
    module = index.get_module(name)
    if not module:
        return []

    allStreams = module.get_all_streams()
    allContexts = []
    for s in allStreams:
        if s.get_stream_name() == stream:
            allContexts.append(s)

    return allContexts

def isEnabled(name):
    return name in enabledStreams

def pickStream(name, stream):
    """Recursively enable a stream and its dependencies with their
    default streams, unless already enabled with a different stream.
    """
    if isEnabled(name):
        return

    allDeps = set()
    allContexts = getAllContexts(name, stream)
    for c in allContexts:
        allDeps = allDeps.union(getDeps(c))

    enabledDeps = []
    for d in allDeps:
        enabledDeps.append((d ,getEnabledOrDefault(d)))

    for ctx in allContexts:
        currDeps = getDepStreams(ctx)
        if all(i in enabledDeps for i in currDeps):
            for dstream in currDeps:
                pickStream(dstream[0], dstream[1])

            enable(ctx)
            return
    raise Exception("Not all of the dependencies of {} could be resolved using defaults.".format(name))

def pickDefaultStream(name):
    pickStream(name, getDefaultStream(name))

def listEnabledStreams():
    for (name, stream) in enabledStreams.items():
        print(stream.get_NSVCA())

def getRpmBlacklist():
    """Get a list of RPMs to blacklist"""
    global index
    enabledRpms = set()
    for stream in enabledStreams.values():
        enabledRpms = enabledRpms.union(stream.get_rpm_artifacts())

    allRpms = set()
    for name in index.get_module_names():
        module = index.get_module(name)
        for stream in module.get_all_streams():
            allRpms = allRpms.union(stream.get_rpm_artifacts())

    return list(allRpms.difference(enabledRpms))

def getArtifactWithName(artifacts, name):
    """Find an item in a list of RPM strings with a specific package name"""
    for artifact in artifacts:
        (n,v,r,e,a) = splitFilename(artifact)
        if name == n:
            return artifact
    return None

def getApiProvides():
    """Get all RPMs from selected streams as a map"""
    apiProvides = {'_other_': set()}
    for stream in enabledStreams.values():
        streamArtifacts = stream.get_rpm_artifacts()
        for rpm in stream.get_rpm_api():
            artifact = getArtifactWithName(streamArtifacts, rpm)
            if artifact:
                if not apiProvides[rpm]:
                    apiProvides[rpm] = set([artifact])
                else:
                    apiProvides[rpm].add(artifact)
                streamArtifacts.remove(artifact)

        # Add the remaining non-api artifacts
        for artifact in streamArtifacts:
            apiProvides['_other_'].add(artifact)
    return apiProvides

def createModuleIndex(metadataPaths):
    """Load metadata from a list of files"""
    merger = Modulemd.ModuleIndexMerger.new()
    for path in metadataPaths:
        i = Modulemd.ModuleIndex.new()
        i.update_from_file(path, True)
        merger.associate_index(i, 0)
    return merger.resolve()


### PUBLIC API ###

def getPackagesForModules(metadataPaths, selectedStreams):
    """Get all RPMs from selected streams as a map of package names to RPM strings

    Map keys are either package names that a module publicly publishes,
    or '_other_' for RPMs which are not part of any published RPM level API.
    """

    # Load and merge metadata from sources
    global index
    index = createModuleIndex(metadataPaths)

    for (name, stream) in selectedStreams:
        try:
            if stream:
                pickStream(name, stream)
            else:
                pickDefaultStream(name)
        except Exception as e:
            print(e)
            print("Skipping {}:{}".format(name, stream))

def getAllPackages(metadataPaths):
    """Get all modular rpms in the repository"""

    global index
    index = createModuleIndex(metadataPaths)
    allRpms = []
    for name in index.get_module_names():
        module = index.get_module(name)
        for stream in module.get_all_streams():
            allRpms.extend(stream.get_rpm_artifacts())
    return allRpms
