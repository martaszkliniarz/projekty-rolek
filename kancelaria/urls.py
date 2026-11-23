from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.urls import path, re_path
from django.views.static import serve

from sprawy import views

urlpatterns = [
    path("", views.pulpit, name="pulpit"),
    path("sprawy/", views.lista_spraw, name="lista_spraw"),
    path("sprawy/<int:pk>/", views.sprawa, name="sprawa"),
    path("terminy/", views.terminy, name="terminy"),
    path("terminy/<int:pk>/status/", views.termin_status, name="termin_status"),
    path("czynnosci/<int:pk>/potwierdz/", views.czynnosc_potwierdz, name="czynnosc_potwierdz"),
    path("kalkulator/", views.kalkulator, name="kalkulator"),
    path("konflikt/", views.konflikt, name="konflikt"),
    path("czas/", views.raport_czasu, name="raport_czasu"),
    path("kalendarz/<str:token>.ics", views.kalendarz, name="kalendarz"),
    path("logowanie/", auth_views.LoginView.as_view(), name="login"),
    path("wyloguj/", auth_views.LogoutView.as_view(), name="logout"),
    path("panel/", admin.site.urls),
    # dokumenty dostępne wyłącznie po zalogowaniu
    re_path(r"^pliki/(?P<path>.*)$", login_required(serve), {"document_root": settings.MEDIA_ROOT}),
]
