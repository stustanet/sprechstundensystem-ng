from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def menu_item_active(context, value, display_hide=False):
    view_name = context['request'].resolver_match.view_name

    default = '' if not display_hide else 'display-hide'

    if isinstance(value, list):
        return 'active open' if view_name in value else default

    return 'active open' if view_name == value else default


@register.simple_tag(takes_context=True)
def abs_url(context, view_name, *args, **kwargs):
    # Could add except for KeyError, if rendering the template
    # without a request available.
    return context['request'].build_absolute_uri(
        reverse(view_name, args=args, kwargs=kwargs)
    )
