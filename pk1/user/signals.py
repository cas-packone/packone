from secrets import token_urlsafe
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, post_delete, pre_delete
from django.contrib.auth.models import User
from .import models

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        models.Profile(owner=instance, enabled=True, remark='auto created').save()

@receiver(pre_save, sender=models.Credential)
def credential_pre_save(sender, instance, **kwargs):
    if not instance.pk:
        if not instance.ssh_passwd:
            instance.ssh_passwd = token_urlsafe(15)

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
