from secrets import token_urlsafe
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, post_delete, pre_delete
from django.contrib.auth.models import User
from .import models
from time import sleep

@receiver(post_save, sender=User)
def profile_auto_create(sender, instance, created, **kwargs):
    if created:
        models.Profile(owner=instance, enabled=True, remark='auto created').save()

@receiver(post_save, sender=models.Profile)
def credential_auto_create(sender, instance, created, **kwargs):
    if created:
        models.Credential(profile=instance,ssh_passwd = token_urlsafe(15)).save()

@receiver(pre_save, sender=models.Credential)
def credential_update(sender, instance, **kwargs):
    if instance.pk:
        old = models.Credential.objects.get(pk=instance.pk)
        if old.ssh_passwd!=instance.ssh_passwd:
            for ins in instance.profile.owner.instance_set.all():
                ins.remedy("echo 'root:{}' | chpasswd".format(instance.ssh_passwd),manual=False)
        if old.ssh_public_key!=instance.ssh_public_key:
            for ins in instance.profile.owner.instance_set.all():
                ins.remedy("echo '{}'>>/root/.ssh/authorized_keys".format(instance.ssh_public_key),manual=False)

@receiver(pre_delete, sender=models.Credential)
def credential_pre_delete(sender, instance, **kwargs):
    if instance.ssh_user=='root':
        raise Exception('cannot delete credentials of root')

@receiver(pre_save, sender=models.Profile)
def profile_pre_save(sender, instance, **kwargs):
    if instance.enabled:
        sender.objects.filter(enabled=True,owner=instance.owner).update(enabled=False)

@receiver(post_save, sender=models.Cloud)
def add_admin_balance(sender, instance, created, **kwargs):
    if created:  
        models.Balance(
            cloud=instance,
            profile=instance.owner.profile_set.filter(enabled=True).first(),
            balance=1000000
        ).save()
