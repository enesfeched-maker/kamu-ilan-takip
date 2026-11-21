import json
import unittest

import tek_paylasim


class AnketTesti(unittest.TestCase):
    def test_anket_gorsele_yanit_olur_ve_oy_degistirilebilir(self):
        govde = json.loads(tek_paylasim.anket_govdesi({'soru': 'Soru?', 'secenekler': ['Evet', 'Hayır']}, '-1', 7))
        self.assertEqual(govde['reply_parameters'], {'message_id': 7})
        self.assertEqual(govde['options'], [{'text': 'Evet'}, {'text': 'Hayır'}])
        self.assertEqual(govde['type'], 'regular')
        self.assertTrue(govde['allows_revoting'])

    def test_dugmesiz_gorselde_klavye_gonderilmez(self):
        govde, _ = tek_paylasim.govde_hazirla({'foto': None}, '-1')
        self.assertNotIn(b'reply_markup', govde)

class IkiliDugmeTesti(unittest.TestCase):
    def test_tek_dugmeler_ikiser_yan_yana_site_dugmesi_tek(self):
        d = [[['A', 'u']], [['B', 'u']], [['C', 'u']], [['🌐 Tüm kamu ilanları', 'u']]]
        self.assertEqual([[x[0] for x in s] for s in tek_paylasim._ikili(d)], [['A', 'B'], ['C'], ['🌐 Tüm kamu ilanları']])

    def test_cok_dugmeli_satir_bozulmaz(self):
        d = [[['A', 'u']], [['B', 'u'], ['C', 'u']], [['D', 'u']], [['E', 'u']]]
        self.assertEqual([[x[0] for x in s] for s in tek_paylasim._ikili(d)], [['A'], ['B', 'C'], ['D', 'E']])


if __name__ == '__main__':
    unittest.main()
