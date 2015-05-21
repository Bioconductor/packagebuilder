from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'spb_history.views.home', name='home'),
    # url(r'^spb_history/', include('spb_history.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', 'viewhistory.views.index'),
    url(r'^recent_builds', 'viewhistory.views.recent_builds'),
    url(r'^jobs/(?P<package_id>\d+)/$', 'viewhistory.views.jobs'),
    url(r'^job/(?P<job_id>\d+)/$', 'viewhistory.views.job'),
    url(r'^jid/(?P<jid>.+)/$', 'viewhistory.views.jid'),
    url(r'^overall_build_status/(?P<job_id>\d+)/$',
        'viewhistory.views.overall_build_status')
)

urlpatterns += staticfiles_urlpatterns()
