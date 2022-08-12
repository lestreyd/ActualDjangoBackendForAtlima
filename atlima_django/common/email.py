from django.db import models
from parler.models import TranslatedFields, TranslatableModel


class EmailTemplate(TranslatableModel):
    """Template for Email"""

    translatable = TranslatedFields(
        template_name=models.CharField(
            max_length=256
        ),
        description=models.TextField(),
        text=models.TextField()
    )

    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        sid = str(self.id)
        return f"email_template{sid}"
