from __future__ import annotations

import unittest

try:
    from improved_version.html_processor import process_html
except ModuleNotFoundError:
    from html_processor import process_html


class HtmlProcessorTests(unittest.TestCase):
    def test_author_with_link_is_converted(self) -> None:
        source = "<p>{John Doe}(https://site.example/user77)</p>\n<p>Short bio</p>"
        result = process_html(source)
        self.assertIn('social_id="77"', result)
        self.assertIn("<description>Short bio</description>", result)

    def test_plain_name_is_converted(self) -> None:
        source = "<p>John Doe</p>\n<p>Author description</p>"
        result = process_html(source)
        self.assertIn('<author-ugc name="John Doe"', result)

    def test_regular_paragraph_pair_is_not_converted(self) -> None:
        source = "<p>First paragraph</p>\n<p>Second paragraph</p>"
        result = process_html(source)
        self.assertNotIn("<author-ugc", result)
        self.assertIn("<p>First paragraph</p>", result)

    def test_hl_surface_switches_by_header(self) -> None:
        source = (
            "<h2>\U0001F44D Pros</h2>\n"
            "<hl>A\nB</hl>\n"
            "<h2>\U0001F44E Cons</h2>\n"
            "<hl>C</hl>"
        )
        result = process_html(source)
        self.assertIn('<hl isbuble="true" surface="positive">', result)
        self.assertIn('<hl isbuble="true" surface="negative">', result)

    def test_link_without_user_id_is_not_converted(self) -> None:
        source = "<p>{John Doe}(https://site.example/profile)</p>\n<p>Bio</p>"
        result = process_html(source)
        self.assertNotIn("<author-ugc", result)

    def test_primary_author_before_lead_is_converted_to_author(self) -> None:
        source = (
            "<p>За и против: <span>стоит&nbsp;ли</span> поддерживать связь с бывшими одноклассниками</p>\n\n"
            "<p>Аргументы читателей</p>\n\n"
            "<p>{Ольга Карасева}(https://t-j.ru/user2111814)</p>\n\n"
            "<p>выслушала обе стороны</p>\n\n"
            "<lead><nobr>Кто-то</nobr> после окончания школы остается на связи с бывшими "
            "одноклассниками, а <nobr>кто-то</nobr> принципиально их избегает.</lead>"
        )
        result = process_html(source)
        self.assertIn("<author>", result)
        self.assertIn("<description>выслушала обе стороны</description>", result)
        self.assertNotIn("{Ольга Карасева}", result)
        self.assertNotIn("<author-ugc", result.split("<lead>", 1)[0])
        self.assertIn("<lead><nobr>Кто-то</nobr>", result)


if __name__ == "__main__":
    unittest.main()
