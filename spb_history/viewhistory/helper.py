

def sort_helper(b1, b2):
    os_order = {'Linux': 0, 'Windows': 1, 'Mac': 2}
    word = b1.os.split(" ")[0]
    word2 = b2.os.split(" ")[0]
    return(cmp(os_order[word], os_order[word2]))

def re_sort(builds):
    return(sorted(builds, cmp=sort_helper))


def get_message(build, build_phase):
    messages = build.message_set.filter(build_phase=build_phase)
    message = ""
    for m in messages:
        message += m.body
    return(message)
    

def get_messages(builds):
    phases = ['building', 'buildingbin', 'checking',
      'post_processing', 'preprocessing']
    for build in builds:
        build.foo = "kfhgkfh22"
        setattr(build, "bar", "lalalal")
        for phase in phases:
            attr_name = "%s_message" % phase
            message = get_message(build, phase)
            setattr(build, attr_name, message)
            #print("[%s]build.%s is \n%s" % (build.builder_id, attr_name, getattr(build, attr_name)))


## FIXME there must be a less hardcodey way to do this
def filter_out_wrong_versions(builds, job):
    r_ver = job.r_version
    bioc_version = job.bioc_version

    nodes = []

    if (r_ver == "3.2"):
        if bioc_version == "3.1":
            nodes = ["zin2", "petty", "moscato2", "morelia"]
        if bioc_version == "3.2":
            nodes = ["linux1.bioconductor.org", "perceval", "windows1.bioconductor.org", "oaxaca"]
    if (r_ver == "3.1"):
        if bioc_version == "3.0":
            nodes = ["zin1", "perceval", "moscato1", "oaxaca"]
        if bioc_version == "2.14":
            nodes = ["zin2", "petty", "moscato2"]
    if (r_ver == "2.16" or r_ver == "3.0"):
        if bioc_version == "2.12":
            nodes = ['george2', 'petty', 'moscato2']
        if bioc_version == "2.13":
            nodes = ["zin1", "perceval", "moscato1"]
    if (r_ver == "2.15"):
        if (bioc_version == "2.11"):
            nodes = ["lamb1", "moscato1", "perceval"]
        if (bioc_version == "2.10"):
            nodes = ["lamb2", "moscato2", "petty"]
    ## keep old stuff here so build history continues to work

    if (len(nodes) == 0):
        raise Exception("Don't know the build nodes for R-%s (BioC %s)" % (r_ver, bioc_version))
    
    ret = []
    for build in builds:
        if build.builder_id in nodes:
            ret.append(build)
    return (ret)