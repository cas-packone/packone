from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from clouds.models import Cloud

#TODO allow user's teammates to access his/her resources
class Profile(models.Model):
    owner=models.ForeignKey(User,on_delete=models.CASCADE,editable=False)
    avatar=models.CharField(max_length=100,blank=True,null=True)
    organization=models.CharField(max_length=50)
    remark = models.CharField(blank=True,null=True,max_length=100)
    enabled=models.BooleanField(default=False)
    def __str__(self):
        return "{}/{}".format(self.owner,self.organization)
    class Meta:
        unique_together = ('owner', 'organization')

class Balance(models.Model): #todo add balance allocate/retrieve
    cloud=models.ForeignKey(Cloud,on_delete=models.CASCADE)
    profile=models.ForeignKey(Profile,on_delete=models.CASCADE)
    balance=models.IntegerField(validators=[MinValueValidator(0)],default=0)
    modified_time=models.DateTimeField(auto_now=True)
    def __str__(self):
        return "{}/{}".format(self.profile, self.cloud)
    class Meta:
        unique_together = ('profile', 'cloud')

class Credential(models.Model):
    profile=models.ForeignKey(Profile,on_delete=models.CASCADE)
    ssh_user=models.CharField(max_length=50,default='root')
    ssh_public_key=models.CharField(max_length=5048,blank=True,null=True) #todo add length restrction
    ssh_passwd=models.CharField(max_length=50,blank=True,null=True)
    def __str__(self):
        return "{}/{}".format(self.profile, self.ssh_user)
    class Meta:
        unique_together = ('profile', 'ssh_user')