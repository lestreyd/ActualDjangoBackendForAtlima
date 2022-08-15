from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from atlima_django.location.models import Country, Region, City
from atlima_django.sport.models import Sport
from atlima_django.qualification.models import OfficialQualification

from atlima_django.users.forms import UserAdminChangeForm, UserAdminCreationForm

User = get_user_model()

class UserAdmin(auth_admin.UserAdmin):

    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("name", "email",  "first_name",
                    "last_name",
                    "native_firstname",
                    "native_lastname",
                    "patronym",
                    "native_patronym",
                    "birth_date",
                    "phone",
                    "image",
                    "sex",
                    "photo",
                    "slug",
                    "vk_profile",
                    "fb_profile",
                    "instagram_profile",
                    "country",
                    "region",
                    "city",
                    "strong_hand")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    list_display = ["username", "name", "is_superuser"]
    search_fields = ["name"]


admin.site.register(User, UserAdmin)