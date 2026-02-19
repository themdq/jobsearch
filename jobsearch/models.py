from django.db import models


class JobPosting(models.Model):
    url = models.URLField(unique=True)
    company = models.CharField(max_length=500, blank=True)
    title = models.CharField(max_length=1000, blank=True)
    location = models.CharField(max_length=500, blank=True)
    posted_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    scraped_at = models.DateTimeField(auto_now=True)

    is_applied = models.BooleanField(default=False)
    apply_date = models.DateField(null=True, blank=True)

    source = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.title or self.url}"


class BadJob(models.Model):
    url = models.URLField(unique=True)
    company = models.CharField(max_length=500, blank=True)
    title = models.CharField(max_length=1000, blank=True)
    location = models.CharField(max_length=500, blank=True)
    posted_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    scraped_at = models.DateTimeField(auto_now=True)

    source = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.title or self.url}"


class BadCompany(models.Model):
    name = models.CharField(max_length=500, unique=True)

    def __str__(self) -> str:
        return self.name


class BadLocation(models.Model):
    pattern = models.CharField(
        max_length=500,
        unique=True,
        help_text="Case-insensitive substring to block (e.g. 'London', 'EMEA')",
    )

    def __str__(self) -> str:
        return self.pattern


# class Alert(models.Model):
#     """
#     Настраиваемые алерты: можно создать правило, например
#     ключевые слова, исключения, после какой даты, адреса email.
#     """
#     name = models.CharField(max_length=200)
#     query = models.CharField(max_length=1000, help_text='Полный Google-запрос (например: (site:jobs.lever.co OR ...) "data engineer" after:2025-11-13 -senior ...)')
#     recipients = models.TextField(help_text='Comma-separated emails')
#     active = models.BooleanField(default=True)
#     last_run = models.DateTimeField(null=True, blank=True)

#     def recipient_list(self):
#         return [e.strip() for e in self.recipients.split(',') if e.strip()]

#     def __str__(self):
#         return self.name
