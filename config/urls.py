from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.authtoken.views import obtain_auth_token
from atlima_django.frontend.api.views import AvailableLanguagePackages, SpecificLanguageContent

from atlima_django.location.api.views import (CountryManager, 
                                              CountrySearch, 
                                              RegionSearch,
                                              CitySearch)

from atlima_django.users.api.views import GetMyProfileInfo, Signin, CheckUserExists
from atlima_django.system.api.views import GetLegal

urlpatterns = [
    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    path(
        "about/", TemplateView.as_view(template_name="pages/about.html"), name="about"
    ),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("atlima_django.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    # Static file serving when using Gunicorn + Uvicorn for local web socket development
    urlpatterns += staticfiles_urlpatterns()

# API URLS
urlpatterns += [
    # API base url
    path("api/", include("config.api_router")),
    # DRF auth token
    path("auth-token/", obtain_auth_token),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
]

# Location Search API for Atlima
urlpatterns += [
    # Countries
    path("country/<country_id>", 
         CountryManager.as_view(), 
         name="country-by-id"),
    path("search-country",
         CountrySearch.as_view(),
         name="country-search"),
    path("search-region",
         RegionSearch.as_view(),
         name='region-search'),
    path("search-city",
         CitySearch.as_view(),
         name="search-city")
]


# Вход и получение профиля
urlpatterns += [
    path("get-profile",
         GetMyProfileInfo.as_view(),
         name='get-profile'),
    path("signin",
         Signin.as_view(),
         name="signin"),
    path("check-user-by-name",
        CheckUserExists.as_view(),
        name="check-user-exist")
]


# Frontend translations
# фронтенд запрашивает языки и получает
# в ответ JSON, заранее заполненный и помещённый на 
# сервер
urlpatterns += [
    path("language-packages",
        AvailableLanguagePackages.as_view(),
        name = "language-packages"),
    path("language-packages-content",
        AvailableLanguagePackages.as_view(),
        name = "language-packages"),
    path("specific-language-package",
         SpecificLanguageContent.as_view(),
         name="specific-language-package"),   
]


# API для получения оферт и ПС
urlpatterns += [
    path("legal", GetLegal.as_view(), name="get-legal")
]




if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
