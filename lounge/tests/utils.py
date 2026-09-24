from io import StringIO

from django.core.management import call_command

from lounge.models import Product


def seed():
    """Load the demo menu the same way `python manage.py seed_demo` does."""
    call_command("seed_demo", stdout=StringIO())


def product(slug):
    return Product.objects.get(slug=slug)
