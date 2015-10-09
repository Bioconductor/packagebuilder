# Create your views here.

from django.template import RequestContext
from django.http import HttpResponse
from django.shortcuts import render_to_response
from viewhistory.models import Package
from viewhistory.models import Job
from viewhistory.models import Build
from viewhistory.models import Message
from viewhistory import helper

def index(request):
    ##packages = Package.objects.all().order_by('name')
    packages = Package.objects.all().extra(select={'lower_name': 'lower(name)'}).order_by('lower_name')
    return render_to_response('index.html',
      {'packages': packages}, context_instance=RequestContext(request))

def jobs(request, package_id):
    p = Package.objects.get(pk=package_id)
    jobs = Job.objects.filter(package=p)#.order_by('id')
    return render_to_response('jobs.html', {'jobs': jobs,
      "package": jobs[0].package.name},
      context_instance=RequestContext(request))
      
def job(request, job_id):
    job = Job.objects.get(pk=job_id)
    builds = job.build_set.all()
    builds = helper.filter_out_wrong_versions(builds, job)
    #builds = helper.re_sort(builds)
    helper.get_messages(builds)
    for build in builds:
        build.builder_id = build.builder_id.replace(".", "_")
    return render_to_response('job.html', {"job": job, "builds": builds},
      context_instance=RequestContext(request))

def recent_builds(request):
    j = Job.objects.order_by("-time_started")[:20]
    return render_to_response("recent_builds.html", 
        {"recent_builds": j}, context_instance=RequestContext(request))

def jid(request, jid):
    b = Build.objects.filter(jid=jid)
    if (len(b) == 0):
        res = 0
    else:
        res = b[0].job.id
    return render_to_response('jid.html', {"res": res},
        context_instance=RequestContext(request))


def overall_build_status(request, job_id):
    ## Out of all the build results, (build, check, build bin, and
    ## post-processing), were there any that were not OK? (with the
    ## exception of build bin on linux which will always be SKIPPED).
    ## if so, return them, else return OK.
    job = Job.objects.get(id=job_id)
    builds = Build.objects.filter(job=job)
    build_statuses = []
    for build in builds:
        if build.version == "0.0.0" and build.preprocessing_result == "":
            continue # filter out builds on wrong machines
        build_statuses.append(build.buildsrc_result)
        build_statuses.append(build.checksrc_result)

        if not "linux" in build.platform.lower():
            build_statuses.append(build.buildbin_result)

        build_statuses.append(build.postprocessing_result)
    result = filter(lambda x: x != 'OK', build_statuses)
    # sometimes there is an empty string in the result, not sure 
    # why. Should look into it more. Meantime let's just filter them out:
    result = filter(lambda x: x != "", result)


    #abnormal = filter(lambda x: x not in ["OK", "WARNINGS", "skipped"])
    if len(result) == 0:
        res = "OK"
    else:
        res = ', '.join(set(result))
    if len(build_statuses) == 0:
        res = "abnormal"
    return render_to_response('overall_build_status.html', {"res": res},
        context_instance=RequestContext(request))
