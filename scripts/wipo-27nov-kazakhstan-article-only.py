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
BASE='e853fb02ba47a6296116296b46929a534e83557b'
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
def video_permalink(loc,id):
 if isinstance(loc,str):
  url=Q.urljoin('https://www.facebook.com',loc)
  p=Q.urlsplit(url)
  if p.scheme=='https' and p.netloc in ('www.facebook.com','facebook.com','m.facebook.com') and id in url and not re.search(r'[\s<>]',url):
   return url
 return 'https://www.facebook.com/reel/'+id
def begin_upload(edge,label):
 res=graph('POST',edge,params={'upload_phase':'start'})
 id=number(res.get('video_id'))
 upload=res.get('upload_url')
 p=Q.urlsplit(upload or '')
 check(p.scheme=='https' and p.netloc=='rupload.facebook.com' and p.path.endswith('/'+id) and not p.query and not p.fragment,'Unexpected upload URL')
 raw=REEL.read_bytes()
 ans=ask('POST',upload,label+' binary upload',raw,{
  'Authorization':'OAuth '+TOKEN,'offset':'0','file_size':str(len(raw)),'Content-Type':'application/octet-stream'})
 check(ans.get('success') is True,label+' upload was not accepted.')
 print(label+' upload accepted, video '+id,flush=True)
 return id
def verify_reel(id):
 stage={}
 for _ in range(12):
  try:
   stage=graph('GET',id,fields='id,status,permalink_url,length,description')
  except GraphError as err:
   if err.code in (100,33):time.sleep(5);continue
   raise
  status=stage.get('status',{})
  processing=status.get('processing_phase',{}).get('status')
  publish=status.get('publishing_phase',{}).get('status')
  video=status.get('video_status')
  if processing=='error' or publish=='error' or video=='error':
   raise Abort('Reel status reports processing or publishing error. No retry.')
  if str(stage.get('id'))==id and (publish=='complete' or (video=='ready' and publish not in ('not_started','in_progress'))) and 4<float(stage.get('length',0) or 0)<=60:
   check('Giọng đọc tổng hợp' in (stage.get('description') or '') and CURRENT_WEB in (stage.get('description') or ''),'Stored Reel description did not match. No retry.')
   return video_permalink(stage.get('permalink_url'),id)
  time.sleep(5)
 raise Abort('Reel finish was sent; no confirmed public status yet. Do not repost.')
def photos():
 out=[]
 for path in PHOTOS:
  b='wipo-verti-editorial-20261124'+str(len(out))
  head=(f'--{b}\r\nContent-Disposition: form-data; name="published"\r\n\r\nfalse\r\n'
   f'--{b}\r\nContent-Disposition: form-data; name="source"; filename="{path.name}"\r\nContent-Type: image/png\r\n\r\n').encode()
  res=graph('POST',PAGE+'/photos',body=head+path.read_bytes()+f'\r\n--{b}--\r\n'.encode(),ctype='multipart/form-data; boundary='+b)
  out.append(number(res.get('id')))
 print('PHOTOS UPLOADED '+','.join(out),flush=True)
 return out
def attached(ids):
 return json.dumps([{'media_fbid':i} for i in ids],separators=(',',':'))
def getpost(id):
 return graph('GET',id,fields='id,from,is_published,message,permalink_url,attachments{media_type,type,target,subattachments{media_type,type,target}}')
def attachments(a):
 kinds=[]
 def get(b):
  if isinstance(b,dict):
   if isinstance(b.get('media_type'),str):kinds.append(b['media_type'])
   elif isinstance(b.get('type'),str):kinds.append(b['type'])
   for k in ('data','attachments','subattachments'):get(b.get(k))
  if isinstance(b,list):
   for i in b:get(i)
 get(a)
 return kinds
def finish_post(proof,id,msg,label):
 url=proof.get('permalink_url')
 p=Q.urlsplit(url or '')
 check(proof.get('id')==id and proof.get('is_published') is True and proof.get('message')==msg and p.scheme=='https' and p.netloc in ('www.facebook.com','facebook.com','m.facebook.com'),'Publish attempted but readback did not match. No retry.')
 print('ARTICLE VERIFIED '+label+' '+id+' '+url,flush=True)
import datetime as dt
ROOT=Path('wipo-27nov-comment-live-fb')
def clean_source(url):
 p=Q.urlsplit(url)
 return (p.netloc.removeprefix('www.'),(p.path.removeprefix('/en').removeprefix('/fr').rstrip('/') + ('?' + p.query if 'serno=' in p.query else '')))
def pack_media(photos):
 return {f'attached_media[{i}]':json.dumps({'media_fbid':x},separators=(',',':')) for i,x in enumerate(photos)}
