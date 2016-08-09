'''
Created on Aug 9, 2016

@author: Crazylemon
'''

import unittest

class DMIReadTest(unittest.TestCase):
    def test_read_icon(self):
        from byond.DMI import DMI
        assets_prefix = __file__
        print(__file__)
