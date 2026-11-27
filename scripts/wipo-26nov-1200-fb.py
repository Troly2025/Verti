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
BASE='f1f910e683db3732dd960d921ab2381a313bf13b'
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
ROOT=Path('wipo-26nov-1200-fb')
def clean_source(url):
 p=Q.urlsplit(url)
 return (p.netloc.removeprefix('www.'),(p.path.removeprefix('/en').removeprefix('/fr').rstrip('/') + ('?' + p.query if 'serno=' in p.query else '')))
def pack_media(photos):
 return {f'attached_media[{i}]':json.dumps({'media_fbid':x},separators=(',',':')) for i,x in enumerate(photos)}
def make_message(a,reel):
 source=a['source']['url']
 leads={'wipo-furukawa-so-huu-tri-tue-tang-truong': 'Một bản đồ sáng chế hữu ích phải giúp đổi một quyết định kinh doanh. Văn phòng WIPO tại Nhật Bản sắp mời người từng làm công tác sở hữu trí tuệ và hiện lãnh đạo Furukawa Electric nói về bước chuyển này.', 'pin-mat-troi-perovskite-hai-lop-308': 'Báo cáo mức 30,8% cho pin mặt trời cần đọc cùng một con số ít xuất hiện trên tiêu đề: diện tích đo chỉ 0,107 cm².', 'arizona-dai-loan-trung-tam-nhan-luc-ban-dan': 'Quận bố trí địa điểm, trường xây khóa học, doanh nghiệp kết nối với ứng viên. Đó là cách Tucson đưa đào tạo bán dẫn đến gần nơi có nhu cầu tuyển dụng.'}
 parts=['(English below)','',a['title']['vi'],'',leads[a['slug']],'',a['summary']['vi']]
 for lang in ('vi','en'):
  if lang=='en':parts+=['','ENGLISH','',a['title']['en'],'',a['summary']['en']]
  for section in a['body'][lang]:parts+=['',section['heading'],*section['paragraphs']]
 parts+=['','Bài trên website / Read on Verti: https://verti.ch/articles/'+a['slug']+'/','EN: https://verti.ch/en/articles/'+a['slug']+'/']
 if reel:parts+=['','Xem Reel / Watch the Reel: '+reel]
 if a['category']!='wipo-webcast':parts+=['','Nguồn / Source: '+source]
 for u in a.get('sources_extra',[]):parts+=['Nguồn đối chiếu / Cross-check: '+u]
 final={'wto-news':'(Trích nguồn wto.org)','wipo-news':'(Trích nguồn WIPO)','publications':'(Trích nguồn WIPO)','frontier-tech':'(Trích nguồn Nature)'}
 parts+=['','Cả hai ảnh là minh họa do AI tạo, không phải ảnh tư liệu / Both images are AI-generated illustrations, not documentary photographs.']
 if a['category'] in final:parts+=['',final[a['category']]]
 return '\n'.join(parts)
