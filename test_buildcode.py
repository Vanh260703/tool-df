import unittest

from buildcode import extract_builds, normalize


class ExtractBuildsTest(unittest.TestCase):
    def test_share_format(self):
        [b] = extract_builds("CI-19 Assault Rifle-Warfare-6HNEL2G0EIPHRNLI0J8JI")
        self.assertEqual((b.weapon, b.mode, b.code), ("CI-19 Assault Rifle", "Warfare", "6HNEL2G0EIPHRNLI0J8JI"))

    def test_strips_leading_text(self):
        [b] = extract_builds("build ngon nè: K437 Assault Rifle-Operations-6HNEL2G0EIPHRNLI0J8JI")
        self.assertEqual(b.weapon, "K437 Assault Rifle")

    def test_bare_code_and_multiple(self):
        builds = extract_builds("k437 rush\n6HNEL2G0EIPHRNLI0J8JI\nM4A1 Assault Rifle-Warfare-6GABCDEF0123456789XY")
        self.assertEqual([b.code for b in builds], ["6HNEL2G0EIPHRNLI0J8JI", "6GABCDEF0123456789XY"])
        self.assertIsNone(builds[0].weapon)
        self.assertEqual(builds[0].note, "k437 rush")

    def test_notes_scoped_per_code(self):
        builds = extract_builds(
            "CI19 nhạc\nCI-19 Assault Rifle-Chiến Dịch (Thoát Hiểm)-6LFHP280AHP1JR9CHG3OI\n\n"
            "K437 full\nK437 Assault Rifle-Chiến Dịch (Thoát Hiểm)-6LFHT2C0AHP1JR9CHG3OI\n"
            "SVD Sniper Rifle-Chiến Dịch (Thoát Hiểm)-6LFI1OC0AHP1JR9CHG3OI"
        )
        self.assertEqual([b.note for b in builds], ["CI19 nhạc", "K437 full", None])
        self.assertEqual(builds[1].mode, "Chiến Dịch (Thoát Hiểm)")
        self.assertNotIn("k437", builds[2].search_text())

    def test_no_match_across_fields(self):
        [b] = extract_builds("K416\nK416 Assault Rifle-Chiến Dịch (Thoát Hiểm)-6LETEL00AHP1JR9CHG3OI")
        self.assertNotIn("mk4", b.search_text())

    def test_bare_code_uses_same_line(self):
        [b] = extract_builds("code mk4 auto 6LM10M40DRSVSN7A25PBI")
        self.assertEqual(b.note, "code mk4 auto")

    def test_ignores_plain_words(self):
        self.assertEqual(extract_builds("HELLOOOOOOOOOOOOOOOOOO anh em"), [])

    def test_normalize(self):
        self.assertEqual(normalize("K437 Assault Rifle"), "k437assaultrifle")
        self.assertEqual(normalize("Súng Đẹp"), "sungdep")


if __name__ == "__main__":
    unittest.main()
