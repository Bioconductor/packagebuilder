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
    packages = Package.objects.all().order_by('name')
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
    #builds = helper.re_sort(builds)
    helper.get_messages(builds)
    return render_to_response('job.html', {"job": job, "builds": builds},
      context_instance=RequestContext(request))