def run_batch():
 global TOKEN,REEL,PHOTOS,TITLE,INTRO,SOURCE,CURRENT_WEB
 check(os.environ.get('GITHUB_REPOSITORY')=='Troly2025/Verti' and os.environ.get('GITHUB_REF')=='refs/heads/main' and os.environ.get('GITHUB_EVENT_NAME')=='push' and os.environ.get('GITHUB_RUN_ATTEMPT')=='1','Wrong action context.')
 push=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
 check(push.get('before')==BASE and push.get('after')==os.environ['GITHUB_SHA'] and not push.get('forced'),'Wrong action push.')
 m=json.loads(Path('.github/releases/wipo-26nov-1200-fb.json').read_text())
 for name,sha in m['sha256'].items():check(hashlib.sha256(Path(name).read_bytes()).hexdigest()==sha,'Media/content digest mismatch '+name)
 rows=json.loads((ROOT/'batch.json').read_text())
 check(0<len(rows)<=8 and len({a['slug'] for a in rows})==len(rows),'Expected unique reviewed stories.')
 if sys.argv[1:]==['--check']:return
 TOKEN=os.environ.get('FACEBOOK_PAGE_ACCESS_TOKEN','')
 check(re.fullmatch(r'[A-Za-z0-9_.|-]{20,4096}',TOKEN),'Missing Page token.')
 me=graph('GET','me',fields='id,name')
 check(me.get('id')==PAGE and me.get('name')==NAME,'Wrong Page, no writes.')
 feed=ask('GET',GRAPH+PAGE+'/published_posts?'+Q.urlencode({'limit':70,'fields':'id,message,permalink_url'}),'dedup Page feed',headers={'Authorization':'Bearer '+TOKEN})
 check(isinstance(feed.get('data'),list),'Cannot preflight Facebook recent publications.')
 seen=feed['data']
 for a in rows:
  slug=a['slug']; CURRENT_WEB='https://verti.ch/articles/'+slug+'/'; SOURCE=a['source']['url']; TITLE=a['graphic']['vi']; INTRO=a['title']['vi']
  f=ROOT/slug
  REEL=f/(slug+'.mp4'); PHOTOS=[f/(slug+'.png'),f/(slug+'-diagram.png')]
  status={'slug':slug}
  try:
   def public_read(url):
    for attempt in range(4):
     try:
      with U.urlopen(U.Request(url,headers={'User-Agent':'Verti WIPO verification'}),timeout=12) as resp:
       if resp.status==200:return resp.read()
     except (OSError,ValueError):
      time.sleep(3)
    raise Abort('Web prerequisite timed out. No writes.')
   for prefix in ('','/en'):
    url='https://verti.ch'+prefix+'/articles/'+slug+'/'
    raw=public_read(url).decode()
    check(url in raw and all('/images/'+p.name in raw for p in PHOTOS),'Web prerequisite missing. No writes.')
   for pic in PHOTOS:
    content=public_read('https://verti.ch/images/'+pic.name)
    check(hashlib.sha256(content).digest()==hashlib.sha256(pic.read_bytes()).digest(),'Live image digest mismatch. No writes.')
   token=clean_source(SOURCE)[1]
   if any(token in str(p.get('message','')) or INTRO in str(p.get('message','')) or CURRENT_WEB in str(p.get('message','')) for p in seen):
    raise Abort('Page already has this topic or source. No writes.')
   rid=begin_upload('me/video_reels','Reel')
   status['reel_id']=rid
   caption=f"(English below)\n\n{TITLE}\n{a['summary']['vi']}\nĐọc toàn văn: {CURRENT_WEB}\nNguồn / Source: {a['source']['name']} ({a['source_date']})\n{SOURCE}\nGiọng đọc tổng hợp.\nCảnh minh họa do AI tạo / AI-generated illustration.\n\n{a['graphic']['en']}\nRead the full article: https://verti.ch/en/articles/{slug}/"
   res=graph('POST','me/video_reels',params={'upload_phase':'finish','video_state':'PUBLISHED','video_id':rid,'title':TITLE,'description':caption})
   check(res.get('success') is True,'Meta did not confirm Reel finish.')
   link=verify_reel(rid)
   status.update(reel_id=rid,reel=link)
   try:
    e=PAGE+'/video_stories'
    sid=begin_upload(e,'Story')
    a_story=graph('POST',e,params={'upload_phase':'finish','video_id':sid})
    if a_story.get('success') is True or a_story.get('post_id'):
     status.update(story_upload_id=sid,story_id=number(a_story.get('post_id')) if a_story.get('post_id') else '',story='accepted_unverified')
     try:
      for _ in range(4):
       found=False
       s=graph('GET',PAGE+'/stories')
       for row in s.get('data',[]):
        if status.get('story_id') and status['story_id']==str(row.get('post_id')) or sid==str(row.get('media_id')):
         url=row.get('url',''); p=Q.urlsplit(url)
         status['story']='published_meta' if str(row.get('status','')).lower()=='published' else 'listed_meta'
         status['meta_story_status']=row.get('status')
         if p.scheme=='https' and p.netloc in ('facebook.com','www.facebook.com','m.facebook.com'): status['story_url']=url
         found=True
         break
       if found:break
       time.sleep(3)
     except Abort:pass
   except Abort as err:
    status['story_error']=str(err)
    if 'uncertain' in str(err) or (isinstance(err,GraphError) and err.code in (4,17,32,613,190)):raise
   ids=photos()
   msg=make_message(a,link)
   post=graph('POST',PAGE+'/feed',params={'message':msg,'published':'true','attached_media':attached(ids)})
   id=postid(post.get('id'))
   status['article_id']=id
   proof=getpost(id)
   kinds=attachments(proof)
   check(sum(k in ('photo','image') for k in kinds)>=2,'Article sent, two-image readback not confirmed. No retry.')
   finish_post(proof,id,msg,'PHOTO AND REEL')
   status['article']=proof['permalink_url'];status['image_ids']=ids;seen.append(proof)
  except Abort as err:
   status['error']=str(err)
   print('WIPO_PROOF '+json.dumps(status,ensure_ascii=True,separators=(',',':')),flush=True)
   if 'uncertain' in str(err) or 'No retry' in str(err) or (isinstance(err,GraphError) and err.code in (4,17,32,613,190)):break
   continue
  print('WIPO_PROOF '+json.dumps(status,ensure_ascii=True,separators=(',',':')),flush=True)
if __name__=='__main__':
 try:run_batch()
 except Abort as e:print(str(e),file=sys.stderr);sys.exit(1)
 except Exception:print('Unexpected batch error. Check previously emitted proofs; do not repeat a write.',file=sys.stderr);sys.exit(1)
