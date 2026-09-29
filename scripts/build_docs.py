"""Build self-contained HTML/PDF manuals, slide PDF, API snapshot and Archi model."""
from pathlib import Path
import html
import json
import re
import sys
import os
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
if (ROOT/'.tools').exists():sys.path.insert(0,str(ROOT/'.tools'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'data/matplotlib'))
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image,PageBreak
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from app.reports.rendering import FONT_PATH

DOCS=ROOT/'docs'
pdfmetrics.registerFont(TTFont('CRM',FONT_PATH))
styles=getSampleStyleSheet()
for style in styles.byName.values():style.fontName='CRM'
styles['BodyText'].fontSize=9;styles['BodyText'].leading=14;styles['BodyText'].spaceAfter=8
styles['Heading1'].fontSize=21;styles['Heading1'].leading=28;styles['Heading1'].textColor=colors.HexColor('#6534b5')
styles['Heading2'].fontSize=14;styles['Heading2'].leading=20;styles['Heading2'].spaceBefore=15
styles.add(ParagraphStyle('CodeCRM',parent=styles['BodyText'],fontSize=8,leading=11,backColor=colors.HexColor('#f4f1f8')))

def clean(line):
    return html.escape(line).replace('`','').replace('**','')

def elements(text):
    result=[];code=False
    for line in text.splitlines():
        line=line.strip()
        if line.startswith('```'):code=not code;continue
        if not line:continue
        image=re.fullmatch(r'!\[(.*?)\]\((.*?)\)',line)
        if image:
            path=DOCS/image[2]
            if path.exists():
                obj=Image(str(path));ratio=min(480/obj.imageWidth,470/obj.imageHeight);obj.drawWidth=obj.imageWidth*ratio;obj.drawHeight=obj.imageHeight*ratio;result.extend([obj,Paragraph(clean(image[1]),styles['Caption'] if 'Caption' in styles else styles['BodyText']),Spacer(1,10)])
            continue
        style='CodeCRM' if code else 'Heading1' if line.startswith('# ') else 'Heading2' if line.startswith('## ') else 'BodyText'
        result.append(Paragraph(clean(re.sub(r'^#+\s*','',line)),styles[style]))
    return result

def footer(canvas,doc):
    canvas.setFont('CRM',8);canvas.setFillColor(colors.HexColor('#716c7e'));canvas.drawString(40,23,'ИТ Школа · CRM / Документация v2.0');canvas.drawRightString(A4[0]-40,23,str(doc.page))

def html_page(text,title):
    body=[];code=False
    for line in text.splitlines():
        if line.startswith('```'):body.append('</pre>' if code else '<pre>');code=not code;continue
        if not line.strip():continue
        image=re.fullmatch(r'!\[(.*?)\]\((.*?)\)',line)
        if image:body.append(f'<figure><img src="{html.escape(image[2])}" alt="{html.escape(image[1])}"><figcaption>{html.escape(image[1])}</figcaption></figure>');continue
        if code:body.append(html.escape(line)+'\n');continue
        tag='h1' if line.startswith('# ') else 'h2' if line.startswith('## ') else 'p'
        body.append(f'<{tag}>{clean(re.sub(r"^#+\s*","",line))}</{tag}>')
    return '<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>body{font:16px/1.65 Segoe UI,Arial,sans-serif;max-width:1100px;margin:40px auto;padding:0 24px;color:#252135}h1,h2,a{color:#6534b5}img{max-width:100%;border:1px solid #ddd;border-radius:12px}pre{white-space:pre-wrap;background:#f6f5f9;padding:18px}figure{margin:25px 0}figcaption{color:#716c7e;font-size:13px}</style><nav><a href="/">CRM</a> · <a href="index.html">Документация</a></nav>'+''.join(body)+'</html>'

