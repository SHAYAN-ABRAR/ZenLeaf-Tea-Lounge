"""The shopping cart lives in the visitor's server-side session: product IDs and quantities only.
Names and prices are always read from the database when the cart is shown or checked out."""
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings

from .models import Product

SESSION_KEY = "cart"


@dataclass
class CartLine:
    product: Product
    quantity: int

    @property
    def line_total(self):
        return self.product.price * self.quantity

    @property
    def problem(self):
        if not self.product.is_listed:
            return "This item is no longer on the menu."
        if not self.product.is_available:
            return "This item is sold out right now."
        return ""


class Cart:
    def __init__(self, request):
        self.session = request.session
        raw = self.session.get(SESSION_KEY, {})
        self.items = {}
        for key, quantity in raw.items():
            key = str(key)
            if key.isascii() and key.isdigit() and isinstance(quantity, int) and quantity > 0:
                self.items[key] = quantity

    @property
    def max_quantity(self):
        return settings.ZENLEAF["MAX_ITEM_QUANTITY"]

    def _save(self):
        self.session[SESSION_KEY] = self.items
        self.session.modified = True

    def quantity_of(self, product_id):
        return self.items.get(str(product_id), 0)

    def add(self, product, quantity=1):
        new = min(self.quantity_of(product.pk) + max(quantity, 1), self.max_quantity)
        self.items[str(product.pk)] = new
        self._save()
        return new

    def set(self, product_id, quantity):
        quantity = max(0, min(int(quantity), self.max_quantity))
        if quantity == 0:
            self.items.pop(str(product_id), None)
        else:
            self.items[str(product_id)] = quantity
        self._save()
        return quantity

    def remove(self, product_id):
        self.items.pop(str(product_id), None)
        self._save()

    def clear(self):
        self.items = {}
        self._save()

    def __len__(self):
        return sum(self.items.values())

    def lines(self):
        """Cart lines in menu order. Items whose product was deleted are dropped from the cart."""
        products = Product.objects.select_related("category").filter(pk__in=[int(k) for k in self.items])
        found = {str(p.pk): p for p in products}
        missing = set(self.items) - set(found)
        if missing:
            for key in missing:
                self.items.pop(key, None)
            self._save()
        return [CartLine(found[k], q) for k, q in sorted(
            self.items.items(), key=lambda kv: (found[kv[0]].category.sort_order, found[kv[0]].sort_order, found[kv[0]].name)
        )]

    @staticmethod
    def subtotal(lines):
        return sum((line.line_total for line in lines), Decimal("0"))
