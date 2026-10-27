
import json
import sqlite3
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from .core import assess, connect

DB=Path(__file__).resolve().parents[1]/'work'/'examiner.sqlite3'
EXECUTOR=ThreadPoolExecutor(max_workers=1,thread_name_prefix='margin-marker')

def open_db():
    c=connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS assessment_jobs (
        id TEXT PRIMARY KEY, request_id TEXT UNIQUE, created REAL NOT NULL, updated REAL NOT NULL,
        state TEXT NOT NULL, stage TEXT NOT NULL, tokens INTEGER NOT NULL DEFAULT 0,
        payload TEXT NOT NULL, result TEXT, error TEXT, submission_id INTEGER)""")
    c.commit()
    return c

def validate_payload(payload):
    if not isinstance(payload,dict): raise ValueError('Expected an assessment form.')
    allowed={'question','response','year','component','work','question_type','passage'}
    if set(payload)-allowed: raise ValueError('Unexpected assessment fields.')
    result={key:payload.get(key,'') for key in allowed}
    for key in allowed-{'year'}:
        if result[key] is None: result[key]=''
        if not isinstance(result[key],str): raise ValueError('Invalid '+key)
    if result['year'] not in {2026,2027}: raise ValueError('Select 2026 or 2027.')
    for key in ('question','response'):
        if not result[key].strip(): raise ValueError('Enter the '+key+' before assessment.')
    from .limits import check_response_limit
    check_response_limit(result['response'])
    if result['question_type'] not in {'essay','passage-based','unseen poetry','unseen prose','open-text drama'}:
        raise ValueError('Select a valid question type.')
    if result['question_type'].startswith('unseen') and not result['passage'].strip():
        raise ValueError('Include the unseen passage.')
    return result

def update(job_id,**values):
    values['updated']=time.time()
    c=open_db()
    try:
        c.execute('UPDATE assessment_jobs SET '+','.join(key+'=?' for key in values)+' WHERE id=?',
                  (*values.values(),job_id))
        c.commit()
    finally: c.close()

def run(job_id,payload):
    update(job_id,state='running',stage='Reading the essay and retrieving relevant sources')
    try:
        report=assess(**payload,progress=lambda stage,tokens=0:update(job_id,stage=stage,tokens=tokens))
        c=open_db()
        try:
            cursor=c.execute('INSERT INTO submissions(year,component,work,question,question_type,response,passage,result_json) VALUES(?,?,?,?,?,?,?,?)',
                (payload['year'],payload['component'],payload['work'],payload['question'],payload['question_type'],
                 payload['response'],payload['passage'],json.dumps(report,ensure_ascii=False)))
            c.execute("UPDATE assessment_jobs SET state='complete',stage='Report saved',updated=?,result=?,submission_id=? WHERE id=?",
                      (time.time(),json.dumps(report,ensure_ascii=False),cursor.lastrowid,job_id))
            c.commit()
        finally: c.close()
    except Exception as exc:
        update(job_id,state='failed',stage='Assessment needs attention',error=str(exc))

def submit(payload,request_id=None):
    payload=validate_payload(payload)
    request_id=request_id or uuid.uuid4().hex
    if not isinstance(request_id,str) or len(request_id)>100: raise ValueError('Invalid request identifier.')
    c=open_db()
    try:
        job_id=uuid.uuid4().hex
        now=time.time()
        cursor=c.execute("INSERT OR IGNORE INTO assessment_jobs(id,request_id,created,updated,state,stage,payload) VALUES(?,?,?,?,'queued','Waiting for the local model',?)",
                         (job_id,request_id,now,now,json.dumps(payload,ensure_ascii=False)))
        c.commit()
        if cursor.rowcount==0:
            return c.execute('SELECT id FROM assessment_jobs WHERE request_id=?',(request_id,)).fetchone()['id']
    finally: c.close()
    EXECUTOR.submit(run,job_id,payload)
    return job_id

def get(job_id):
    c=open_db()
    try: row=c.execute('SELECT * FROM assessment_jobs WHERE id=?',(job_id,)).fetchone()
    finally: c.close()
    if row is None: return None
    item=dict(row)
    item['payload']=json.loads(item['payload'])
    item['result']=json.loads(item['result']) if item['result'] else None
    end=item['updated'] if item['state'] in {'complete','failed'} else time.time()
    item['elapsed_seconds']=round(end-item['created'])
    return item

def recover():
    c=open_db()
    try:
        c.execute("UPDATE assessment_jobs SET state='failed',stage='Server restarted',error='The server restarted during assessment. Your response is saved. Use Retry assessment.',updated=? WHERE state='running'",(time.time(),))
        queued=c.execute("SELECT id,payload FROM assessment_jobs WHERE state='queued' ORDER BY created").fetchall()
        c.commit()
    finally: c.close()
    for row in queued: EXECUTOR.submit(run,row['id'],json.loads(row['payload']))
