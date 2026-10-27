import copy
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from app.local_model import report_schema, validate_report
from app import jobs

def fixture():
    response='The opening is tense.\n\nThe ending is very effective.'
    from app.review import units
    sentences={f'S{i+1}':s for i,s in enumerate(units(response))}
    data={'paragraphs':[{'id':'P1'},{'id':'P2'}],'sources':{'primary':{}},
          'rubric':'level 4 13 12 11 demonstrates knowledge level 0 0 insufficient'}
    output={'mark':12,'judgement':'An uneven response.','strengths':'Relevant reference.',
            'next_band':'Develop the analysis.','final_remarks':'Analyse the ending.',
            'paragraph_reviews':{'P1':'The opening is relevant.','P2':'The ending needs explanation.'},
            'ao_reviews':{f'AO{i}':'Some relevant evidence.' for i in range(1,5)},
            'feedback':[{'sentence_id':'S2','title':'Specify the effect','mistake':'The effect is asserted.',
                         'why_it_matters':'Analysis is limited.','improvement':'Explain a specific effect.',
                         'model_line':'The ending creates uncertainty.','next_action':'Analyse the image.',
                         'source_ids':['primary']}]}
    return response,sentences,data,output

class ReportContractTests(unittest.TestCase):
    def test_rewrite_is_recovered_and_unverified_context_is_qualified(self):
        response,sentences,data,output=fixture()
        note=output['feedback'][0]
        note['model_line']='The ending is very effective.'
        note['next_action']="Replace with: 'The final image leaves the conflict unresolved.'"
        note['mistake']='This historical context is historically inaccurate.'
        result=validate_report(output,data,sentences,response)['feedback'][0]
        self.assertEqual(result['model_line'],'The final image leaves the conflict unresolved.')
        self.assertIn('not verified',result['mistake'])
        self.assertEqual(result['context_claim_status'],'unverified_in_supplied_material')
    def test_exact_candidate_line_is_resolved_from_original_offsets(self):
        response,sentences,data,output=fixture()
        result=validate_report(output,data,sentences,response)
        self.assertEqual(result['feedback'][0]['candidate_line'],'The ending is very effective.')
        self.assertEqual(result['feedback'][0]['location'],'Paragraph 2, source line 3')
        self.assertEqual(result['level'],4)

    def test_schema_requires_every_paragraph_and_ao(self):
        response,sentences,data,output=fixture()
        schema=report_schema(data,sentences)
        self.assertEqual(schema['properties']['paragraph_reviews']['required'],['P1','P2'])
        del output['paragraph_reviews']['P2']
        with self.assertRaisesRegex(ValueError,'Incomplete paragraph_reviews'):
            validate_report(output,data,sentences,response)

    def test_unknown_sentence_and_source_are_rejected(self):
        response,sentences,data,output=fixture()
        bad=copy.deepcopy(output); bad['feedback'][0]['sentence_id']='S100'
        with self.assertRaisesRegex(ValueError,'Unknown candidate line'):
            validate_report(bad,data,sentences,response)
        output['feedback'][0]['source_ids']=['invented']
        with self.assertRaisesRegex(ValueError,'Unknown source citation'):
            validate_report(output,data,sentences,response)

class DurableJobTests(unittest.TestCase):
    payload={'year':2026,'component':'42','work':'','question_type':'unseen poetry',
             'question':'How is conflict presented?','response':'A response.','passage':'A passage.'}
    def wait_for(self,job_id):
        until=time.monotonic()+5
        while time.monotonic()<until:
            item=jobs.get(job_id)
            if item['state'] in {'complete','failed'}: return item
            time.sleep(.02)
        self.fail('Job did not terminate')

    def test_saved_result_is_independent_of_browser_and_duplicate_click(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(jobs,'DB',Path(temp)/'jobs.db'):
            with patch.object(jobs,'assess',return_value={'result':{'mark':12}}):
                job_id=jobs.submit(self.payload,'one-click')
                self.assertEqual(jobs.submit(self.payload,'one-click'),job_id)
                item=self.wait_for(job_id)
            self.assertEqual(item['state'],'complete')
            self.assertEqual(item['result']['result']['mark'],12)
            c=jobs.open_db()
            self.assertEqual(c.execute('SELECT count(*) FROM submissions').fetchone()[0],1)
            c.close()

    def test_failure_keeps_response_for_retry(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(jobs,'DB',Path(temp)/'jobs.db'):
            with patch.object(jobs,'assess',side_effect=RuntimeError('Model offline')):
                item=self.wait_for(jobs.submit(self.payload))
            self.assertEqual(item['state'],'failed')
            self.assertEqual(item['payload']['response'],self.payload['response'])
            self.assertIn('offline',item['error'])

if __name__=='__main__': unittest.main()