def make_message(a,reel):
 source=a['source']['url']
 parts=['(English below)','',a['title']['vi'],'',a['summary']['vi']]
 for lang in ('vi','en'):
  if lang=='en':parts+=['','ENGLISH','',a['title']['en'],'',a['summary']['en']]
  for section in a['body'][lang]:parts+=['',section['heading'],*section['paragraphs']]
 parts+=['','Bài trên website / Read on Verti: https://verti.ch/articles/'+a['slug']+'/','EN: https://verti.ch/en/articles/'+a['slug']+'/']
 if reel:parts+=['','Xem Reel / Watch the Reel: '+reel]
 if a['category']!='wipo-webcast':parts+=['','Nguồn / Source: '+source]
 for u in a.get('sources_extra',[]):parts+=['Nguồn đối chiếu / Cross-check: '+u]
 final={'wto-news':'(Trích nguồn wto.org)','wipo-news':'(Trích nguồn WIPO)','publications':'(Trích nguồn WIPO)','frontier-tech':'(Trích nguồn Nature)'}
 parts+=['','Ảnh bìa: minh họa AI, không phải ảnh tư liệu. Sơ đồ: Verti, dữ liệu WTO / Cover: AI-generated illustration, not a documentary image. Timeline: Verti, WTO data.']
 if a['category'] in final:parts+=['',final[a['category']]]
 return '\n'.join(parts)

def run():
 global TOKEN,CURRENT_WEB,PHOTOS
 check(os.environ.get('GITHUB_REPOSITORY')=='Troly2025/Verti' and os.environ.get('GITHUB_REF')=='refs/heads/main' and os.environ.get('GITHUB_EVENT_NAME')=='push' and os.environ.get('GITHUB_RUN_ATTEMPT')=='1','Wrong action context')
 push=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
 check(push.get('before')==BASE and push.get('after')==os.environ['GITHUB_SHA'] and not push.get('forced'),'Wrong action push')
 m=json.loads(Path('.github/releases/wipo-27nov-kazakhstan-article-only.json').read_text())
 for n,h in m['sha256'].items():check(hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,'Input mismatch')
 [a]=json.loads((ROOT/'batch.json').read_text())
 slug=a['slug'];check(slug=='kazakhstan-wto-giay-phep-dich-vu','Wrong story')
 rid='1171675278636135';sid='1592952125853927'
 CURRENT_WEB='https://verti.ch/articles/'+slug+'/'
 PHOTOS=[Path('src/images')/(slug+'.png'),Path('src/images')/(slug+'-diagram.png')]
 msg=make_message(a,'https://www.facebook.com/reel/'+rid+'/')
 check(len(msg)<10000 and CURRENT_WEB in msg and msg.endswith('(Trích nguồn wto.org)'),'Invalid article copy')
 if sys.argv[1:]==['--check']:return
 TOKEN=os.environ.get('FACEBOOK_PAGE_ACCESS_TOKEN','').strip()
 check(re.fullmatch(r'[A-Za-z0-9_.|-]{20,4096}',TOKEN),'Invalid token format')
 me=graph('GET','me',fields='id,name');check(me.get('id')==PAGE and me.get('name')==NAME,'Wrong Page, no writes.')
 link=verify_reel(rid)
 status={'slug':slug,'reel_id':rid,'reel':link,'story_upload_id':sid,'story':'upload_accepted_publish_unconfirmed','comment':'blocked_permission_not_verified_inline_link_retained'}
 try:
  ss=graph('GET',PAGE+'/stories')
  match=next((row for row in ss.get('data',[]) if str(row.get('media_id'))==sid),None)
  if match:
   status.update(story='published_meta' if match.get('status')=='published' else 'listed_meta',story_id=str(match.get('post_id') or ''),story_url=match.get('url',''))
 except Abort:pass
 print('WIPO_RECOVERY_PRECHECK '+json.dumps(status,separators=(',',':')),flush=True)
 postfields='id,message,permalink_url,attachments{type,media_type,target,url}'
 seen=ask('GET',GRAPH+PAGE+'/published_posts?'+Q.urlencode({'limit':70,'fields':postfields}),'dedup Page feed',headers={'Authorization':'Bearer '+TOKEN})
 check(isinstance(seen.get('data'),list),'Cannot preflight Page feed')
 source=a['source']['url']
 def is_confirmed_reel(x):
  if rid in str(x.get('permalink_url')):return True
  if any(str(v.get('target',{}).get('id'))==rid for v in x.get('attachments',{}).get('data',[])):return True
  msg=str(x.get('message',''))
  return a['graphic']['vi'] in msg and 'Giọng đọc tổng hợp.' in msg and source in msg and CURRENT_WEB in msg and a['title']['vi'] not in msg
 for x in seen['data']:
  t=str(x.get('message',''))
  if (source in t or CURRENT_WEB in t or a['title']['vi'] in t) and not is_confirmed_reel(x):
   raise Abort('Matching Page post already exists or is ambiguous. No writes.')
 msg=make_message(a,link)
 ids=photos()
 post=graph('POST',PAGE+'/feed',params={'message':msg,'published':'true','attached_media':attached(ids)})
 id=postid(post.get('id'));status.update(article_id=id,image_ids=ids)
 print('WIPO_RECOVERY_POST_ID '+id,flush=True)
 proof=getpost(id)
 check(sum(k in ('photo','image') for k in attachments(proof))>=2,'Two-image readback not confirmed. No retry.')
 finish_post(proof,id,msg,'ARTICLE ONLY')
 status['article']=proof['permalink_url']
 print('WIPO_PROOF '+json.dumps(status,separators=(',',':')),flush=True)
if __name__=='__main__':
 try:run()
 except Abort as e:print(str(e),file=sys.stderr);sys.exit(1)
 except Exception as e:print('Internal '+type(e).__name__+'; check immutable proof. Do not retry a write.',file=sys.stderr);sys.exit(1)
