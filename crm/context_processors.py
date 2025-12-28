from django.conf import settings


def crm_contact_settings(request):
    return {
        "whatsapp_number": getattr(settings, "WHATSAPP_NUMBER", ""),
    }
