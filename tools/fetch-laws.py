# 법령·기준 원문을 국가법령정보센터 공동활용 API로 받아 law-data.js로 만든다.
#   python3 tools/fetch-laws.py   (OC는 본인 법제처 API 아이디로 바꿔도 됨, 기본 test)
import json,urllib.request,urllib.parse,time,sys,re
def get(path,**q):
    q.setdefault('OC','test');q.setdefault('type','JSON')
    u='https://www.law.go.kr/DRF/'+path+'?'+urllib.parse.urlencode(q)
    for i in range(6):
        try:
            r=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'})
            return json.loads(urllib.request.urlopen(r,timeout=40).read().decode('utf-8'))
        except Exception as e:
            time.sleep(2*(i+1))
    raise RuntimeError('fail '+u)
def find(tgt,name):
    d=get('lawSearch.do',target=tgt,query=name,display=20)
    r=list(d.values())[0].get(tgt) or []
    if isinstance(r,dict):r=[r]
    key='법령명한글' if tgt=='law' else '행정규칙명'
    ex=[i for i in r if i[key].replace(' ','')==name.replace(' ','')]
    cur=[i for i in ex if i.get('현행연혁구분','현행') in ('현행',None,'')] or ex
    if not cur: raise RuntimeError('not found '+name+' : '+', '.join(i[key] for i in r))
    return cur[0]
def txt(x):
    if x is None:return ''
    if isinstance(x,str):return x
    if isinstance(x,list):return '\n'.join(txt(i) for i in x)
    if isinstance(x,dict):
        out=[]
        for k in ('조문내용','항내용','호내용','목내용'):
            if k in x and x[k]:out.append(txt(x[k]))
        for k in ('항','호','목'):
            if k in x:out.append(txt(x[k]))
        return '\n'.join(o for o in out if o)
    return str(x)
def law_items(mst,short):
    d=get('lawService.do',target='law',MST=mst)['법령']
    info=d['기본정보'];out=[]
    js=d['조문']['조문단위'];js=[js] if isinstance(js,dict) else js
    for a in js:
        if a.get('조문여부')=='전문':continue
        b=txt(a).strip()
        m=re.match(r'(제\d+조(?:의\d+)?)\s*\(([^)]*)\)',b)
        if not m:continue
        out.append({'n':m.group(1),'t':m.group(2),'b':b})
    bp=d.get('별표') or {}
    bs=bp.get('별표단위') or []
    bs=[bs] if isinstance(bs,dict) else bs
    for x in bs:
        t=(x.get('별표제목') or '').strip();c=txt(x.get('별표내용')).strip()
        no=x.get('별표번호','').lstrip('0') or '?';ga=x.get('별표가지번호','').lstrip('0')
        nm='별표 '+no+('의'+ga if ga else '')
        if c:out.append({'n':nm,'t':t,'b':c})
    return info,out
def adm_items(sid):
    d=get('lawService.do',target='admrul',ID=sid)['AdmRulService']
    info=d['행정규칙기본정보'];c=d.get('조문내용')
    out=[]
    if isinstance(c,list):
        for s in c:
            s=txt(s).strip();m=re.match(r'(제\d+조(?:의\d+)?)\s*\(([^)]*)\)',s)
            if m:out.append({'n':m.group(1),'t':m.group(2),'b':s})
            elif s and out:out[-1]['b']+='\n'+s
    else:
        s=txt(c)
        # NFTC형: "2.1.1 ..." 절 번호로 나눔
        parts=re.split(r'(?<![\d.])(?=(\d{1,2}\.\d{1,2}(?:\.\d{1,2}){0,3})\s?[가-힣「(])',s)
        buf=None
        i=0;segs=[]
        for p in parts:
            if p is None:continue
            segs.append(p)
        joined=s
        idx=[m.start() for m in re.finditer(r'(?<![\d.])(\d{1,2}\.\d{1,2})(?=\s?[가-힣「(])',s)]
        idx=[0]+[k for k in idx if k>0]+[len(s)]
        for a,b in zip(idx,idx[1:]):
            seg=s[a:b].strip()
            if not seg:continue
            m=re.match(r'(\d{1,2}\.\d{1,2})\s?([^\d][^.]{0,40}?)(?=\d{1,2}\.\d{1,2}\.\d|$)',seg)
            n=m.group(1) if m else seg[:6];t=(m.group(2).strip() if m else '')
            seg=re.sub(r'(?<![\d.])(\d{1,2}\.\d{1,2}\.\d{1,2}(?:\.\d{1,2})*)',r'\n\1',seg)
            out.append({'n':n,'t':t,'b':seg.strip()})
    return info,out
