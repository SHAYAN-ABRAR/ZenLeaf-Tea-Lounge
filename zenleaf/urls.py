from django.urls import include, path

urlpatterns = [
    path("staff/", include("lounge.staff_urls")),
    path("", include("lounge.urls")),
]

handler404 = "lounge.views.public.page_not_found"
handler500 = "lounge.views.public.server_error"
