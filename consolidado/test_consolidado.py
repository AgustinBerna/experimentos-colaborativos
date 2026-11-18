import csv,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class ConsolidadoTests(unittest.TestCase):
 def rows(self,name):
  with (ROOT/'datos'/name).open(encoding='utf-8') as f:return list(csv.DictReader(f))
 def test_completitud_semillas_y_metodos(self):
  rows=self.rows('metricas_por_semilla.csv');self.assertEqual(len(rows),780)
  groups={r['method_uid'] for r in rows};self.assertEqual(len(groups),26)
  sets=[{r['seed'] for r in rows if r['method_uid']==g} for g in groups]
  self.assertTrue(all(len(s)==30 and s==sets[0] for s in sets))
 def test_controles_sin_doble_conteo(self):
  rows=self.rows('controles_reproducidos.csv');self.assertEqual(len(rows),8)
  self.assertTrue(all(float(r['max_gain_diff'])==0 and float(r['max_auc_diff'])<1e-10 for r in rows))
 def test_familias_holm(self):
  rows=self.rows('tests_pareados_holm.csv');self.assertEqual(len(rows),294)
  groups={tuple(r[k] for k in ['family','test_family','metric']) for r in rows}
  for g in groups:
   rs=sorted([r for r in rows if tuple(r[k] for k in ['family','test_family','metric'])==g],key=lambda r:float(r['p_raw']))
   self.assertTrue(all(int(r['family_size'])==len(rs) for r in rs))
   ps=[float(r['p_holm']) for r in rs]
   self.assertEqual(ps,sorted(ps));self.assertTrue(all(float(r['p_raw'])<=float(r['p_holm'])<=1 for r in rs))
 def test_definiciones_no_fusionadas(self):
  rows=self.rows('resumen_unificado.csv');lookup={r['method_uid']:r for r in rows}
  self.assertNotEqual(lookup['EXP1::FF_MED_PRE']['gain_ensemble'],lookup['EXP1::FF_MED_POST']['gain_ensemble'])
  e0=lookup['EXP1::E0'];self.assertNotEqual(e0['gain_mean'],e0['gain_ensemble'])
  self.assertTrue(all(not r['method'].startswith('E12') for r in rows))
if __name__=='__main__':unittest.main()