SRC=[('law','건축물의 설비기준 등에 관한 규칙','피뢰설비·비상용승강기·배연 등','pv'),
     ('law','학교보건법 시행규칙','교사 안 조도 등 환경위생 기준(별표)','sch'),
     ('law','재생에너지 개발ㆍ이용ㆍ보급 촉진법 시행령','공공기관 재생에너지 설치 의무','re'),
     ('law','전기안전관리법 시행규칙','사용전검사·정기검사·안전관리','es'),
     ('admrul','건축물의 에너지절약설계기준','전기설비부문 의무사항·에너지성능지표','en'),
     ('admrul','재생에너지 설비의 지원 등에 관한 규정','태양광 설비 시공 기준','re2'),
     ('admrul','전기설비 검사 및 점검의 방법·절차 등에 관한 고시','사용전검사 항목','chk'),
     ('admrul','유도등 및 유도표지의 화재안전기술기준(NFTC 303)','유도등','f303'),
     ('admrul','비상조명등의 화재안전기술기준(NFTC 304)','비상조명등','f304'),
     ('admrul','비상콘센트설비의 화재안전기술기준(NFTC 504)','비상콘센트','f504'),
     ('admrul','자동화재탐지설비 및 시각경보장치의 화재안전기술기준(NFTC 203)','자동화재탐지·시각경보','f203'),
     ('admrul','비상방송설비의 화재안전기술기준(NFTC 202)','비상방송','f202'),
     ('law','전기공사업법','분리발주·시공관리책임자·하도급·시공책임형','ew'),
     ('law','전기공사업법 시행령','시공관리책임자 지정·공사 범위','ewd'),
     ('law','전기공사업법 시행규칙','시공관리책임자 지정 통지 등 서식','ewr'),
     ('law','전력기술관리법','설계·감리 의무, 감리원 배치','pt'),
     ('law','전력기술관리법 시행령','설계감리·공사감리 대상, 감리원 배치기준','ptd'),
     ('law','전기안전관리법','사용전검사·정기검사·안전관리자','esl'),
     ('admrul','전력시설물 공사감리업무 수행지침','착공~준공 감리(공사감독) 업무 절차','sup')]
docs=[]
for tgt,name,desc,key in SRC:
    try:
        it=find(tgt,name)
        if tgt=='law':info,items=law_items(it['법령일련번호'],key);meta={'type':info.get('법종구분',{}).get('content') if isinstance(info.get('법종구분'),dict) else '', 'ef':info.get('시행일자'),'pr':info.get('공포일자')}
        else:info,items=adm_items(it['행정규칙일련번호']);meta={'type':info.get('행정규칙종류'),'ef':info.get('시행일자'),'pr':info.get('발령일자')}
        docs.append({'k':key,'name':name,'desc':desc,'meta':meta,'c':items})
        print('OK',name,len(items),meta,flush=True)
    except Exception as e:
        print('FAIL',name,e,flush=True)
import html,gzip,base64,os
if len(docs)<len(SRC):
    print('일부 실패 — law-data.js를 덮지 않습니다',len(docs),'/',len(SRC));sys.exit(1)
D={'got':time.strftime('%Y-%m-%d'),'src':'국가법령정보센터 공동활용 API(law.go.kr)','d':docs}
for d in D['d']:
    out=[];seen=set()
    for c in d['c']:
        t=html.unescape(c['t'] or '').strip();b=html.unescape(c['b'] or '').strip()
        if t.startswith('삭제') or len(b)<20 or c['n'] in seen:continue
        seen.add(c['n'])
        b=re.sub(r'(?<=[.다\)])\s*(?=(\d{1,2})\.\s?[가-힣「])',"\n",b)
        out.append({'n':c['n'],'t':t,'b':b})
    d['c']=out
raw=json.dumps(D,ensure_ascii=False,separators=(',',':')).encode()
b64=base64.b64encode(gzip.compress(raw,9)).decode()
dst=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','law-data.js')
open(dst,'w').write('/* 전기설계 관련 법령·기준 원문 — 국가법령정보센터 공동활용 API에서 '+D['got']+' 받음. 갱신: tools/fetch-laws.py */\nwindow.LAW_B64="'+b64+'";\n')
print('law-data.js',len(b64))
