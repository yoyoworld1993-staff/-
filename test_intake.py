import unittest
from intake import parse_clipboard

class TestClipboard(unittest.TestCase):
    def test_jpy_and_chinese_reference(self):
        item=parse_clipboard("KK scale 1/18 Pontiac LeMans GTO 1972\n15,500日元（参考价：682人民币）\nhttps://auctions.yahoo.co.jp/jp/auction/r12345")
        self.assertEqual(item["bid_jpy"],15500)
        self.assertEqual(item["platform"],"Yahoo Auctions")
        self.assertIn("Pontiac",item["title"])
    def test_no_unfounded_price(self):
        item=parse_clipboard("模型车\n参考价：682人民币")
        self.assertIsNone(item["bid_jpy"])
    def test_fixed_price(self):
        item=parse_clipboard("京商 Ferrari F40 1/64\n一口价 3,500円")
        self.assertEqual(item["bid_jpy"],3500)
        self.assertEqual(item["kind"],"一口价")

if __name__ == "__main__":
    unittest.main()
