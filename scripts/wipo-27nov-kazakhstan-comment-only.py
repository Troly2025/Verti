import hashlib,json,os,re,sys,time,urllib.request as U,urllib.parse as Q,urllib.error as E
from pathlib import Path
VERSION='v24.0'
PAGE='927870153743820'
NAME='Tin tức công nghệ - sở hữu trí tuệ - thương mại thế giới'
SOURCE='https://www.wipo.int/en/web/scp/w/news/2026/patent-law-at-your-fingertips-wipo-launches-a-new-comparative-database'
TITLE='Đã công bố sáng chế, còn tính mới không?'
INTRO='WIPO mở cơ sở dữ liệu đối chiếu luật sáng chế giữa các nước'
REEL=Path('media-trial/wipo-patent-law-reel.mp4')
PHOTOS=[Path('media-trial')/f'wipo-luat-sang-che-{i}.png' for i in (1,2)]
BASE='96be7ec76e5a88ce0ee6ff54dd5baee4d7eae4fb'
GRAPH='https://graph.facebook.com/'+VERSION+'/'
TOKEN=''
class Abort(Exception): pass
class GraphError(Abort):
 def __init__(self,label,status,code,sub):
  self.code=code
  self.status=status
  super().__init__(f'{label}: HTTP {status}, code {code}, subcode {sub}')
class NoRedirect(U.HTTPRedirectHandler):
 def redirect_request(self,*a,**k): return None
opener=U.build_opener(NoRedirect())
def check(b,s):
 if not b: raise Abort(s)
def number(x):
 x=str(x)
 check(re.fullmatch(r'[0-9]{5,24}',x),'Unexpected ID format')
 return x
def postid(x):
 x=str(x)
 check(re.fullmatch(r'[0-9]{5,24}_[0-9]{5,24}',x),'Unexpected Page post ID format')
 return x
def ask(method,url,label,data=None,headers=None):
 try:
  with opener.open(U.Request(url,method=method,data=data,headers=headers or {}),timeout=25) as r:
   got=json.loads(r.read(2000000))
 except E.HTTPError as e:
  try:o=json.loads(e.read(100000)).get('error',{})
  except Exception:o={}
  o=o if isinstance(o,dict) else {}
  safe=lambda x:x if isinstance(x,int) else 0
  raise GraphError(label,e.code,safe(o.get('code')),safe(o.get('error_subcode'))) from None
 except (E.URLError,OSError,ValueError):
  raise Abort(f'{label}: response uncertain. Do not repeat a write; inspect the Page first.') from None
 check(isinstance(got,dict) and 'error' not in got,f'{label}: unexpected response')
 return got
def graph(method,edge,fields=None,params=None,body=None,ctype='application/x-www-form-urlencoded'):
 hdr={'Authorization':'Bearer '+TOKEN,'Accept':'application/json'}
 if method=='GET':
  url=GRAPH+edge+('?' + Q.urlencode({'fields':fields}) if fields else '')
  return ask(method,url,'GET '+edge,headers=hdr)
 if body is None:body=Q.urlencode(params or {}).encode()
 hdr['Content-Type']=ctype
 return ask(method,GRAPH+edge,'POST '+edge,body,hdr)

POST='927870153743820_122155741473188514'
REEL='https://www.facebook.com/reel/1171675278636135/'
WEB='https://verti.ch/articles/kazakhstan-wto-giay-phep-dich-vu/'
SHORT='Xem video tóm tắt / Watch the video summary: '+REEL
POST_URL='https://www.facebook.com/122155354473188514/posts/122155741473188514'
def run():
 global TOKEN
 check(os.environ.get('GITHUB_REPOSITORY')=='Troly2025/Verti' and os.environ.get('GITHUB_REF')=='refs/heads/main' and os.environ.get('GITHUB_EVENT_NAME')=='push' and os.environ.get('GITHUB_RUN_ATTEMPT')=='1','Wrong action context.')
 p=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
 check(p.get('before')==BASE and p.get('after')==os.environ.get('GITHUB_SHA') and not p.get('forced'),'Wrong action push.')
 config=json.loads(Path('.github/releases/wipo-27nov-kazakhstan-comment-only.json').read_text())
 check(config['base']==BASE and hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==config['script_sha256'],'Pinned script changed.')
 if sys.argv[1:]==['--check']:return
 TOKEN=os.environ.get('FACEBOOK_PAGE_ACCESS_TOKEN','').strip()
 check(re.fullmatch(r'[A-Za-z0-9_.|-]{20,4096}',TOKEN),'Page token missing or malformed.')
 me=graph('GET','me',fields='id,name')
 check(me.get('id')==PAGE and me.get('name')==NAME,'Wrong Facebook Page. No writes.')
 x=graph('GET',POST,fields='id,message,permalink_url,is_published,from')
 check(x.get('id')==POST and x.get('is_published') is True and x.get('from',{}).get('id')==PAGE and x.get('permalink_url','').rstrip('/')==POST_URL and all(z in x.get('message','') for z in (WEB,REEL)),'Expected Facebook article or paired Reel not confirmed. No writes.')
 pre=graph('GET',POST+'/comments',fields='id,message,from')
 check(isinstance(pre.get('data'),list) and not pre.get('paging',{}).get('next'),'Cannot rule out an existing Reel comment. No writes.')
 matches=[i for i in pre['data'] if REEL.rstrip('/') in (i.get('message') or '')]
 if matches:
  check(len(matches)==1 and str(matches[0].get('from',{}).get('id'))==PAGE,'A related comment already exists. No writes.')
  cid=str(matches[0].get('id','')); state='verified_existing'
 else:
  print('COMMENT_PRECHECK Page and post verified; no matching comment.',flush=True)
  cid=str(graph('POST',POST+'/comments',params={'message':SHORT}).get('id',''));state='published'
 check(re.fullmatch(r'[0-9]{5,24}(?:_[0-9]{5,24}){0,2}',cid),'Comment ID not confirmed. Do not repeat.')
 print('COMMENT_ID '+cid,flush=True)
 q=graph('GET',cid,fields='id,message,from')
 check(str(q.get('id'))==cid and q.get('from',{}).get('id')==PAGE and REEL in (q.get('message') or ''),'Meta did not verify the comment. Do not repeat.')
 print('COMMENT_PROOF '+json.dumps({'post':POST_URL,'reel':REEL,'comment_id':cid,'url':POST_URL+'?comment_id='+cid.rsplit('_',1)[-1],'status':state},separators=(',',':')),flush=True)
if __name__=='__main__':
 try:run()
 except Abort as e:print(str(e),file=sys.stderr);sys.exit(1)
 except Exception as e:print('Internal '+type(e).__name__+'. No replay without checking writes.',file=sys.stderr);sys.exit(1)
