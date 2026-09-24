from django.core.management.base import BaseCommand
from django.db import transaction

from lounge.models import Category, Product
from lounge.seed_data import CATEGORIES, PRODUCTS


class Command(BaseCommand):
    help = (
        "Load the illustrative demo menu. Only missing categories and products are added, so running it "
        "again never overwrites changes made in the staff area. Use --reset to restore the demo values."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true",
            help="Also reset existing demo products (price, availability, text) to their seed values.",
        )

    @transaction.atomic
    def handle(self, *args, reset=False, **options):
        categories = {}
        for slug, name, description, order in CATEGORIES:
            category, _ = Category.objects.get_or_create(
                slug=slug, defaults={"name": name, "description": description, "sort_order": order},
            )
            if reset:
                category.name, category.description, category.sort_order = name, description, order
                category.save()
            categories[slug] = category

        created = updated = 0
        for (slug, cat, name, short, description, price, illustration, caffeine, temperature, brew_time,
             notes, allergens, available, featured, order) in PRODUCTS:
            values = {
                "category": categories[cat], "name": name, "short_description": short,
                "description": description, "price": price, "illustration": illustration,
                "caffeine": caffeine, "brew_temperature_c": temperature, "brew_time": brew_time,
                "tasting_notes": notes, "allergens": allergens, "is_listed": True,
                "is_available": available, "is_featured": featured, "sort_order": order,
            }
            product = Product.objects.filter(slug=slug).first()
            if product is None:
                Product.objects.create(slug=slug, **values)
                created += 1
            elif reset:
                for field, value in values.items():
                    setattr(product, field, value)
                product.save()
                updated += 1

        kept = len(PRODUCTS) - created - updated
        self.stdout.write(self.style.SUCCESS(
            f"Demo menu ready: {created} product(s) added, {updated} reset, {kept} left unchanged "
            f"({Product.objects.count()} products in the database)."
        ))
