#!/usr/bin/env python3
from pathlib import Path
import xml.etree.ElementTree as ET
import urllib.parse, hashlib, json, os
SRC=Path('/Users/tigerguo/git/Legacy/poemMedia')
OUT=Path(__file__).resolve().parents[2]
STAGE=Path('/Users/tigerguo/git/poem-media-upload')
NS={'itunes':'http://www.itunes.com/dtds/podcast-1.0.dtd','content':'http://purl.org/rss/1.0/modules/content/','atom':'http://www.w3.org/2005/Atom'}
for k,v in NS.items(): ET.register_namespace(k,v)
TAGS={
 'dufu':'poem-media-dufu-v1',
 'jianggao':'poem-media-jianggao-v1',
 'chu-sheng-tang':'poem-media-chu-sheng-tang-v1',
 'zhong-wan-tang':'poem-media-zhong-wan-tang-v1',
 'ruanji':'poem-media-ruanji-v1',
 'taoyuanming':'poem-media-taoyuanming-v1',
}
# Exact title-stem index; duplicates are a hard failure. This is the source's explicit RSS title -> source filename mapping.
idx={}
for f in (SRC/'data').rglob('*.mp3'):
 if f.stem in idx: raise SystemExit(f'duplicate source title stem: {f.stem!r}')
 idx[f.stem]=f
all_feed=ET.parse(SRC/'docs/feed/all.xml').getroot().find('channel')
rows=[]; ids=set(); titles=set()
for item in all_feed.findall('item'):
 title=item.findtext('title'); guid=item.findtext('guid'); en=item.find('enclosure')
 asset=urllib.parse.unquote(Path(urllib.parse.urlparse(en.attrib['url']).path).name)
 aid=Path(asset).stem; series=aid.rsplit('-',1)[0]
 if title not in idx: raise SystemExit(f'no exact title-stem source match: {aid}: {title!r}')
 f=idx[title]
 if aid in ids: raise SystemExit(f'duplicate asset id: {aid}')
 ids.add(aid); titles.add(title)
 if series not in TAGS: raise SystemExit(f'unknown series: {series}')
 if f.stat().st_size < 10000: raise SystemExit(f'not materialized or too small: {f} ({f.stat().st_size})')
 # Hard link gives upload basename without re-encoding or copying bytes.
 sd=STAGE/TAGS[series]; sd.mkdir(parents=True,exist_ok=True); dst=sd/asset
 if dst.exists():
  if not os.path.samefile(f,dst): raise SystemExit(f'Unexpected staging file: {dst}')
 elif dst.is_symlink(): raise SystemExit(f'Unexpected staging symlink: {dst}')
 else: os.link(f,dst)
 h=hashlib.sha256()
 with open(f,'rb') as fp:
  for b in iter(lambda:fp.read(8*1024*1024),b''): h.update(b)
 rows.append({'asset_id':aid,'asset_name':asset,'series':series,'release_tag':TAGS[series],
  'source_path':str(f.relative_to(SRC)),'source_title_exact_match':title,'bytes':f.stat().st_size,
  'sha256':h.hexdigest(),'guid':guid,'pubDate':item.findtext('pubDate')})
if len(rows)!=84 or len(ids)!=84: raise SystemExit(f'expected 84 unique assets, got {len(rows)}/{len(ids)}')
# Every physical MP3 must be explicitly mapped exactly once.
physical={f for f in (SRC/'data').rglob('*.mp3')}
mapped={SRC/r['source_path'] for r in rows}
if physical != mapped:
 raise SystemExit(f'physical/mapped mismatch missing={physical-mapped}, extra={mapped-physical}')
byid={r['asset_id']:r for r in rows}
validation=json.loads((OUT/'archive/poem-media-migration/audio-validation.json').read_text())
durations={a['asset']:a['duration_seconds'] for a in validation['assets']}
feed_stats=[]
for src_feed in sorted((SRC/'docs/feed').glob('*.xml')):
 tree=ET.parse(src_feed); root=tree.getroot(); ch=root.find('channel')
 # Point channel and episode links at the target Pages site.
 for link in ch.findall('link'): link.text='https://huahuahu.github.io/podcast-lab/'
 for item in ch.findall('item'):
  for link in item.findall('link'): link.text='https://huahuahu.github.io/podcast-lab/'
 # Legacy cover does not exist in source checkout; remove rather than fabricate or retain dead old-repo URL.
 for image in ch.findall('image'): ch.remove(image)
 # Add canonical self URL.
 self_url=f'https://huahuahu.github.io/podcast-lab/feeds/{src_feed.name}'
 atom=ET.Element('{%s}link'%NS['atom'],{'href':self_url,'rel':'self','type':'application/rss+xml'})
 title_el=ch.find('title'); ch.insert(list(ch).index(title_el)+1,atom)
 count=0
 for item in ch.findall('item'):
  en=item.find('enclosure'); old=en.attrib['url']; aid=Path(urllib.parse.urlparse(old).path).stem
  r=byid[aid]
  en.attrib['url']=f'https://github.com/huahuahu/podcast-lab/releases/download/{r["release_tag"]}/{r["asset_name"]}'
  en.attrib['length']=str(r['bytes']); count+=1
  seconds=round(durations[r['asset_name']]); hours,seconds=divmod(seconds,3600); minutes,seconds=divmod(seconds,60)
  duration=item.find('{%s}duration'%NS['itunes'])
  if duration is None: duration=ET.SubElement(item,'{%s}duration'%NS['itunes'])
  duration.text=f'{hours:02d}:{minutes:02d}:{seconds:02d}'
 out=OUT/'docs/feeds'/src_feed.name
 ET.indent(tree,space='  ')
 tree.write(out,encoding='UTF-8',xml_declaration=True,short_empty_elements=True)
 feed_stats.append({'file':src_feed.name,'items':count,'url':self_url})
manifest={'source_repo':'/Users/tigerguo/git/Legacy/poemMedia','target_repo':'huahuahu/podcast-lab',
 'asset_count':len(rows),'total_bytes':sum(r['bytes'] for r in rows),'release_tags':TAGS,
 'feeds':feed_stats,'assets':rows}
(OUT/'archive/poem-media-migration/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
from order_feeds import main as order_feeds
order_feeds()
print(json.dumps({'assets':len(rows),'bytes':manifest['total_bytes'],'feeds':feed_stats,'tags':TAGS},ensure_ascii=False,indent=2))
