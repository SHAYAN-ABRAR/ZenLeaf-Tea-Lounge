from django.urls import path

from .views import public

app_name = "lounge"

urlpatterns = [
    path("", public.home, name="home"),
    path("menu/", public.menu, name="menu"),
    path("menu/<slug:slug>/", public.product_detail, name="product"),
    path("cart/", public.cart_view, name="cart"),
    path("cart/add/", public.cart_add, name="cart_add"),
    path("cart/update/", public.cart_update, name="cart_update"),
    path("checkout/", public.checkout, name="checkout"),
    path("orders/<str:token>/", public.order_status, name="order_status"),
    path("reserve/", public.reserve, name="reserve"),
    path("reservations/<str:token>/", public.reservation_status, name="reservation_status"),
    path("reservations/<str:token>/cancel/", public.reservation_cancel, name="reservation_cancel"),
    path("contact/", public.contact, name="contact"),
    path("newsletter/", public.newsletter_signup, name="newsletter"),
    path("about/", public.about, name="about"),
]
