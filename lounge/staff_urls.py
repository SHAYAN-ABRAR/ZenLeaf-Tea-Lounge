from django.urls import path

from .views import staff

app_name = "staff"

urlpatterns = [
    path("login/", staff.StaffLoginView.as_view(), name="login"),
    path("logout/", staff.StaffLogoutView.as_view(), name="logout"),
    path("", staff.dashboard, name="dashboard"),
    path("products/", staff.product_list, name="products"),
    path("products/new/", staff.product_edit, name="product_new"),
    path("products/<int:pk>/", staff.product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", staff.product_delete, name="product_delete"),
    path("products/<int:pk>/toggle/<str:field>/", staff.product_toggle, name="product_toggle"),
    path("orders/", staff.order_list, name="orders"),
    path("orders/<int:pk>/", staff.order_detail, name="order_detail"),
    path("reservations/", staff.reservation_list, name="reservations"),
    path("reservations/<int:pk>/", staff.reservation_detail, name="reservation_detail"),
    path("messages/", staff.message_list, name="messages"),
    path("messages/<int:pk>/", staff.message_detail, name="message_detail"),
    path("messages/<int:pk>/toggle/", staff.message_toggle, name="message_toggle"),
    path("subscribers/", staff.subscriber_list, name="subscribers"),
    path("subscribers/export.csv", staff.subscriber_export, name="subscriber_export"),
    path("subscribers/<int:pk>/delete/", staff.subscriber_delete, name="subscriber_delete"),
]
