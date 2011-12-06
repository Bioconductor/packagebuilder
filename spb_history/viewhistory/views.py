# Create your views here.

from django.http import HttpResponse
from django.shortcuts import render_to_response
from viewhistory.models import Package
from viewhistory.models import Job

def index(request):
    packages = Package.objects.all().order_by('name')
    return render_to_response('index.html',
      {'packages': packages})

def jobs(request, package_id):
    p = Package.objects.get(pk=package_id)
    jobs = Job.objects.filter(package=p)#.order_by('id')
    return render_to_response('jobs.html', {'jobs': jobs,
      "package": jobs[0].package.name})
