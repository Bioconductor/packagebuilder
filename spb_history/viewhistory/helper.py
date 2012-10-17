

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
    if r_ver == "2.14":
        nodes = ['wilson2', 'pitt', 'moscato1']
    elif r_ver == "2.15":
        if bioc_version == "2.11":
            nodes = ['lamb1', 'perceval', 'moscato1']
    elif r_ver == "2.16":
        if bioc_version == "2.12":
            nodes = ['lamb2', 'petty', 'moscato2']

    else:
        raise Exception("Don't know the build nodes for R-%s (BioC %s)" % (r_ver, bioc_version))
    
    ret = []
    for build in builds:
        if build.builder_id in nodes:
            ret.append(build)
    return (ret)