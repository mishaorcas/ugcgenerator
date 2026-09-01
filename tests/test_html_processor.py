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
        self.assertIn('<author prop="additional" social_id="77">', result)
        self.assertNotIn("author-ugc", result)

    def test_plain_name_is_converted(self) -> None:
        source = "<p>John Doe</p>\n<p>Author description</p>"
        result = process_html(source)
        self.assertIn('<author name="John Doe"', result)
        self.assertIn('<author name="John Doe" prop="additional" img="">', result)
        self.assertNotIn("author-ugc", result)

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
        self.assertIn('<bubble surface="positive">', result)
        self.assertIn('<bubble surface="negative">', result)

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
        self.assertTrue(result.startswith("<author>"))

    def test_existing_empty_author_is_filled(self) -> None:
        source = (
            "<author>\n"
            "    <description></description>\n"
            "</author>\n\n"
            "<p>{Ольга Карасева}(https://t-j.ru/user2111814)</p>\n"
            "<p>выслушала обе стороны</p>\n"
            "<lead>Текст лида</lead>"
        )
        result = process_html(source)
        self.assertEqual(result.count("<author>"), 1)
        self.assertIn("<description>выслушала обе стороны</description>", result)
        self.assertNotIn("<description></description>", result)
        self.assertNotIn("{Ольга Карасева}", result)

    def test_empty_author_without_data_is_removed(self) -> None:
        source = (
            "<author>\n"
            "    <description></description>\n"
            "</author>\n\n"
            "<p>Просто текст</p>"
        )
        result = process_html(source)
        self.assertNotIn("<author>", result)
        self.assertIn("<p>Просто текст</p>", result)

    def test_contents_assigns_ids_to_h2_headers(self) -> None:
        source = (
            "<contents-title>О чем поговорим</contents-title>\n"
            "<contents>\n"
            "    <li>{Как понять, что кофе действительно хороший и качественный?}(#one)</li>\n"
            "    <li>{Как отличить арабику от робусты?}(#two)</li>\n"
            "    <li>{<nobr>Могут ли</nobr> кофейные производители маскировать некачественное сырье?}(#three)</li>\n"
            "</contents>\n\n"
            "<h2>Как понять, что кофе действительно хороший и качественный?</h2>\n\n"
            "<h2>Как отличить арабику от робусты?</h2>\n\n"
            "<h2><nobr>Могут ли</nobr> кофейные производители маскировать некачественное сырье?</h2>"
        )
        result = process_html(source)
        self.assertIn('id="one"', result)
        self.assertIn('id="two"', result)
        self.assertIn('id="three"', result)
        self.assertIn('<h2 id="one">Как понять', result)
        self.assertIn('<h2 id="two">Как отличить', result)
        self.assertIn('<h2 id="three"><nobr>Могут ли</nobr>', result)
        self.assertIn("<contents>", result)
        self.assertIn("</contents>", result)

    def test_contents_without_contents_block_is_unchanged(self) -> None:
        source = "<h2>Без оглавления</h2>"
        result = process_html(source)
        self.assertNotIn('id="', result)
        self.assertIn("<h2>Без оглавления</h2>", result)

    def test_contents_with_many_headers(self) -> None:
        source = (
            "<contents>\n"
            "    <li>{Первый заголовок}(#a)</li>\n"
            "    <li>{Второй заголовок}(#b)</li>\n"
            "    <li>{Третий заголовок}(#c)</li>\n"
            "    <li>{Четвёртый заголовок}(#d)</li>\n"
            "    <li>{Пятый заголовок}(#e)</li>\n"
            "</contents>\n\n"
            "<h2>Первый заголовок</h2>\n\n"
            "<h2>Второй заголовок</h2>\n\n"
            "<h2>Третий заголовок</h2>\n\n"
            "<h2>Четвёртый заголовок</h2>\n\n"
            "<h2>Пятый заголовок</h2>"
        )
        result = process_html(source)
        self.assertIn('id="one"', result)
        self.assertIn('id="two"', result)
        self.assertIn('id="three"', result)
        self.assertIn('id="four"', result)
        self.assertIn('id="five"', result)

    def test_contents_preserves_existing_h2_attributes(self) -> None:
        source = (
            "<contents>\n"
            "    <li>{Заголовок}(#x)</li>\n"
            "</contents>\n\n"
            '<h2 class="special">Заголовок</h2>'
        )
        result = process_html(source)
        self.assertIn('id="one"', result)
        self.assertIn('class="special"', result)

    def test_contents_fallback_to_anchors_when_texts_dont_match(self) -> None:
        source = (
            "<contents-title>Отзывы туристов о Вьетнаме</contents-title>\n"
            "<contents>\n"
            "    <li>{Отзыв № 1: низкие цены}(#one)</li>\n"
            "    <li>{Отзыв № 2: комфортное автобусное сообщение }(#two)</li>\n"
            "    <li>{Отзыв № 3: толпы российских туристов}(#three)</li>\n"
            "</contents>\n\n"
            "<h2>\n"
            "    <label position=\"top\">Отзыв № 1</label>\n"
            "    👍 «Цены очень адекватные даже в приличных заведениях»\n"
            "</h2>\n\n"
            "<h2>\n"
            "    <label position=\"top\">Отзыв № 2</label>\n"
            "    👍 «Считаю Вьетнам лучшей страной региона»\n"
            "</h2>\n\n"
            "<h2>\n"
            "    <label position=\"top\">Отзыв № 3</label>\n"
            "    🤏 «Несносно много туристов из России»\n"
            "</h2>"
        )
        result = process_html(source)
        self.assertIn('id="one"', result)
        self.assertIn('id="two"', result)
        self.assertIn('id="three"', result)
        self.assertIn('<h2 id="one">', result)
        self.assertIn('<h2 id="two">', result)
        self.assertIn('<h2 id="three">', result)
        self.assertIn("<contents>", result)
        self.assertIn("</contents>", result)

    def test_emoji_plus_replaced_with_image_tag(self) -> None:
        source = '<h2>➕ Хорошее оснащение и множество модификаций</h2>'
        result = process_html(source)
        self.assertIn('<image src="plus-icon" />', result)
        self.assertIn('Хорошее оснащение и множество модификаций', result)
        self.assertNotIn('➕', result)

    def test_emoji_minus_replaced_with_image_tag(self) -> None:
        source = '<h2>➖ Хорошее оснащение и множество модификаций</h2>'
        result = process_html(source)
        self.assertIn('<image src="minus-icon" />', result)
        self.assertIn('Хорошее оснащение и множество модификаций', result)
        self.assertNotIn('➖', result)

    def test_h2_without_emoji_unchanged(self) -> None:
        source = '<h2>Просто заголовок</h2>'
        result = process_html(source)
        self.assertNotIn('<image', result)
        self.assertIn('<h2>Просто заголовок</h2>', result)


if __name__ == "__main__":
    unittest.main()