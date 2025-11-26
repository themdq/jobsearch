from django.contrib import admin
from django.db.models.query import QuerySet
from django.utils.html import format_html

from .models import BadJob, JobPosting


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
    list_display = ("url",)