def build_archi():
    xsi='http://www.w3.org/2001/XMLSchema-instance';archi='http://www.archimatetool.com/archimate'
    ET.register_namespace('xsi',xsi);ET.register_namespace('archimate',archi)
    model=ET.Element('{'+archi+'}model',{'name':'ИТ Школа CRM v2','id':'model-crm-v2','version':'5.0.0'})
    folders={kind:ET.SubElement(model,'folder',{'name':name,'id':'folder-'+kind,'type':kind}) for kind,name in [('business','Бизнес'),('application','Приложения'),('technology','Технологии'),('relations','Связи'),('diagrams','Представления')]}
    entries=[('kam','КАМ','BusinessRole','business'),('manager','Руководитель','BusinessRole','business'),('admin','Администратор','BusinessRole','business'),('process','Сотрудничество с ВУЗом','BusinessProcess','business'),('spa','React SPA','ApplicationComponent','application'),('api','FastAPI CRM','ApplicationComponent','application'),('kc','Keycloak OIDC','ApplicationComponent','application'),('reports','Формирование отчётов','ApplicationFunction','application'),('adapters','LMS / Website adapters','ApplicationComponent','application'),('data','University / Interaction / Workflow','DataObject','application'),('audit','AuditLog','DataObject','application'),('pg','PostgreSQL','SystemSoftware','technology'),('redis','Redis','SystemSoftware','technology'),('storage','Files volume','Artifact','technology'),('docker','Linux Docker host','Node','technology')]
    for id,name,type,folder in entries:ET.SubElement(folders[folder],'element',{'{'+xsi+'}type':'archimate:'+type,'id':id,'name':name})
    relations=[('spa','kam','ServingRelationship'),('spa','manager','ServingRelationship'),('spa','admin','ServingRelationship'),('api','spa','ServingRelationship'),('spa','kc','FlowRelationship'),('api','data','AccessRelationship'),('api','audit','AccessRelationship'),('api','adapters','FlowRelationship'),('api','reports','CompositionRelationship'),('pg','api','ServingRelationship'),('redis','api','ServingRelationship'),('api','storage','AccessRelationship'),('docker','pg','CompositionRelationship')]
    for i,(source,target,type) in enumerate(relations):ET.SubElement(folders['relations'],'element',{'{'+xsi+'}type':'archimate:'+type,'id':f'relation-{i}','source':source,'target':target})
    view=ET.SubElement(folders['diagrams'],'element',{'{'+xsi+'}type':'archimate:ArchimateDiagramModel','id':'view-components','name':'Функциональная и компонентная архитектура'})
    nodes={}
    for i,(id,name,type,folder) in enumerate(entries):
        node=ET.SubElement(view,'child',{'{'+xsi+'}type':'archimate:DiagramObject','id':'view-'+id,'archimateElement':id})
        ET.SubElement(node,'bounds',{'x':str(30+(i%3)*260),'y':str(30+(i//3)*125),'width':'230','height':'90'})
        nodes[id]=node
    for i,(source,target,kind) in enumerate(relations):
        cid=f'connection-{i}'
        ET.SubElement(nodes[source],'sourceConnection',{'{'+xsi+'}type':'archimate:Connection','id':cid,'source':'view-'+source,'target':'view-'+target,'archimateRelationship':f'relation-{i}'})
        nodes[target].set('targetConnections',(nodes[target].get('targetConnections','')+' '+cid).strip())
    ET.indent(model);ET.ElementTree(model).write(DOCS/'architecture.archimate',encoding='utf-8',xml_declaration=True)

def main():
    names=['USER_GUIDE','ADMIN_GUIDE','ARCHITECTURE','API','SECURITY','DEPLOYMENT','ACCEPTANCE']
    combined=[];links=[]
    for name in names:
        path=DOCS/(name+'.md')
        if not path.exists():continue
        text=path.read_text(encoding='utf-8');title=text.splitlines()[0].lstrip('# ')
        SimpleDocTemplate(str(DOCS/(name+'.pdf')),pagesize=A4,leftMargin=40,rightMargin=40,topMargin=40,bottomMargin=40,title=title,author='ИТ Школа CRM').build(elements(text),onFirstPage=footer,onLaterPages=footer)
        (DOCS/(name+'.html')).write_text(html_page(text,title),encoding='utf-8')
        if combined:combined.append(PageBreak())
        combined.extend(elements(text));links.append(f'<li><a href="{name}.html">{html.escape(title)}</a> · <a href="{name}.pdf">PDF</a></li>')
    SimpleDocTemplate(str(DOCS/'documentation.pdf'),pagesize=A4,leftMargin=40,rightMargin=40,topMargin=40,bottomMargin=40,title='Сопроводительная документация CRM').build(combined,onFirstPage=footer,onLaterPages=footer)
    (DOCS/'index.html').write_text('<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CRM · Документация</title><style>body{font:18px/2 Segoe UI,Arial;max-width:1000px;margin:60px auto;padding:20px;color:#252135}a{color:#6534b5}</style><a href="/help">Вернуться в CRM</a><h1>ИТ Школа · Документация</h1><ul>'+''.join(links)+'<li><a href="documentation.pdf">Полная документация PDF</a></li><li><a href="PRESENTATION.pdf">Презентация PDF</a></li><li><a href="architecture.archimate">Archi-модель</a></li><li><a href="openapi.json">OpenAPI JSON</a></li></ul></html>',encoding='utf-8')
    slides=re.split(r'^## ',(DOCS/'PRESENTATION.md').read_text(encoding='utf-8'),flags=re.M)[1:]
    canvas=Canvas(str(DOCS/'PRESENTATION.pdf'),pagesize=landscape(A4));width,height=landscape(A4)
    for i,slide in enumerate(slides,1):
        lines=slide.strip().splitlines();canvas.setFillColor(colors.HexColor('#24163a'));canvas.rect(0,0,width,height,fill=1,stroke=0);canvas.setFillColor(colors.HexColor('#ff8650'));canvas.setFont('CRM',13);canvas.drawString(45,height-45,'ИТ ШКОЛА / РОСТЕЛЕКОМ');canvas.setFillColor(colors.white)
        title=Paragraph(html.escape(lines[0]),ParagraphStyle('SlideTitle',fontName='CRM',fontSize=28,leading=36,textColor=colors.white));_,h=title.wrap(width-90,150);title.drawOn(canvas,45,height-95-h)
        y=height-140-h
        for line in lines[1:]:
            if not line.strip():continue
            p=Paragraph(html.escape(line.lstrip('- ')),ParagraphStyle('SlideBody',fontName='CRM',fontSize=18,leading=28,textColor=colors.HexColor('#e7e0f1')));_,h=p.wrap(width-110,300);p.drawOn(canvas,55,y-h);y-=h+25
        canvas.setFont('CRM',11);canvas.drawRightString(width-40,25,f'{i} / {len(slides)}');canvas.showPage()
    canvas.save();build_archi()
    from app.main import app
    (DOCS/'openapi.json').write_text(json.dumps(app.openapi(),ensure_ascii=False,indent=2),encoding='utf-8')
    package=json.loads((ROOT/'frontend/package.json').read_text(encoding='utf-8'))
    components='# Компоненты и библиотеки\n\nПрямые зависимости frontend зафиксированы в package-lock.json; backend — в requirements. Транзитивные пакеты входят в дерево соответствующего менеджера.\n\n## Frontend\n\n'
    components+='\n'.join(f'- {name}: {version}' for name,version in {**package['dependencies'],**package['devDependencies']}.items())
    components+='\n\n## Backend\n\n'+(ROOT/'backend/requirements.txt').read_text()+'\n\n## Backend tests\n\n'+(ROOT/'backend/requirements-dev.txt').read_text()+'\n\n## Infrastructure\n\nPostgreSQL 17, Redis 7, Keycloak 26.2.5, Nginx 1.28, Python 3.12, Node 24. Для production следует фиксировать digest образов после проверки обновлений.\n'
    (DOCS/'COMPONENTS.md').write_text(components,encoding='utf-8')
    print(f'Built {len(links)} manuals, combined PDF, {len(slides)} slides, Archi and OpenAPI')

if __name__=='__main__':main()
