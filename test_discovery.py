import unittest
from discovery import parse_mercari_html, parse_yahoo_html, allowed_link, extract_price

class TestDiscovery(unittest.TestCase):
    def test_price(self):
        self.assertEqual(extract_price("現在 ¥ 12,500 円"), 12500)
        self.assertEqual(extract_price("9,900円"), 9900)
        self.assertIsNone(extract_price("即決"))
    def test_mercari(self):
        html = '<div data-testid="item-cell"><a href="/item/m12345678901">トミカ 限定版 <span>¥2,500</span></a></div>'
        products = parse_mercari_html(html)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["price_jpy"], 2500)
        self.assertEqual(products[0]["kind"], "一口价")
        self.assertTrue(products[0]["url"].startswith("https://jp.mercari.com/item/"))
    def test_yahoo(self):
        html = '<div class="Product"><a class="Product__titleLink" href="https://page.auctions.yahoo.co.jp/jp/auction/r123456">トミカ R32</a><div class="Product__priceInfo"><span class="Product__price">3,500円</span></div></div>'
        products = parse_yahoo_html(html)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["price_jpy"], 3500)
        self.assertEqual(products[0]["end_at"], "")
    def test_foreign_host_rejected(self):
        self.assertEqual(allowed_link("https://evil.example/item/m12345678", "jp.mercari.com"), "")
        self.assertEqual(allowed_link("http://jp.mercari.com/item/m12345678", "jp.mercari.com"), "")

if __name__ == "__main__":
    unittest.main()
