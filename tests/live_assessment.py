
import json
import argparse
import sqlite3
import time
from app import jobs

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--limit-test',action='store_true')
    args=parser.parse_args()
    c=sqlite3.connect(jobs.DB)
    row=c.execute("SELECT year,component,work,question,question_type,response,passage FROM submissions WHERE work='Plaits' ORDER BY id DESC LIMIT 1").fetchone()
    c.close()
    payload=dict(zip(('year','component','work','question','question_type','response','passage'),row))
    if args.limit_test:
        extra='The contrast between the two plaits establishes difference, but their equal ribbon suggests a shared dignity rather than a complete removal of their difference.'
        count=1000-len(payload['response'].split())
        additions=(extra.split()*50)[:count]
        payload['response']+='\n\n'+' '.join(additions)+'.'
        assert len(payload['response'].split())==1000
        jobs.DB=jobs.DB.with_name('word-limit-verification.sqlite3')
        print('ISOLATED 1000-WORD TEST',flush=True)
    job_id=jobs.submit(payload)
    print('JOB',job_id,flush=True)
    last=None
    while True:
        item=jobs.get(job_id)
        state=(item['state'],item['stage'],item['tokens']//100)
        if state!=last:
            print(item['elapsed_seconds'],item['state'],item['stage'],item['tokens'],flush=True)
            last=state
        if item['state']=='failed': raise RuntimeError(item['error'])
        if item['state']=='complete':
            report=item['result']
            assert len(report['semantic_paragraph_reviews'])==report['coverage']['paragraphs']
            assert len(report['ao_indicators'])==4
            assert all(payload['response'][note['start']:note['end']]==note['candidate_line'] for note in report['line_feedback'])
            print('COMPLETE',item['submission_id'],report['result'],report['model_audit']['elapsed_seconds'],flush=True)
            print(json.dumps({'judgement':report['examiner_judgement'],'feedback':report['line_feedback']},ensure_ascii=False),flush=True)
            break
        time.sleep(2)

if __name__=='__main__': main()
