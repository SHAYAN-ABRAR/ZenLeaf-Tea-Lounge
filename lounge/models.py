import hashlib
import secrets
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.urls import reverse

from .illustrations import ILLUSTRATION_CHOICES, illustration_alt


def new_token():
    """An unguessable value for private status links (orders and reservations)."""
    return secrets.token_urlsafe(16)


class Category(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True)
    description = models.CharField(max_length=200, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    class Caffeine(models.TextChoices):
        NONE = "none", "Caffeine-free"
        LOW = "low", "Low caffeine"
        MEDIUM = "medium", "Medium caffeine"
        HIGH = "high", "High caffeine"

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=90, unique=True)
    short_description = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("1.00"))])
    illustration = models.CharField(max_length=40, choices=ILLUSTRATION_CHOICES)
    caffeine = models.CharField(max_length=10, choices=Caffeine.choices, blank=True)  # empty for food
    brew_temperature_c = models.PositiveSmallIntegerField(
        "brewing temperature (°C)", null=True, blank=True,
        validators=[MinValueValidator(40), MaxValueValidator(100)],
    )
    brew_time = models.CharField("steeping time", max_length=20, blank=True, help_text="For example: 2–3 min")
    tasting_notes = models.CharField(max_length=120, blank=True, help_text="Comma-separated, for example: grassy, bright")
    allergens = models.CharField(max_length=120, blank=True, help_text="For example: Contains milk")
    is_listed = models.BooleanField("shown on the menu", default=True)
    is_available = models.BooleanField("available to order", default=True)
    is_featured = models.BooleanField("featured on the home page", default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category__sort_order", "sort_order", "name"]
        indexes = [models.Index(fields=["is_listed", "is_available"])]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("lounge:product", args=[self.slug])

    @property
    def illustration_path(self):
        return f"lounge/img/menu/{self.illustration}.svg"

    @property
    def illustration_alt(self):
        return illustration_alt(self.illustration)

    @property
    def notes_list(self):
        return [note.strip() for note in self.tasting_notes.split(",") if note.strip()]

    @property
    def caffeine_short(self):
        return {"none": "None (caffeine-free)", "low": "Low", "medium": "Medium", "high": "High"}.get(self.caffeine, "")

    @property
    def can_be_ordered(self):
        return self.is_listed and self.is_available


class Order(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        PREPARING = "preparing", "Being prepared"
        READY = "ready", "Ready for pickup"
        COMPLETED = "completed", "Collected"
        CANCELLED = "cancelled", "Cancelled"

    PROGRESS = [Status.RECEIVED, Status.PREPARING, Status.READY, Status.COMPLETED]

    number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    token = models.CharField(max_length=40, unique=True, default=new_token, editable=False)
    # One value per checkout page, so submitting the same form twice can't create two orders.
    checkout_key = models.CharField(max_length=40, unique=True, null=True, blank=True, editable=False)
    customer_name = models.CharField(max_length=80)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    notes = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RECEIVED, db_index=True)
    staff_note = models.CharField("internal note", max_length=500, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    item_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.number or f"Order {self.pk}"

    def get_absolute_url(self):
        return reverse("lounge:order_status", args=[self.token])

    def assign_number(self):
        self.number = f"ZL-{self.pk:05d}"
        self.save(update_fields=["number"])

    @property
    def progress_index(self):
        return self.PROGRESS.index(self.status) if self.status in self.PROGRESS else -1

    @property
    def is_open(self):
        return self.status in (self.Status.RECEIVED, self.Status.PREPARING, self.Status.READY)

    @classmethod
    def place(cls, *, customer_name, email, phone, notes, lines, checkout_key=None):
        """Create an order and its items in one transaction. *lines* are (product, quantity) pairs;
        prices are always read from the database, never from the browser."""
        with transaction.atomic():
            subtotal = sum((product.price * qty for product, qty in lines), Decimal("0"))
            order = cls.objects.create(
                customer_name=customer_name, email=email, phone=phone, notes=notes,
                subtotal=subtotal, item_count=sum(qty for _product, qty in lines),
                checkout_key=checkout_key,
            )
            OrderItem.objects.bulk_create([
                OrderItem(order=order, product=product, product_name=product.name,
                          unit_price=product.price, quantity=qty)
                for product, qty in lines
            ])
            order.assign_number()
        return order


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items")
    product_name = models.CharField(max_length=80)          # kept even if the product is renamed or deleted
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(20)])

    class Meta:
        ordering = ["pk"]

    def __str__(self):
        return f"{self.quantity} × {self.product_name}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class Reservation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        DECLINED = "declined", "Declined"
        CANCELLED = "cancelled", "Cancelled"

    reference = models.CharField(max_length=20, unique=True, null=True, blank=True)
    token = models.CharField(max_length=40, unique=True, default=new_token, editable=False)
    name = models.CharField(max_length=80)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    date = models.DateField(db_index=True)
    time = models.TimeField()
    party_size = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(50)])
    notes = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    guest_message = models.CharField(
        "message to the guest", max_length=300, blank=True,
        help_text="Shown on the guest's status page.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "time"]

    def __str__(self):
        return self.reference or f"Reservation {self.pk}"

    def get_absolute_url(self):
        return reverse("lounge:reservation_status", args=[self.token])

    def assign_reference(self):
        self.reference = f"R-{self.pk:05d}"
        self.save(update_fields=["reference"])

    @property
    def is_active(self):
        return self.status in (self.Status.PENDING, self.Status.CONFIRMED)


class ContactMessage(models.Model):
    class Topic(models.TextChoices):
        GENERAL = "general", "General question"
        FEEDBACK = "feedback", "Feedback"
        GROUP = "group", "Group booking or event"
        OTHER = "other", "Something else"

    name = models.CharField(max_length=80)
    email = models.EmailField()
    topic = models.CharField(max_length=10, choices=Topic.choices, default=Topic.GENERAL)
    message = models.TextField()
    fingerprint = models.CharField(max_length=64, db_index=True, editable=False)
    is_handled = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name}: {self.get_topic_display()}"

    @staticmethod
    def make_fingerprint(email, message):
        normalized = " ".join(message.lower().split())
        return hashlib.sha256(f"{email.lower()}\n{normalized}".encode()).hexdigest()


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)                   # stored in lower case
    source = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
