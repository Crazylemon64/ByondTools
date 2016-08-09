'''
Created on Feb 18, 2015

@author: Rob
'''
import unittest

class ListParserTests(unittest.TestCase):
    def setUp(self):
        from byond.script.dmscript import DreamSyntax
        self.syntax = DreamSyntax(list_only=True, simplify_lists=True)

    def test_syntax_associative(self):
        testString = 'list("apple"=1, "b"="c")'

        result = self.syntax.ParseString(__file__,testString)

        self.assertEqual(result['apple'], 1)
        self.assertEqual(result['b'], 'c')

    def test_syntax_nonassociative_nums(self):
        testString = 'list(2,0,8,3)'

        result = self.syntax.ParseString(__file__,testString)

        self.assertEqual(result[0], 2)
        self.assertEqual(result[1], 0)
        self.assertEqual(result[2], 8)
        self.assertEqual(result[3], 3)

    def test_syntax_nonassociative_mixed(self):
        testString = 'list("waffle",23,"q",4.5)'

        result = self.syntax.ParseString(__file__,testString)

        self.assertEqual(result[0], "waffle")
        self.assertEqual(result[1], 23)
        self.assertEqual(result[2], "q")
        self.assertEqual(result[3], 4.5)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
