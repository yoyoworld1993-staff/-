import unittest
from streamlit.testing.v1 import AppTest

class AppSmokeTest(unittest.TestCase):
    def test_no_exception_on_first_mobile_page(self):
        page = AppTest.from_file("app.py", default_timeout=30).run()
        problems = [str(x.message) for x in page.exception]
        self.assertEqual(problems, [], "首页渲染异常：" + " | ".join(problems))

if __name__ == "__main__":
    unittest.main()
