import unittest
from details import parse_details, clean_html


class DetailTests(unittest.TestCase):
    def test_academics_keeps_all_sections_and_actual_deadline(self):
        html = '''<script type="application/ld+json">[{"@type":"JobPosting","description":"Partial","datePosted":"2026-09-14T22:00:00Z","validThrough":"2026-11-09"}]</script>
        <p>Published: 2026-09-15</p><div class="html-content"><h2>Job description:</h2><p>Introduction</p></div>
        <div class="html-content"><p>Working hours: 30</p><p>Application deadline: 10/15/2026</p></div>'''
        detail = parse_details(html, 'https://www.academics.com/jobs/example', 'academics')
        self.assertIn('Introduction', detail['description_html'])
        self.assertIn('Working hours: 30', detail['description_html'])
        self.assertEqual(detail['posted'], '2026-09-15')
        self.assertEqual(detail['deadline'], '2026-10-15')

    def test_jobsac_description_and_ordinal_date(self):
        detail = parse_details('<div id="job-description"><p>Scientific computing</p></div><p>Closes: 4th October 2026</p>', 'https://www.jobs.ac.uk/job/example', 'jobsac_uk')
        self.assertIn('Scientific computing', detail['description_html'])
        self.assertEqual(detail['deadline'], '2026-10-04')

    def test_untrusted_html_is_sanitized(self):
        body = clean_html('<p onclick="bad()">Hello<script>bad()</script><a href="javascript:bad()">bad</a><a href="/apply">Apply</a></p>', 'https://example.org/job')
        self.assertNotIn('script', body)
        self.assertNotIn('onclick', body)
        self.assertIn('https://example.org/apply', body)

    def test_euraxess_offer_section(self):
        detail = parse_details('<nav>Menu</nav><div><h2 id="offer-description">Offer Description</h2><p>PhD in power electronics</p></div>', 'https://euraxess.ec.europa.eu/jobs/1', 'euraxess')
        self.assertIn('power electronics', detail['description_html'])
        self.assertNotIn('Menu', detail['description_html'])


if __name__ == '__main__':
    unittest.main()
