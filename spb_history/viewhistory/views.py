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
    return render_to_response('job.html', {"job": job, "builds": builds},
      context_instance=RequestContext(request))

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
    ## if so, return the severest one (error > warning) or SKIPPED
    ## which might be caused by an SPB config problem.
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
    if len(result) == 0:
        res = "OK"
    else:
        res = ', '.join(set(result))
    return render_to_response('overall_build_status.html', {"res": res},
        context_instance=RequestContext(request))
