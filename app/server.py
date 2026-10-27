from __future__ import annotations
import json
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse
from .core import SOURCE_ROOT, assess, connect, ingest

ROOT=Path(__file__).resolve().parents[1]; DB=ROOT/'work'/'examiner.sqlite3'
INGEST_LOCK = Lock()
class LocalServer(ThreadingHTTPServer):
    
    allow_reuse_address = False
    def server_bind(self):
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

class Handler(BaseHTTPRequestHandler):
    def reply(self, status, data, content='application/json'):
        raw=data.encode() if isinstance(data,str) else json.dumps(data,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type',content+'; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/health':
            from .limits import MAX_RESPONSE_WORDS
            return self.reply(200,{'app':'Margin','version':'2026.10.14-word-limit-v2','max_response_words':MAX_RESPONSE_WORDS})
        
        
        if path=='/': return self.reply(200,(ROOT/'app'/'index.html').read_text(encoding='utf-8'),'text/html')
        if path=='/app.js': return self.reply(200,(ROOT/'app'/'app.js').read_text(encoding='utf-8'),'application/javascript')
        if path=='/api/dashboard':
            c=connect(DB)
            try:
                return self.reply(200,{"resources":[dict(r) for r in c.execute('select kind,count(*) count from resources group by kind')],"annotations":c.execute('select count(*) from annotations').fetchone()[0],"rubrics":c.execute('select count(*) from rubrics').fetchone()[0]})
            finally: c.close()
        if path=='/api/model-status':
            from .local_model import status
            return self.reply(200,status())
        if path.startswith('/api/jobs/'):
            from .jobs import get
            job=get(path.rsplit('/',1)[1])
            return self.reply(200,job) if job else self.reply(404,{'error':'Assessment job not found'})
        if path=='/api/knowledge':
            from .knowledge import DEFAULT_DB, db_open
            from contextlib import closing
            with closing(db_open(DEFAULT_DB)) as c:
                manifests=[json.loads(r[0]) for r in c.execute('SELECT manifest FROM documents')]
                return self.reply(200,{'resources':len(manifests),
                    'pages':c.execute('SELECT count(*) FROM pages').fetchone()[0],
                    'annotations':c.execute('SELECT count(*) FROM notes').fetchone()[0],
                    'rubrics':c.execute('SELECT count(*) FROM rubrics').fetchone()[0],
                    'manifest':manifests,'semantic_model_configured':(ROOT/'local_model.json').exists()})
        if path=='/api/submissions':
            c=connect(DB)
            try:
                rows=c.execute('select id,created_at,year,component,work,question,question_type,result_json from submissions order by id desc limit 50').fetchall()
                return self.reply(200,{"submissions":[{**dict(r),"result":json.loads(r["result_json"] or '{}')} for r in rows]})
            finally: c.close()
        if path.startswith('/api/submissions/'):
            try: submission_id=int(path.rsplit('/',1)[1])
            except ValueError: return self.reply(400,{"error":"Invalid saved assessment id"})
            c=connect(DB)
            try:
                row=c.execute('select * from submissions where id=?',(submission_id,)).fetchone()
                if not row: return self.reply(404,{"error":"Saved assessment not found"})
                return self.reply(200,{**dict(row),"result":json.loads(row["result_json"] or '{}')})
            finally: c.close()
        self.reply(404,{"error":"Not found"})
    def do_POST(self):
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length>2_000_000: return self.reply(413,{'error':'Assessment form is too large'})
            payload=json.loads(self.rfile.read(length))
            if self.path=='/api/jobs':
                from .jobs import submit
                job_id=submit(payload.get('assessment'),payload.get('request_id'))
                return self.reply(202,{'job_id':job_id})
            if self.path=='/api/ingest':
                with INGEST_LOCK:
                    from .knowledge import build
                    root=Path(payload.get('root',SOURCE_ROOT))
                    result=ingest(root,DB)
                    result['knowledge_pipeline']=build(root)
                    return self.reply(200,result)
            if self.path=='/api/mark':
                result=assess(**payload); c=connect(DB)
                try:
                    c.execute('insert into submissions(year,component,work,question,question_type,response,passage,result_json) values(?,?,?,?,?,?,?,?)',(payload.get('year'),payload.get('component'),payload.get('work'),payload['question'],payload['question_type'] if payload.get('question_type') else 'essay',payload['response'],payload.get('passage'),json.dumps(result))); c.commit()
                finally: c.close()
                return self.reply(200,result)
            self.reply(404,{"error":"Not found"})
        except (ValueError,KeyError) as e: self.reply(400,{"error":str(e)})
        except Exception as e:
            from .local_model import ModelUnavailable
            if isinstance(e,ModelUnavailable): return self.reply(503,{"error":str(e)})
            self.reply(500,{"error":type(e).__name__,"detail":str(e)})
if __name__=='__main__':
    from .jobs import recover
    recover()
    print('Open http://127.0.0.1:8765'); LocalServer(('127.0.0.1',8765),Handler).serve_forever()
