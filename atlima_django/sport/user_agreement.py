from django.db import models
from parler.models import TranslatedFields, TranslatableModel


class UserAgreement(TranslatableModel):
    """
    User Agreement model with content, title
    and description fields in content field
    """
    document_version = models.IntegerField(
        null=False, blank=False
    )
    slug = models.SlugField(
        max_length=64, unique=True
    )
    created = models.DateField(auto_now_add=True)
    updated = models.DateField(auto_now=True)
    content = TranslatedFields(
        content=models.TextField()
    )

    def __str__(self):
        return (
            f"{self.pk}_{self.document_version}"
        )
