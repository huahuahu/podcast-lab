#!/usr/bin/env python3
"""Order lecture feeds by numeric source title, preserving identity and audio."""
from pathlib import Path
import xml.etree.ElementTree as ET
import re, json, copy
ROOT=Path(__file__).resolve().parents[2]
IT='http://www.itunes.com/dtds/podcast-1.0.dtd'
ET.register_namespace('itunes',IT)
ET.register_namespace('atom','http://www.w3.org/2005/Atom')
FILES=['yejiaying-shuo-chu-sheng-tang-shi.xml','yejiaying-shuo-dufu.xml','yejiaying-shuo-ruanji.xml','yejiaying-shuo-shi-jianggao.xml','yejiaying-shuo-taoyuanming.xml','yejiaying-shuo-zhong-wan-tang-shi.xml']
def source_number(item):
 title=item.findtext('title')
 match=re.match(r'(\d+)',title)
 if match:return int(match[1])
 match=re.search(r'诗人之([一二三四五六七八九十])',title)
 if match:return '一二三四五六七八九十'.index(match[1])+1
 raise ValueError('Missing source number: '+title)
def set_text(parent,name,text):
 el=parent.find('{'+IT+'}'+name)
 if el is None:el=ET.SubElement(parent,'{'+IT+'}'+name)
 el.text=str(text)
def save(tree,path,items):
 ch=tree.find('channel')
 for old in ch.findall('item'):ch.remove(old)
 set_text(ch,'type','serial')
 for item in items:ch.append(item)
 ET.indent(tree,space='  ');tree.write(path,encoding='UTF-8',xml_declaration=True)
def main():
 all_items=[];report=[]
 for season,name in enumerate(FILES,1):
  path=ROOT/'docs/feeds'/name;tree=ET.parse(path)
  items=sorted(tree.findall('channel/item'),key=source_number)
  assert len({source_number(i) for i in items})==len(items)
  for number,item in enumerate(items,1):
   set_text(item,'episode',number);set_text(item,'season',1)
   combined=copy.deepcopy(item);set_text(combined,'season',season);all_items.append(combined)
  save(tree,path,items)
  report.append({'feed':name,'source_numbers':[source_number(i) for i in items],'guids':[i.findtext('guid') for i in items]})
 path=ROOT/'docs/feeds/all.xml';save(ET.parse(path),path,all_items)
 (ROOT/'archive/poem-media-migration/order-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
