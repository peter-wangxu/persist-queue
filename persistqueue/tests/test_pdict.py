
import shutil
import tempfile
import unittest

from persistqueue import pdict


class PDictTest(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp(suffix='pdict')

    def tearDown(self):
        shutil.rmtree(self.path, ignore_errors=True)

    def test_unsupported(self):
        pd = pdict.PDict(self.path, 'pd')
        pd['key_a'] = 'value_a'
        self.assertRaises(NotImplementedError, pd.keys)
        self.assertRaises(NotImplementedError, pd.iterkeys)
        self.assertRaises(NotImplementedError, pd.values)
        self.assertRaises(NotImplementedError, pd.itervalues)
        self.assertRaises(NotImplementedError, pd.items)
        self.assertRaises(NotImplementedError, pd.iteritems)

        def _for():
            for _ in pd:
                pass
        self.assertRaises(NotImplementedError, _for)

    def test_add(self):
        pd = pdict.PDict(self.path, 'pd')
        pd['key_a'] = 'value_a'
        self.assertEqual(pd['key_a'], 'value_a')
        self.assertTrue('key_a' in pd)
        self.assertFalse('key_b' in pd)
        self.assertEqual(pd.get('key_a'), 'value_a')
        self.assertEqual(pd.get('key_b'), None)
        self.assertEqual(pd.get('key_b', 'absent'), 'absent')
        self.assertRaises(KeyError, lambda: pd['key_b'])
        pd['key_b'] = 'value_b'
        self.assertEqual(pd['key_a'], 'value_a')
        self.assertEqual(pd['key_b'], 'value_b')

    def test_set(self):
        pd = pdict.PDict(self.path, 'pd')
        pd['key_a'] = 'value_a'
        pd['key_b'] = 'value_b'
        self.assertEqual(pd['key_a'], 'value_a')
        self.assertEqual(pd['key_b'], 'value_b')
        self.assertEqual(pd.get('key_a'), 'value_a')
        self.assertEqual(pd.get('key_b', 'absent'), 'value_b')
        pd['key_a'] = 'value_aaaaaa'
        self.assertEqual(pd['key_a'], 'value_aaaaaa')
        self.assertEqual(pd['key_b'], 'value_b')

    def test_delete(self):
        pd = pdict.PDict(self.path, 'pd')
        pd['key_a'] = 'value_a'
        pd['key_b'] = 'value_b'
        self.assertEqual(pd['key_a'], 'value_a')
        self.assertEqual(pd['key_b'], 'value_b')
        del pd['key_a']
        self.assertFalse('key_a' in pd)
        self.assertRaises(KeyError, lambda: pd['key_a'])
        self.assertEqual(pd['key_b'], 'value_b')

    def test_two_dicts(self):
        pd_1 = pdict.PDict(self.path, '1')
        pd_2 = pdict.PDict(self.path, '2')
        pd_1['key_a'] = 'value_a'
        pd_2['key_b'] = 'value_b'
        self.assertEqual(pd_1['key_a'], 'value_a')
        self.assertEqual(pd_2['key_b'], 'value_b')
        self.assertRaises(KeyError, lambda: pd_1['key_b'])
        self.assertRaises(KeyError, lambda: pd_2['key_a'])
