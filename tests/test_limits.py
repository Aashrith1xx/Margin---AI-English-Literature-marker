import unittest
from app.core import assess
from app.jobs import validate_payload
from app.limits import word_count
from app.local_model import packet

class ResponseLimitTests(unittest.TestCase):
    def payload(self,count):
        return {'year':2026,'component':'12','work':'Plaits','question_type':'essay',
                'question':'How is unity presented?','response':' '.join(['word']*count),'passage':''}

    def test_boundary_accepts_1000_rejects_1001(self):
        for count in (999,1000):
            self.assertEqual(word_count(validate_payload(self.payload(count))['response']),count)
        with self.assertRaisesRegex(ValueError,'remove 1 word'):
            validate_payload(self.payload(1001))
        with self.assertRaisesRegex(ValueError,'limit is 1,000'):
            assess(**self.payload(1001))

    def test_full_1000_word_response_reaches_model_packet(self):
        response=' '.join(['analysis']*999+['FINALWORD'])
        evidence={'rubric_context':[{'descriptor_text':'level 4 13 12 11 demonstrates knowledge'}],
                  'paragraph_reviews':[{'paragraph':1,'candidate_text':response,
                                        'retrieved_evidence':[],'human_annotations':[]}]}
        data,sentences,removed=packet('How? ',response,2026,'12','Plaits','essay','',evidence)
        model_text=' '.join(item['text'] for item in data['candidate_sentences'].values())
        self.assertEqual(word_count(model_text),1000)
        self.assertTrue(model_text.endswith('FINALWORD'))
        self.assertEqual(len(sentences),1)

    def test_whitespace_word_count(self):
        self.assertEqual(word_count('  a\tb\nc\n\nd\u00a0e  '),5)

    def test_unrelated_candidate_example_is_not_textual_evidence(self):
        evidence={'rubric_context':[{'descriptor_text':'level 4 13 12 11 knowledge'}],
                  'paragraph_reviews':[{'paragraph':1,'candidate_text':'An interpretation.',
                    'retrieved_evidence':[{'provenance':'candidate_response','passage_id':'other-poem'}],
                    'human_annotations':[]}]}
        data,_,_=packet('How?','An interpretation.',2026,'12','Plaits','essay','The primary text.',evidence)
        self.assertEqual(list(data['sources']),['primary_passage'])

if __name__=='__main__': unittest.main()
