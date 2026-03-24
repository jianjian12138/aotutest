from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Project, ProjectMember
from apps.api_testing.models import ApiProject
from apps.ui_automation.models import UiProject

@receiver(post_save, sender=Project)
def sync_project_to_modules(sender, instance, created, **kwargs):
    """
    Sync core_platform.Project to module-specific projects.
    """
    # Sync to API Testing if applicable
    if instance.project_type == 'API':
        ApiProject.objects.update_or_create(
            name=instance.name,
            defaults={
                'description': instance.description,
                'status': 'IN_PROGRESS' if instance.status == 'active' else 'COMPLETED',
                'owner': instance.owner,
            }
        )
    
    # Sync to UI Automation if applicable
    elif instance.project_type == 'UI':
        # UI module status choices differ slightly
        UiProject.objects.update_or_create(
            name=instance.name,
            defaults={
                'description': instance.description,
                'status': 'IN_PROGRESS' if instance.status == 'active' else 'COMPLETED',
                'owner': instance.owner,
                'base_url': 'http://target-url.com' # Default placeholder
            }
        )

@receiver(post_save, sender=ProjectMember)
def sync_members_to_modules(sender, instance, created, **kwargs):
    """
    Sync members when they are added to a core project.
    """
    project = instance.project
    user = instance.user
    
    if project.project_type == 'API':
        api_proj = ApiProject.objects.filter(name=project.name).first()
        if api_proj:
            api_proj.members.add(user)
            
    elif project.project_type == 'UI':
        ui_proj = UiProject.objects.filter(name=project.name).first()
        if ui_proj:
            ui_proj.members.add(user)

@receiver(post_delete, sender=ProjectMember)
def remove_members_from_modules(sender, instance, **kwargs):
    """
    Remove members from module projects when deleted from core.
    """
    project = instance.project
    user = instance.user
    
    if project.project_type == 'API':
        api_proj = ApiProject.objects.filter(name=project.name).first()
        if api_proj:
            api_proj.members.remove(user)
            
    elif project.project_type == 'UI':
        ui_proj = UiProject.objects.filter(name=project.name).first()
        if ui_proj:
            ui_proj.members.remove(user)
