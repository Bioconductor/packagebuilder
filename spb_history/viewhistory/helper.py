

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
