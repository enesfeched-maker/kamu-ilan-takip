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


if __name__ == '__main__':
    unittest.main()
