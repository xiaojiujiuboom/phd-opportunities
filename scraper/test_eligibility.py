import unittest
from datetime import date
from eligibility import filter_phds


class PublicationPolicyTests(unittest.TestCase):
    today = date(2026, 9, 27)

    def filter(self, **kwargs):
        job = dict(title="PhD in plasma physics", deadline="2026-10-01", profile="R1")
        job.update(kwargs)
        return filter_phds([job], today=self.today, observed_at="2026-04-20T13:33:22Z")

    def test_today_is_inclusive(self):
        self.assertEqual(len(self.filter(deadline="2026-09-27")[0]), 1)

    def test_expired(self):
        self.assertEqual(self.filter(deadline="2026-09-26")[1], {"expired": 1})

    def test_closed_future_deadline(self):
        self.assertEqual(self.filter(status="filled")[1], {"closed": 1})

    def test_stale_undated(self):
        self.assertEqual(self.filter(deadline=None)[1], {"undated_stale": 1})

    def test_recent_undated_not_claimed_open(self):
        kept, _ = self.filter(deadline=None, last_seen="2026-09-25")
        self.assertEqual(kept[0]["status"], "deadline_unspecified")

    def test_undated_expires_after_seven_days(self):
        self.assertEqual(self.filter(deadline=None, last_seen="2026-09-19")[1], {"undated_stale": 1})

    def test_future_observation_not_valid(self):
        self.assertEqual(self.filter(deadline=None, last_seen="2027-01-01")[1], {"undated_stale": 1})

    def test_bad_deadline(self):
        self.assertEqual(self.filter(deadline="rolling")[1], {"invalid_deadline": 1})

    def test_r1_does_not_imply_phd(self):
        self.assertEqual(self.filter(title="Research scientist")[1], {"phd_not_confirmed": 1})

    def test_mixed_role_needs_review(self):
        self.assertEqual(self.filter(title="PhD / Postdoc in plasma")[1], {"mixed_or_non_phd_role": 1})

    def test_professor_with_phd_requirement_is_excluded(self):
        self.assertEqual(self.filter(title="Assistant Professor (PhD required)")[1], {"mixed_or_non_phd_role": 1})

    def test_multilingual_titles(self):
        for title in ["Ph.D. position", "Doctoral researcher", "Doktorand i fysik", "Promovendus", "Doctorant en physique", "Stipendiat i fysikk"]:
            with self.subTest(title=title):
                self.assertEqual(len(self.filter(title=title)[0]), 1)


if __name__ == "__main__":
    unittest.main()
