from __future__ import annotations

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .models import Car, Customer, Reservation


@receiver(post_migrate)
def create_crm_role_groups(sender, **kwargs) -> None:
    if sender.name != "crm":
        return

    role_permissions = {
        "viewer": ("view",),
        "staff": ("view", "add", "change"),
        "admin": ("view", "add", "change", "delete"),
    }
    model_classes = (Car, Customer, Reservation)
    content_types = {model: ContentType.objects.get_for_model(model) for model in model_classes}

    for role_name, actions in role_permissions.items():
        group, _ = Group.objects.get_or_create(name=role_name)
        permissions = []
        for model in model_classes:
            content_type = content_types[model]
            for action in actions:
                permissions.append(
                    Permission.objects.get(
                        content_type=content_type,
                        codename=f"{action}_{model._meta.model_name}",
                    )
                )
        group.permissions.set(permissions)
