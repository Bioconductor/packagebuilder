from django.db import models

# Create your models here.
class Package(models.Model):
    name = models.CharField(max_length=30)
    last_built_at = models.DateTimeField(auto_now=True)
    added_at = models.DateTimeField(auto_now_add=True)
    
    def __unicode__(self):
        return self.name
        
class Job(models.Model):
    package = models.ForeignKey(Package)
    job_id = models.CharField(max_length=50) # unique for each job
    repository = models.CharField(max_length=20)
    r_version = models.CharField(max_length=10)
    time_started = models.DateTimeField()
    pkg_url = models.CharField(max_length=200)
    force = models.BooleanField()
    client_id = models.CharField(max_length=30)
    
    def pkg_type(self):
        word = self.os.split(" ")[0]
        if word == "Linux":
            return "src/contrib"
        elif word == "Mac":
            return "bin/macosx/leopard/contrib"
        elif word == "Windows":
            return "bin/windows/contrib"
        return None
    
    
class Build(models.Model):
    RESULT_CHOICES = (
        ('unknown', 'unknown'),
        ('skipped', 'skipped'),
        ('ERROR', 'ERROR'),
        ('WARNINGS', 'WARNINGS'),
        ('TIMEOUT', 'TIMEOUT'),
        ('IN_PROGRESS', 'IN_PROGRESS'),
        ('OK', 'OK'),
    )
    job = models.ForeignKey(Job)
    jid = models.CharField(max_length=50)
    builder_id = models.CharField(max_length=20)
    maintainer = models.CharField(max_length=255)
    version = models.CharField(max_length=10)
    preprocessing_result = models.CharField(max_length=20)
    buildsrc_result = models.CharField(max_length=20, choices=RESULT_CHOICES)
    checkinstall_result = models.CharField(max_length=20, choices=RESULT_CHOICES)
    checksrc_result = models.CharField(max_length=20, choices=RESULT_CHOICES)
    buildbin_result = models.CharField(max_length=20, choices=RESULT_CHOICES)
    postprocessing_result = models.CharField(max_length=20, choices=RESULT_CHOICES)
    svn_cmd = models.TextField()
    check_cmd = models.TextField()
    r_cmd = models.TextField()
    r_buildbin_cmd = models.TextField()
    os = models.CharField(max_length=50)
    arch = models.CharField(max_length=50)
    r_version = models.CharField(max_length=255)
    platform = models.CharField(max_length=255)
    invalid_url = models.BooleanField()
    build_not_required = models.BooleanField()
    build_product = models.CharField(max_length=255)
    filesize = models.DecimalField(max_digits=10, decimal_places=2)

class NodeInfo(models.Model):
    builder_id = models.ForeignKey(Build)
    arch = models.CharField(max_length=20)
    r_version = models.CharField(max_length=50)
    platform = models.CharField(max_length=50)
    os = models.CharField(max_length=50)

class Message(models.Model):
    build = models.ForeignKey(Build)
    build_phase = models.CharField(max_length=20)
    sequence = models.IntegerField()
    retcode = models.IntegerField()
    body = models.TextField()