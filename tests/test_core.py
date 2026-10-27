import tempfile, unittest
from unittest.mock import patch
from pathlib import Path
from app.core import SOURCE_ROOT, annotation_records, assess, ingest

class CoreTests(unittest.TestCase):
 def test_question_required(self):
  with self.assertRaises(ValueError): assess('', 'answer', 2026, None, None, 'essay', None)
 def test_year_guard(self):
  with self.assertRaises(ValueError): assess('How?', 'answer', 2028, None, None, 'essay', None)
 def test_line_specific_feedback_is_limited_and_grounded(self):
  from tests.test_local_model import fixture
  from app.local_model import validate_report
  response,sentences,data,output=fixture()
  result=validate_report(output,data,sentences,response)
  self.assertLessEqual(len(result['feedback']),3)
  self.assertIn(result['feedback'][0]['candidate_line'],response)
 def test_annotated_drama_survives(self):
  records=annotation_records(SOURCE_ROOT/'texts_and_analysis/drama/_OceanofPDF.com_Blues_for_an_Alabama_Sky_-_Pearl_Cleage.pdf')
  self.assertGreaterEqual(sum(x['subtype']=='Highlight' for x in records), 100)
 def test_annotated_prose_survives(self):
  records=annotation_records(SOURCE_ROOT/'texts_and_analysis/prose/things-fall-apart.pdf')
  self.assertGreaterEqual(sum(x['subtype']=='Highlight' for x in records), 350)
 def test_ingestion(self):
  with tempfile.TemporaryDirectory() as d:
   result=ingest(SOURCE_ROOT,Path(d)/'x.sqlite3'); self.assertGreater(result['annotations'],400)
if __name__=='__main__': unittest.main()
