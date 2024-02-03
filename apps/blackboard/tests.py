from django.test import TestCase

# Create your tests here.
# 编写一个简单测试，测试 1+1 = 2 ?
class SimpleTest(TestCase):
    def test_add(self):
        self.assertEqual(1 + 1, 2)  # 1+1=2