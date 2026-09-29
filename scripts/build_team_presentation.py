"""Fill the supplied LCT template, preserving original slide 9 and its dependencies."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from io import BytesIO
import hashlib
import json
import posixpath
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools'))
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from lxml import etree as E
from PIL import Image

SOURCE = Path.home() / 'Desktop' / 'ЛЦТ2026 Шаблон презентации.pptx'
PHOTO = Path.home() / 'Downloads' / 'Telegram Desktop' / 'photo_2026-09-15_17-11-58.jpg'
OUT = ROOT / 'docs' / 'Пользователи 200 — ЛЦТ2026.pptx'
WORK = ROOT / 'docs' / 'presentation-work'
WORK.mkdir(exist_ok=True)
prs = Presentation(SOURCE)
P = '520978'
DARK = '310F53'
INK = '1C1D22'
PINK = 'FF0053'
WHITE = 'FFFFFF'

def slide(n): return prs.slides[n-1]

def shape(n, sid):
    return next(s for s in slide(n).shapes if s.shape_id == sid)

def fill(s, value, size=19, color=INK, bold=False):
    tf = s.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(.02)
    tf.margin_top = tf.margin_bottom = Inches(.02)
    tf.vertical_anchor = MSO_ANCHOR.TOP
    for j, line in enumerate(value.split('\n')):
        p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
        p.text = line
        p.level = 0
        p.space_before = Pt(0)
        p.space_after = Pt(9)
        p.line_spacing = 1.08
        p.alignment = PP_ALIGN.LEFT
        p.font.name = 'Montserrat'
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = RGBColor.from_string(color)
        # Template placeholders may inherit bullets from master styles.
        pp = p._p.get_or_add_pPr()
        pp.set('marL','0')
        pp.set('indent','0')
        for c in list(pp):
            if E.QName(c).localname.startswith('bu'): pp.remove(c)
        bullet=E.Element('{http://schemas.openxmlformats.org/drawingml/2006/main}buNone')
        before=next((c for c in pp if E.QName(c).localname in ('tabLst','defRPr','extLst')),None)
        if before is None: pp.append(bullet)
        else: pp.insert(list(pp).index(before),bullet)
    return s

def put(n, sid, value, size=19, color=INK, bold=False, box=None):
    s=shape(n,sid)
    if box:
        s.left,s.top,s.width,s.height=[Inches(v) for v in box]
    return fill(s,value,size,color,bold)

def text(n, value, x,y,w,h,size=19,color=INK,bold=False):
    return fill(slide(n).shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h)),value,size,color,bold)

def remove(n,sid):
    s=shape(n,sid);s._element.getparent().remove(s._element)

def screenshot(n,name,x,y,w,h):
    file=ROOT/'docs/screenshots'/name
    iw,ih=Image.open(file).size
    # A top-aligned PowerPoint crop keeps screenshot pixels unchanged.
    pic=slide(n).shapes.add_picture(str(file),Inches(x),Inches(y),width=Inches(w),height=Inches(h))
    wanted=iw*h/w
    if wanted<ih:pic.crop_bottom=1-wanted/ih
    return pic

def note(n,value):
    slide(n).notes_slide.notes_text_frame.text=value

# 7: title, using the supplied organizer branding and the Rostelecom logo from slide 6.
put(7,811667492,'Пользователи 200',29,WHITE,True, (.42,.48,5.55,1.0))
put(7,225676857,'CRM для ИТ Школы\nРостелекома',34,WHITE,True,(.55,3.1,8.0,1.55))
put(7,979326395,'Система контроля и обработки статистических данных\nпо обучению студентов ВУЗов и школ по ИТ-направлениям',17,WHITE,False,(.58,5.1,9.2,1.25))
text(7,'ЛИДЕРЫ ЦИФРОВОЙ ТРАНСФОРМАЦИИ 2026',.58,6.67,9,.3,12,WHITE)
logo=shape(6,782868321).image.blob
slide(7).shapes.add_picture(BytesIO(logo),Inches(.58),Inches(2.35),width=Inches(2.3))
note(7,'Представляем команду «Пользователи 200» и CRM для сотрудников ИТ Школы Ростелекома. Решение объединяет образовательное партнёрство, документы, этапы работы и статистику подготовки ИТ-кадров.')

# 8: overview and all full names; the protected team slide follows unchanged.
remove(8,1753280885)
slide(8).shapes.add_picture(str(PHOTO),Inches(.38),Inches(.42),width=Inches(3.12),height=Inches(3.12))
text(8,'Пользователи\n200',3.72,.75,3.05,1.0,24,P,True)
text(8,'5 участников\nВолжский филиал ВолГУ\nВолжский, Волгоградская область',3.72,1.92,3.05,1.5,16,DARK)
put(8,1369185537,'Состав команды',17,P,True)
put(8,419332358,'Гончарова Ангелина Сергеевна — капитан\nРубцова Анастасия Михайловна\nТулупников Илья Дмитриевич\nЛалаян Эдуард Владимирович\nЛазимов Рамал Ариф оглы',14,DARK,False,(.4,4.25,6.3,2.65))
put(8,1970562306,'От первого контакта\nдо результата обучения',22,P,True,(7.46,1.15,5.35,1.12))
put(8,1225073325,'Что делает CRM',18,P,True)
put(8,1094275808,'Ведёт ВУЗы, программы и продукты.\nСвязывает этапы сотрудничества с договорами, лицензиями, файлами и статистикой.',19,INK,False,(7.46,3.0,5.35,1.7))
put(8,1995815798,'Особенность решения',18,P,True)
put(8,673533444,'Настраиваемый workflow + рейтинг программ по заявкам, обучающимся и потокам. Доступ к данным зависит от роли и назначений.',18,INK,False,(7.46,5.45,5.35,1.6))

# Original slide 9 is deliberately never accessed for modification.

put(10,1458052251,'КОМАНДА И ВЫЗОВЫ',20,WHITE,True)
put(10,764322044,'Пять ролей — один продукт',19,P,True,(.58,1.4,10.8,.4))
put(10,125629218,'Участники Волжского филиала ВолГУ закрывают анализ, интерфейс, backend, интеграции и качество. Распределение ролей и контакты — на предыдущем слайде.',18,INK,False,(.58,1.94,11.0,1.02))
put(10,1307299817,'Почему задача важна',19,P,True,(.58,3.18,11,.45))
put(10,1880041961,'Подготовка ИТ-кадров требует прозрачного сотрудничества с ВУЗами. Сотруднику нужна единая история: от первого контакта до обучения и контроля исполнения.',18,INK,False,(.58,3.85,11,.95))
put(10,1070648540,'Какие сложности решили',19,P,True,(.58,5.02,11,.45))
put(10,182026123,'Разные права — серверное разграничение данных. Разные таблицы — маппинг Excel. Нет контрактов API — заменяемые mock-адаптеры. Ограничения Windows — локальный запуск без Docker.',18,INK,False,(.58,5.7,11,1.0))
note(10,'История участия в прошлых хакатонах и личные достижения не добавлялись: подтверждённых данных о них не предоставлено. Описаны состав команды и реальные технические сложности проекта.')

put(11,612268779,'React + TypeScript: интерфейс без перезагрузок.\nFastAPI + PostgreSQL: данные, API, миграции и аудит.\nKeycloak: вход, JWT и три роли.\nRedis: кэш с работой без него при отказе.\nАдаптеры LMS / сайта и локальный AI-помощник.',19)
put(11,1731740780,'Внутренний инструмент для ИТ Школы и КАМов по ВУЗам.\nПилот на одном направлении → сбор обратной связи → расширение.\nМетрики пилота: срок этапа, полнота данных, время подготовки отчёта.\nЭффект оцениваем по результатам пилота; коммерческие показатели пока не измерены.',19)
put(11,1783022708,'Внедрение и польза',22,P,True)

# Product / marketing / business sections, using the provided layouts.
put(12,1313990260,'ПРОБЛЕМА И ЦЕЛЬ',24,P,True)
put(12,1875783975,'Сотрудничество с каждым ВУЗом проходит длинный путь: контакты, документы, лицензии, внедрение и обучение.\nРазрозненные таблицы затрудняют контроль этапов и сравнение программ.\nЦель CRM — сократить ручные операции и сделать статус каждого взаимодействия прозрачным.',23,INK)
text(12,'14',8.0,2.25,4,1.3,68,WHITE,True)
text(12,'базовых этапов\nв одном управляемом процессе',8.05,3.55,4.7,1.6,25,WHITE)

put(13,2082633713,'DASHBOARD НА ДАННЫХ CRM',24,WHITE,True,(.58,.48,10,.6))
remove(13,1935404044)
screenshot(13,'dashboard.png',.57,1.65,8.3,4.98)
text(13,'Единые фильтры',9.12,1.82,3.35,.7,21,P,True)
text(13,'Период, ВУЗ, направление, программа, продукт, ответственный и этап.',9.12,2.55,3.35,1.25,18)
text(13,'Статистика из БД',9.12,4.0,3.35,.55,21,P,True)
text(13,'Рейтинг программ и экспорт диаграмм PNG / PDF.\nНа экране — демоданные.',9.12,4.75,3.35,1.85,18)

put(14,239345494,'ВЗАИМОДЕЙСТВИЕ',22,P,True)
put(14,533860383,'ВУЗ + программа + ИТ-продукт\nОтветственный сотрудник\nДоговор и срок лицензии\nЭтапы, комментарии и файлы\nИстория: кто, когда и что изменил\nПодсказка следующего действия',20,INK,False,(.7,1.5,5.15,4.9))
remove(14,859679009)
screenshot(14,'interaction.png',6.58,1.35,6.3,4.8)
text(14,'Настраиваемый путь вместо фиксированного списка статусов',6.7,6.38,5.9,.65,16,WHITE)

put(15,1304804737,'ПОЛЬЗА И МЕТРИКИ ПИЛОТА',23,P,True,(.58,.45,11,.6))
rows=[('Сотрудник / КАМ','Единая карточка ВУЗа: меньше поиска по таблицам и переписке.'),('Руководитель','Назначения и нагрузка команды; видны текущие этапы.'),('ИТ Школа','Сравнение программ по заявкам, обучающимся и потокам.'),('Метрики внедрения','Время отчёта, длительность этапа, доля заполненных карточек.'),('Проверка эффекта','Замер «до / после» в пилоте. Экономия пока не подтверждена.')]
for j,(h,b) in enumerate(rows):
 y=1.88+j*.94
 put(15,[387293582,570677988,1284065627,1876004369,1787691646][j],h,18,P,True,(.58,y,3.5,.65))
 text(15,b,4.35,y,8.3,.7,18)

put(16,1278372885,'АРХИТЕКТУРА',20,WHITE,True)
heads=[2044349616,1071145442,688235115,2139186858]
bodies=[1977294603,1586499484,1215698215,1620825207]
nums=[2073917121,1438238244,510737862,1915185023]
for j,(h,b) in enumerate([
 ('Интерфейс','React / TypeScript\nMUI и Recharts\nTanStack Query\nDesktop и mobile'),
 ('Бизнес-логика','FastAPI / Pydantic\nREST / OpenAPI\nRBAC и аудит\nИмпорт и отчёты'),
 ('Данные','PostgreSQL\nSQLAlchemy / Alembic\nRedis: кэш\nФайлы вне БД'),
 ('Доступ и API','Keycloak / PKCE\nПроверка JWT\nLMS и Website\nЗаменяемые адаптеры')]):
 put(16,heads[j],h,19,P,True);put(16,bodies[j],b,17);put(16,nums[j],f'0{j+1}',28,PINK,True)
note(16,'Связи компонентов: браузер проходит вход через Keycloak и вызывает FastAPI с JWT. Backend обращается к PostgreSQL, Redis, файловому хранилищу и адаптерам внешних API. Подготовлен Docker Compose из пяти сервисов. Контейнерный запуск пока не проверен.')

put(17,2037246486,'ТРИ РОЛИ — РАЗНЫЕ ПРАВА',24,P,True)
for j,(role,title,body) in enumerate([
 ('USER','КАМ','Назначенные ВУЗы\nВзаимодействия\nРазрешённые этапы\nФайлы и комментарии\nОтчёты'),
 ('MANAGER','Руководитель','Данные подчинённых\nНазначение КАМов\nСмена ответственных\nКонтроль нагрузки\nКомандная аналитика'),
 ('ADMIN','Администратор','Пользователи и роли\nСправочники\nНастройка workflow\nПрава и параметры\nЖурнал аудита')]):
 put(17,[1030893452,2117719570,2083305194][j],role,19,PINK,True,([.85,5.05,9.35][j],1.96,3.0,.6))
 put(17,[128672613,768239325,281017996][j],title,20,P,True)
 put(17,[1879341390,1046827295,299291637][j],body,18)

put(18,513245146,'ФУНКЦИИ',20,WHITE,True)
cards=[('01','Excel без ручного переноса','XLS / XLSX → маппинг → preview → подтверждение и ошибки по строкам.'),('02','Отчёты под задачу','Выбор периода, фильтров и колонок. Экспорт XLS, XLSX, PDF, JSON.'),('03','Управляемый workflow','14 базовых этапов; можно менять порядок, названия, активность и права.'),('04','История и документы','Комментарии и вложения связаны с этапом. Переходы сохраняют автора и время.'),('05','API внешних систем','LMS / Website: новые записи, обновление существующих и аудит синхронизации.'),('06','Помощник без внешней LLM','Правила находят незаполненные поля и предлагают следующее действие.')]
ids=[(627595599,1592263424,1140510560),(276215088,2045507408,2068167021),(1221125376,90655918,334465192),(1273614701,1064143456,2060304069),(725878089,1409392635,1669306219),(1594503774,1379306717,520845544)]
for (a,b,c),(num,h,body) in zip(ids,cards):
 put(18,a,num,25,PINK,True);put(18,b,h,18,P,True);put(18,c,body,16,box=(shape(18,c).left/914400,shape(18,c).top/914400,4.5,.95))

put(19,1539679460,'ОТЧЁТЫ',20,WHITE,True)
for sid in [337698276,603718987,714864044,259753529]:remove(19,sid)
screenshot(19,'reports.png',.45,1.35,8.0,4.9)
text(19,'От выборки до файла',8.8,1.55,4.0,.65,23,P,True)
text(19,'01  Задайте фильтры\n02  Выберите колонки\n03  Проверьте preview\n04  Скачайте отчёт',8.8,2.5,4.0,2.4,20)
text(19,'В выгрузку попадают только данные, доступные текущему пользователю.',8.8,5.15,3.95,1.25,18,P)

put(20,884406034,'ПРОВЕРКИ',20,WHITE,True)
put(20,160532972,'Работающий локальный стенд\nPostgreSQL + Keycloak + API + web-интерфейс.\nПроверены три роли, workflow, комментарии, загрузка файлов и Excel.\n0 перезагрузок страницы при редактировании.\nИзмерения — на демоданных; это не гарантия production SLA.',21)
for sid,value in zip([656338683,1003591602,1895362509,2088102061,2001149553],[
 '14 / 14 backend-тестов: SQLite и PostgreSQL',
 '5 / 5 frontend-тестов; lint, TypeScript, build',
 '196–439 мс: три проверенные UI-операции',
 '50 сессий / 10 отчётов: без ошибок; p95 1,22 с',
 'Compose подготовлен; запуск контейнеров не проверен']):put(20,sid,value,16,P)
note(20,'Источники: docs/ACCEPTANCE.md, browser-results.json, ui-performance.json, load-sessions-results.json. UI: комментарий 196 мс, переход 439 мс, preview 238 мс. Нагрузка измерялась отдельно, без Redis; порог <=1 секунды под нагрузкой пока не подтверждён. Redis-кэш реализован, но настоящий Redis на этом стенде недоступен.')

put(24,701914234,'БЕЗОПАСНОСТЬ',20,WHITE,True)
for sid,value in zip([1951173445,1036787441,1628251778],[
 'ДОСТУП\nKeycloak и JWT\nТри роли\nПроверка назначений на сервере\nАудит изменений',
 'ДАННЫЕ И ФАЙЛЫ\nВалидация полей\nРазмер, MIME и расширение\nБезопасные имена файлов\nПараметризованные запросы',
 'ГРАНИЦЫ ГОТОВНОСТИ\nHTTPS, backup и мониторинг — на целевом стенде.\nСоответствие 152-ФЗ / ФСТЭК №117 требует оценки заказчика.']):
    put(24,sid,value,18)
    shape(24,sid).height=Inches(3.3)
note(24,'Не заявляем автоматическую сертификацию или полное нормативное соответствие. Это карта реализованных программных мер и оставшихся задач инфраструктуры.')

put(25,1498909464,'ПЛАН РАЗВИТИЯ',20,WHITE,True)
# Template cards are decorative and overlap its placeholders; put readable text above them.
for sid in [1966538093,1593293017,2102879176,2006174710,517539641,1748071264,1841270755,902079730,375464038,240942989]:remove(25,sid)
for x,y,title,body in [( .48,1.68,'Linux-стенд','Compose, Redis, TLS\nПубличный демодоступ'),(2.98,5.48,'Реальные API','Контракты LMS и сайта\nПроверка синхронизации'),(5.38,1.68,'Нагрузочный тест','50 пользователей\nОптимизация до ≤1 с'),(7.88,5.48,'Пилот в ИТ Школе','Обратная связь КАМов\nЗамер пользы и удобства'),(10.27,1.68,'Эксплуатация','Backup, мониторинг\nОценка требований ИБ')]:
 text(25,title,x,y,2.7,.4,17,P,True);text(25,body,x,y+.5,2.7,1.0,15)

# Final slide uses a clean purple template with its large white content panel.
put(26,1966271123,'ДЕМОНСТРАЦИЯ',20,WHITE,True)
for sid in [460826205,1144293732,939443870,1459294004,1935078250]:remove(26,sid)
text(26,'От контакта с ВУЗом\nдо прозрачного результата',.65,1.6,11.7,1.65,35,P,True)
text(26,'Войти → выбрать ВУЗ → изменить этап → приложить файл → получить отчёт',.68,3.65,11.7,1.15,24,INK)
text(26,'Пользователи 200',.68,5.35,8,.65,27,P,True)
text(26,'Капитан: Гончарова Ангелина Сергеевна  ·  @cristal_mell',.68,6.15,11.7,.55,18)
note(26,'Для локального показа: start-local.bat, http://localhost:3000; demo: admin/admin123, manager/manager123, user/user123. localhost не является публичной ссылкой для жюри. До подачи решения нужно опубликовать репозиторий, прототип, презентацию и документацию; публичные URL не придуманы.')

selected=list(range(7,21))+[24,25,26]
for n in selected:
    if n!=9 and not slide(n).has_notes_slide:
        note(n,'Слайд подготовлен по исходному ТЗ и реализованной CRM. Демонстрационные данные не являются статистикой реального внедрения.')

temp=WORK/'filled-template.pptx'
prs.save(temp)
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
with ZipFile(SOURCE) as src,ZipFile(temp) as gen:
    data={n:gen.read(n) for n in gen.namelist()}
    original={n:src.read(n) for n in src.namelist()}
    # Restore the original slide and every transitive dependency verbatim.
    protected=set()
    def restore(part):
        if part in protected or part not in original:return
        protected.add(part);data[part]=original[part]
        rel=posixpath.join(posixpath.dirname(part),'_rels',posixpath.basename(part)+'.rels')
        if rel in original:
            protected.add(rel);data[rel]=original[rel]
            for r in E.fromstring(original[rel]):
                if r.get('TargetMode')!='External':restore(posixpath.normpath(posixpath.join(posixpath.dirname(part),r.get('Target'))))
    restore('ppt/slides/slide9.xml')
    root=E.fromstring(data['ppt/presentation.xml']);lst=root.find('p:sldIdLst',NS)
    for i,el in enumerate(list(lst),1):
        if i not in selected:lst.remove(el)
    data['ppt/presentation.xml']=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
    if 'docProps/app.xml' in data:
        app=E.fromstring(data['docProps/app.xml'])
        for el in app.iter():
            if E.QName(el).localname=='Slides':el.text=str(len(selected))
        data['docProps/app.xml']=E.tostring(app,xml_declaration=True,encoding='UTF-8',standalone=True)
    with ZipFile(OUT,'w',ZIP_DEFLATED) as dest:
        for n,b in data.items():dest.writestr(n,b)
    assert data['ppt/slides/slide9.xml']==original['ppt/slides/slide9.xml']
    (WORK/'verification.json').write_text(json.dumps({'visible_slides':len(selected),'original_slide_order':selected,'protected_original_slide':9,'protected_final_position':3,'protected_parts_unchanged':len(protected),'slide9_sha256':hashlib.sha256(original['ppt/slides/slide9.xml']).hexdigest()},ensure_ascii=False,indent=2),encoding='utf-8')
print(OUT)
print('Slides:',len(selected),'Protected original slide 9 and dependencies:',len(protected))
