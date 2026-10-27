import json
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch
from app.server import Handler, LocalServer


class PersistenceTests(unittest.TestCase):
    def test_async_api_persists_and_enforces_word_limit(self):
        from app import jobs
        with tempfile.TemporaryDirectory() as temp, patch('app.server.DB',Path(temp)/'saved.db'), patch.object(jobs,'DB',Path(temp)/'saved.db'):
            server=LocalServer(('127.0.0.1',0),Handler)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            base='http://127.0.0.1:'+str(server.server_address[1])
            payload={'year':2026,'component':'12','work':'Plaits','question_type':'essay','question':'How?','passage':'','response':' '.join(['word']*1000)}
            try:
                with patch.object(jobs,'assess',return_value={'result':{'mark':12}}):
                    request=urllib.request.Request(base+'/api/jobs',json.dumps({'assessment':payload}).encode(),{'Content-Type':'application/json'})
                    with urllib.request.urlopen(request,timeout=5) as response:
                        self.assertEqual(response.status,202);job_id=json.load(response)['job_id']
                    deadline=time.monotonic()+5
                    while time.monotonic()<deadline:
                        with urllib.request.urlopen(base+'/api/jobs/'+job_id,timeout=5) as response:item=json.load(response)
                        if item['state']=='complete':break
                        time.sleep(.02)
                    self.assertEqual(item['state'],'complete')
                    self.assertEqual(len(item['payload']['response'].split()),1000)
                payload['response']+=' extra'
                request=urllib.request.Request(base+'/api/jobs',json.dumps({'assessment':payload}).encode(),{'Content-Type':'application/json'})
                with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(request,timeout=5)
                self.assertEqual(error.exception.code,400)
            finally:
                server.shutdown();server.server_close();thread.join(timeout=5)

    def test_whole_review_survives_saved_assessment(self):
        with tempfile.TemporaryDirectory() as temp, patch('app.server.DB',Path(temp)/'saved.db'):
            server=LocalServer(('127.0.0.1',0),Handler)
            thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
            base='http://127.0.0.1:'+str(server.server_address[1])
            try:
                payload={'year':2026,'component':'42','work':'','question_type':'unseen poetry',
                         'question':'How does the writer present conflict?',
                         'response':'The opening contrasts light with darkness.\n\nThe final image is very effective.',
                         'passage':'The light went out. Darkness remained.'}
                request=urllib.request.Request(base+'/api/mark',json.dumps(payload).encode(),
                                               {'Content-Type':'application/json'})
                marked_result={'assessment':{'question':payload['question'],'year':2026,'component':'42','work':'','question_type':'unseen poetry'},'result':{'mark':12,'maximum_mark':25,'indicative_level':4},'semantic_paragraph_reviews':[{'paragraph':1,'judgement':'Opening reviewed'},{'paragraph':2,'judgement':'Ending reviewed'}], 'line_feedback':[{'paragraph':2,'candidate_line':'The final image is very effective.'}]}
                with patch('app.server.assess',return_value=marked_result):
                    with urllib.request.urlopen(request,timeout=30) as response: marked=json.load(response)
                self.assertEqual(len(marked['semantic_paragraph_reviews']),2)
                self.assertEqual(marked['line_feedback'][0]['paragraph'],2)
                with urllib.request.urlopen(base+'/api/submissions',timeout=10) as response: saved=json.load(response)
                sid=saved['submissions'][0]['id']
                with urllib.request.urlopen(base+'/api/submissions/'+str(sid),timeout=10) as response: reopened=json.load(response)
                self.assertEqual(reopened['response'],payload['response'])
                self.assertEqual(reopened['result']['semantic_paragraph_reviews'],marked['semantic_paragraph_reviews'])
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=5)

if __name__=='__main__': unittest.main()
