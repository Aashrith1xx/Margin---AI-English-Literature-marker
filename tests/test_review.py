import json
import tempfile
import unittest
from pathlib import Path
from app.review import review, units
from app.knowledge import build, db_open, metadata, retrieve, descriptor_grid


class WholeResponseTests(unittest.TestCase):
    def test_late_priority_and_exact_offsets(self):
        response=('The image contrasts confinement with freedom.\n\n'
                  'The speaker hesitates before answering.\n\n'
                  'The closing image is very effective and makes the reader feel sad.')
        result=review('How is confinement presented?',response,db_path=Path('missing-test-kb'))
        self.assertEqual(result['coverage']['paragraphs'],3)
        self.assertEqual(result['line_feedback'][0]['paragraph'],3)
        for note in result['line_feedback']:
            self.assertEqual(response[note['start']:note['end']],note['candidate_line'])

    def test_missing_quotes_not_automatically_error(self):
        result=review('How does the writer show tension?',
                      'The speaker pauses before the final reply, delaying the resolution.',db_path=Path('missing-test-kb'))
        self.assertEqual(result['line_feedback'],[])

    def test_whole_excerpt_not_truncated(self):
        response=('A long discussion '+('of the image '*45)+'is very effective.')
        note=review('How is the image used?',response,db_path=Path('missing-test-kb'))['line_feedback'][0]
        self.assertEqual(note['candidate_line'],response)

    def test_single_curly_quotes_and_uncertainty(self):
        result=review('How is silence presented?', 'The phrase ‘silent room’ is important.',
                      passage='The silent room filled with light.', db_path=Path('missing-test-kb'))
        self.assertEqual(result['quote_checks'][0]['status'],'matched_extracted_text')
        result=review('How?', 'He says “unfindable phrase”.',passage='The actual passage.',db_path=Path('missing-test-kb'))
        self.assertIn('needs checking',result['line_feedback'][0]['mistake'])

    def test_sentence_boundaries_keep_original_newlines(self):
        text='  First point.\nSecond point!\n\n  Last point?  '
        spans=units(text)
        self.assertEqual(len(spans),3)
        self.assertEqual(spans[-1]['paragraph'],2)
        self.assertEqual(spans[-1]['line_start'],4)
        for span in spans: self.assertEqual(text[span['start']:span['end']],span['text'])


class KnowledgeTests(unittest.TestCase):
    def test_grid_formatting_dedup_preserves_real_wording(self):
        a=descriptor_grid('heading level 8 her / his effects level 1 response papacambridge footer')
        b=descriptor_grid('heading band 8 her/his effects band 1 response')
        self.assertEqual(a,b)
        self.assertNotEqual(a,descriptor_grid('level 8 their effects level 1 response'))

    def test_future_policy_quarantined(self):
        m=metadata(Path('0475_s26_ms_12.pdf'),'0475/12 Mark scheme 2028 level response understanding')
        self.assertFalse(m['active_policy'])
        self.assertTrue(m['metadata_conflict'])

    def test_duplicate_and_reproducible_build(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'sources'; root.mkdir()
            text='0475/12 Mark scheme 2026\nLevel 1 response understanding language analysis.'
            (root/'a.txt').write_text(text)
            (root/'b.txt').write_text(text)
            db=Path(temp)/'kb.db'
            first=build(root,db); second=build(root,db)
            self.assertEqual(first,second)
            c=db_open(db)
            try:
                manifests=[json.loads(r[0]) for r in c.execute('select manifest from documents')]
                self.assertEqual(len({m['canonical_resource_id'] for m in manifests}),1)
                self.assertEqual(c.execute('select count(*) from search').fetchone()[0],1)
                hits=retrieve('understanding',component='12',db_path=db)
                self.assertEqual(len(hits),1)
                (root/'a.txt').unlink()
                build(root,db)
                self.assertEqual(len(retrieve('understanding',component='12',db_path=db)),1)
                (root/'b.txt').unlink()
                build(root,db)
                self.assertEqual(retrieve('understanding',db_path=db),[])
            finally: c.close()

if __name__=='__main__': unittest.main()
