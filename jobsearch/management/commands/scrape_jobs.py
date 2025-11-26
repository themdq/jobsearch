import time
import traceback

from django.core.management.base import BaseCommand

from jobsearch.models import BadJob, JobPosting
from jobsearch.utils import google_search, parse_ashby, parse_greenhouse, parse_lever

QUERY = '"data engineer"'
# QUERY = '"analytics engineer"'


class Command(BaseCommand):
    help = "Scrape Google Custom Search results and save jobs into JobPosting table"

    def handle(self, *args, **options):
        self.stdout.write("Running static job scrape...")

        found_new = []
        start = 1

        try:
            while True:
                results, queries_meta = google_search(QUERY, start=start, num=10)
                if not results:
                    break

                for res in results:
                    link = str(res["link"])
                    if "lever" in link:
                        link = "/".join(link.split("/")[:5])

                    # если уже есть — пропускаем
                    if (
                        JobPosting.objects.filter(url=link).exists()
                        or BadJob.objects.filter(url=link).exists()
                    ):
                        continue
                    try:
                        if "greenhouse" in link:
                            company, title, location, description, date_posted = (
                                parse_greenhouse(link)
                            )
                            source = "greenhouse"
                        elif "lever" in link:
                            company, title, location, description, date_posted = (
                                parse_lever(link)
                            )
                            source = "lever"
                        elif "ashbyhq" in link:
                            company, title, location, description, date_posted = (
                                parse_ashby(link)
                            )
                            source = "ashby"
                        else:
                            continue

                    except Exception as e:
                        self.stderr.write(f"Failed fetch {link}: {e}")
                        continue

                    if str(location) in ["India"]:
                        BadJob.objects.create(url=link)

                    else:
                        jp = JobPosting.objects.create(
                            url=link,
                            company=company,
                            title=title or res.get("title") or "",
                            location=location,
                            description=description,
                            source=source,
                            posted_date=date_posted,
                        )
                        found_new.append(jp)

                    # не спамим сайты
                    time.sleep(1.0)

                # пагинация Google API
                next_info = queries_meta.get("nextPage")
                if next_info and isinstance(next_info, list):
                    start = next_info[0].get("startIndex")
                    if not start:
                        break
                else:
                    break

        except Exception as e:
            self.stderr.write(f"Fatal error: {e}")
            traceback.print_exc()
            return

        # финальный вывод
        self.stdout.write(f"Added {len(found_new)} new job postings.")
        if found_new:
            for jp in found_new:
                self.stdout.write(f" - {jp.title} | {jp.url}")
