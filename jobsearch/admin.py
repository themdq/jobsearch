from django.contrib import admin
from django.db.models.query import QuerySet
from django.utils.html import format_html

from jobsearch.utils import move_company_to_bad

from .models import BadCompany, BadJob, BadLocation, JobPosting


@admin.action(description="Convert to Bad Jobs")
def convert_to_bad(modeladmin, request, queryset: QuerySet[JobPosting]):
    for item in queryset:
        BadJob.objects.create(url=item.url)
        item.delete()


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "company",
        "location",
        "posted_date",
        "display_url",
        "is_applied",
        "scraped_at",
    )
    list_editable = ("is_applied",)
    search_fields = ("title", "company", "content", "location", "url")
    readonly_fields = ("scraped_at",)
    search_fields = ("company",)
    actions = [convert_to_bad]

    def display_url(self, obj):
        return format_html('<a href="{}">{}</a>', obj.url, obj.source)


@admin.register(BadJob)
class BadJobAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "location", "url")
    search_fields = ("company", "url")


@admin.register(BadLocation)
class BadLocationAdmin(admin.ModelAdmin):
    list_display = ("pattern",)
    search_fields = ("pattern",)


@admin.register(BadCompany)
class BadCompanyAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            count = move_company_to_bad(obj.name)
            self.message_user(request, f"Moved {count} job(s) from '{obj.name}' to Bad Jobs.")
