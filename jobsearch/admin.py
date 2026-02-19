from django.contrib import admin
from django.db.models.query import QuerySet
from django.http import JsonResponse
from django.urls import path
from django.utils import timezone
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
        "applied_checkbox",
        "scraped_at",
        "updated_at",
    )
    search_fields = ("company",)
    readonly_fields = ("scraped_at", "updated_at")
    actions = [convert_to_bad]

    class Media:
        js = ("jobsearch/admin/autosave_applied.js",)

    def display_url(self, obj):
        return format_html('<a href="{}">{}</a>', obj.url, obj.source)

    def applied_checkbox(self, obj):
        checked = "checked" if obj.is_applied else ""
        return format_html(
            '<input type="checkbox" class="autosave-applied" data-id="{}" {}>',
            obj.pk,
            checked,
        )

    applied_checkbox.short_description = "Applied"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "toggle-applied/<int:pk>/",
                self.admin_site.admin_view(self.toggle_applied_view),
            )
        ]
        return custom + urls

    def toggle_applied_view(self, request, pk):
        value = request.POST.get("value") == "1"
        JobPosting.objects.filter(pk=pk).update(
            is_applied=value,
            updated_at=timezone.now(),
        )
        return JsonResponse({"status": "ok"})


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
