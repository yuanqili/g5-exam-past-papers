#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate index.html (light theme, responsive, navbar + sub-tabs) for the
G5 admissions past-paper library. Reads file tree + descriptions.json."""
import os, re, json, html

ROOT = os.path.dirname(os.path.abspath(__file__))
EXAMS = ["STEP", "TMUA", "ESAT", "TARA"]
BRAND = "航铂教育"
SUBEXAMS = ("NSAA", "ENGAA", "TSA", "BMAT")

# ---------- scan files ----------
def detect_type(name, category):
    if category == "Specifications": return "Specification"
    if category == "References": return "Reference"
    low = name.lower()
    if "answer key" in low: return "Answer Key"
    if "worked answers" in low: return "Worked Answers"
    if "examiner report" in low: return "Examiner Report"
    if "mark scheme" in low: return "Mark Scheme"
    if "explained answers" in low: return "Solutions"
    if "solution" in low or "hints" in low or "answers (all papers)" in low: return "Solutions"
    return "Question Paper"

def pill(t):
    if t == "Question Paper": return "试卷"
    if t == "Examiner Report": return "报告"
    return "答案"

PILL_ORDER = {"试卷": 0, "答案": 1, "报告": 2}
DESC_CN = {"Answer Key": "答案", "Worked Answers": "详解", "Solutions": "解析",
           "Mark Scheme": "评分标准", "Examiner Report": "考官报告"}

def unit_of(exam, nm):
    m = re.search(r'Sections?\s*1\s*&\s*2', nm)
    if m: return "Section 1·2"
    m = re.search(r'Paper\s*(\d)', nm)
    if m: return ("STEP " + m.group(1)) if exam == "STEP" else ("Paper " + m.group(1))
    m = re.search(r'Section\s*(\d)', nm)
    if m: return "Section " + m.group(1)
    return None

def cn_name(exam, nm, t):
    base = nm[:-4] if nm.lower().endswith(".pdf") else nm
    unit = unit_of(exam, base)
    allp = "all papers" in base.lower()
    specimen = "Specimen" in base or "specimen" in base
    if t == "Question Paper":
        label = unit if unit else ("全卷" if allp else base)
        if specimen and unit: label += "（样卷）"
        return label
    head = unit if unit else ("全卷" if allp else "")
    d = DESC_CN.get(t, "答案")
    return (head + " · " + d) if head else d

cos_map_path = os.path.join(ROOT, "cos_map.json")
COS_MAP = json.load(open(cos_map_path, encoding="utf-8")) if os.path.exists(cos_map_path) else {}

papers = {e: [] for e in EXAMS}      # 历年真题
resources = {e: [] for e in EXAMS}   # 考纲资源 (Specifications + References)

for exam in EXAMS:
    for dirpath, dns, fns in os.walk(os.path.join(ROOT, exam)):
        for f in sorted(fns):
            if not f.lower().endswith(".pdf"): continue
            rel = os.path.relpath(os.path.join(dirpath, f), ROOT)
            parts = rel.split(os.sep)
            category = parts[1] if len(parts) > 1 else ""
            t = detect_type(f, category)
            size = os.path.getsize(os.path.join(ROOT, rel))
            if category == "Papers":
                mid = parts[2:-1]
                sub = mid[0] if mid and mid[0] in SUBEXAMS else ""
                rest = mid[1:] if sub else mid
                glabel = " ".join(rest) if rest else "—"
                ym = re.search(r'(19|20)\d{2}', glabel)
                year = int(ym.group(0)) if ym else 0
                is_spec = "Specimen" in glabel or "specimen" in glabel
                base_name = cn_name(exam, f, t)
                if exam in ("ESAT", "TARA"):
                    # 用户按年份找：同一年内合并不同子考试，文件名前标注子考试
                    header = glabel if is_spec else str(year)
                    name = (sub + " · " + base_name) if sub else base_name
                else:
                    header = glabel
                    name = base_name
                papers[exam].append({
                    "header": header, "sub": sub, "year": year, "spec": is_spec,
                    "pill": pill(t), "porder": PILL_ORDER[pill(t)],
                    "name": name, "path": COS_MAP.get(rel, rel), "size": size,
                })
            else:
                resources[exam].append({
                    "cat": category, "name": f[:-4], "path": COS_MAP.get(rel, rel), "size": size,
                    "kind": "考纲" if category == "Specifications" else "资料",
                })

# group papers by header, sort groups (sub asc, specimen last, year desc)
def disp_header(h):
    if h.isdigit():
        return h + " 年"
    return (h.replace("Early Specimen", "早期样卷")
             .replace("Specimen", "样卷"))

def group_papers(items):
    groups = {}
    for it in items:
        groups.setdefault(it["header"], []).append(it)
    def gkey(h):
        its = groups[h]
        gspec = 1 if any(x["spec"] for x in its) else 0   # 样卷类排最后
        gyear = max((x["year"] for x in its), default=0)
        return (gspec, -gyear, h)
    ordered = []
    for h in sorted(groups, key=gkey):
        # 组内：先按子考试，再按类型(试卷/答案/报告)，再按名称
        arr = sorted(groups[h], key=lambda x: (x["sub"], x["porder"], x["name"]))
        ordered.append({"header": disp_header(h), "files": arr})
    return ordered

PAPERS = {e: group_papers(papers[e]) for e in EXAMS}
def res_sort(items):
    return sorted(items, key=lambda x: (0 if x["cat"] == "Specifications" else 1, x["name"]))
RES = {e: res_sort(resources[e]) for e in EXAMS}

# ---------- descriptions ----------
desc_path = os.path.join(ROOT, "descriptions.json")
DESC = json.load(open(desc_path, encoding="utf-8")) if os.path.exists(desc_path) else {}
courses_path = os.path.join(ROOT, "courses.json")
COURSES = json.load(open(courses_path, encoding="utf-8")) if os.path.exists(courses_path) else {}

counts = {e: len(papers[e]) + len(resources[e]) for e in EXAMS}
total = sum(counts.values())

PAPER_NOTES = {
 "ESAT": "缩写说明：同一年份下合并展示。ENGAA = 工程入学测试（Engineering Admissions Assessment）、NSAA = 自然科学入学测试（Natural Sciences Admissions Assessment），二者均为 ESAT 的前身真题，可用于练习。",
 "TARA": "缩写说明：同一年份下合并展示。TSA = 思维能力评估（Thinking Skills Assessment）、BMAT = 生物医学入学考试（BioMedical Admissions Test），均为官方推荐用于 TARA 备考的代练真题。",
}

PAPER_INTRO = {
 "STEP": [
  "覆盖范围：1987–2025 连续。1994–2019 每年含 STEP 1/2/3；STEP 1 已于 2020 年停考，故 2020 年起仅有 STEP 2、STEP 3；1987–1993 为旧格式（原 Maths / Further A / Further B，对应 Paper 1/2/3）。",
  "答案情况：2003 年及以前无官方解析；2004–2017 为「全卷打包」解析；2018 年起按卷拆分为解析 + 评分标准；2014 年起另含考官报告（报告胶囊）。",
  "参考价值：现行只考 STEP 2 与 STEP 3，应作为备考重点。2018 年至今的真题与当前题型、难度最接近，优先限时精做；2018 年以前风格略有差异，仍是优质练习；1987–1993 旧格式可作能力拓展。",
  "建议用法：先限时完成「试卷」，再对照「答案」，最后阅读「报告」了解评分标准与常见失分点。",
 ],
 "TMUA": [
  "覆盖范围：2016–2023，外加一套早期样卷（Early Specimen）。2024 年起 TMUA 改由 UAT-UK 以 Pearson VUE 机考形式进行，官方不再发布 PDF 真题，因此没有 2024 及以后的年份。",
  "每年内容：Paper 1（数学应用）+ Paper 2（数学推理），各配详解（Worked Answers）与答案速查（Answer Keys）。",
  "参考价值：虽已转为机考，但考纲与题型保持不变，历年纸笔真题仍是最有效的练习材料，建议全部做完；机考界面与节奏可另用官方在线练习适应。",
  "建议用法：限时做两卷 → 对照详解订正 → 用答案速查核对得分。",
 ],
 "ESAT": [
  "为什么是 NSAA / ENGAA：ESAT 是 2024 年新启用的考试，官方没有可下载真题（样题仅为在线机考）。这里收录其前身 NSAA（自然科学）与 ENGAA（工程）的历年真题作为练习，覆盖 2016–2023（含 Specimen 样卷）。",
  "每年内容：Section 1 与 Section 2 的题目及答案；同一年份下 NSAA 与 ENGAA 合并展示，文件名已标注所属考试。",
  "新老变化与参考价值：ESAT 改为多模块机考（Mathematics 1 必考 + 按专业选考 Math 2 / 物理 / 化学 / 生物），但内容仍基于中学数理，与 NSAA/ENGAA 高度重合——其数学、物理、化学、生物题目仍极具参考价值；主要差异是由分卷纸笔改为分模块上机多选，需注意作答节奏。",
  "建议用法：按目标专业所需模块，针对性选做对应科目的题目（如工程方向重点练 ENGAA 与数学/物理部分）。",
 ],
 "TARA": [
  "为什么是 TSA / BMAT：TARA 是 2026 年入学起的全新考试，官方只有在线样题与考纲，没有历年真题。官方推荐用已停考的 TSA、BMAT 的 Section 1 作为代练，本页据此收录。",
  "收录内容：TSA Section 1（2008–2023）+ Section 2 写作（2008–2022）+ 官方 Specimen 样卷；BMAT Section 1（2003–2023）。同一年份下合并展示，文件名标注所属考试。",
  "为何只收这些：TARA 的「批判性思维」「问题解决」两个客观模块承接 TSA/BMAT Section 1 的命题传统，写作模块类似 TSA 写作，因此这些最具参考价值；BMAT 的 Section 2（科学知识）与 Section 3 与 TARA 无关，未收录。",
  "建议用法：客观题练 TSA / BMAT 的 Section 1，写作练 TSA Section 2；新机考界面用官方在线样题适应。",
 ],
}

payload = json.dumps({"PAPERS": PAPERS, "RES": RES, "DESC": DESC, "COURSES": COURSES,
                      "NOTES": PAPER_NOTES, "INTRO": PAPER_INTRO, "COUNTS": counts,
                      "TOTAL": total, "EXAMS": EXAMS, "BRAND": BRAND}, ensure_ascii=False)

# ---------- HTML ----------
TPL = r'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>航铂教育 · 英国 G5 入学笔试真题库</title>
<style>
:root{--bg:#f6f8fc;--card:#fff;--ink:#1d2433;--mut:#6b7488;--line:#e6eaf2;--acc:#2f6bff;--acc-soft:#eaf1ff;--shadow:0 1px 3px rgba(20,40,90,.06),0 6px 20px rgba(20,40,90,.05)}
*{box-sizing:border-box}
html,body{margin:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--ink);line-height:1.6;-webkit-text-size-adjust:100%}
a{color:var(--acc);text-decoration:none}
.bar{background:var(--card);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:30}
.bar .in{max-width:1040px;margin:0 auto;padding:12px 18px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.brand{font-size:16px;white-space:nowrap;display:inline-flex;align-items:baseline;gap:9px}
.brand b{font-weight:800;color:var(--acc)}
.brand .sb{font-weight:400;color:var(--mut);font-size:16px}
.nav{display:flex;gap:6px;margin-left:auto;flex-wrap:wrap}
.nav button{border:1px solid var(--line);background:var(--card);color:var(--mut);padding:7px 16px;border-radius:999px;font-size:14px;cursor:pointer;font-weight:600;transition:.15s}
.nav button.on{background:var(--acc);border-color:var(--acc);color:#fff}
.wrap{max-width:1040px;margin:0 auto;padding:18px}
.hero{padding:10px 2px 2px}
.hero .l1{font-size:25px;font-weight:800;margin:2px 0;line-height:1.25}
.hero .l1 .abbr{color:var(--acc);margin-right:8px}
.hero .l2{font-size:14px;color:#454e60;font-weight:600;margin-top:2px}
.hero .l3{font-size:13px;color:var(--mut);margin-top:4px}
.subtabs{display:flex;gap:6px;margin:16px 0 6px;border-bottom:1px solid var(--line);overflow-x:auto}
.subtabs button{border:0;background:none;color:var(--mut);padding:10px 4px;margin-right:14px;font-size:15px;cursor:pointer;font-weight:600;border-bottom:2px solid transparent;white-space:nowrap}
.subtabs button.on{color:var(--acc);border-bottom-color:var(--acc)}
section.card{background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);padding:18px;margin:14px 0}
section.card h3{margin:0 0 12px;font-size:17px;display:flex;align-items:center;gap:8px}
section.card h3::before{content:"";width:4px;height:16px;background:var(--acc);border-radius:3px}
.lead{color:var(--mut);font-size:13px;margin:-4px 0 14px}
table{width:100%;border-collapse:collapse;font-size:14px;overflow:hidden;border-radius:10px}
th,td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--acc-soft);color:#2a4a8f;font-weight:700;white-space:nowrap}
tr:last-child td{border-bottom:0}
.kv td:first-child{white-space:nowrap;color:var(--mut);font-weight:600;width:36%}
p.para{margin:0 0 10px;white-space:pre-wrap}
.faq-item{border:1px solid var(--line);border-radius:10px;margin:8px 0;overflow:hidden;background:var(--card)}
.faq-q{cursor:pointer;padding:11px 14px;font-weight:600;font-size:14px;display:flex;align-items:center;gap:8px;user-select:none;transition:background .2s}
.faq-q .qi{color:var(--acc);font-weight:800}
.faq-q .chev{margin-left:auto;color:var(--mut);transition:transform .28s ease;font-size:12px}
.faq-item.open .faq-q{background:var(--acc-soft)}
.faq-item.open .faq-q .chev{transform:rotate(180deg)}
.faq-panel{display:grid;grid-template-rows:0fr;transition:grid-template-rows .28s ease}
.faq-item.open .faq-panel{grid-template-rows:1fr}
.faq-ans-in{overflow:hidden}
.faq-ans{padding:0 14px;color:#39414f;font-size:14px;white-space:pre-wrap;line-height:1.75;transition:padding .28s ease}
.faq-item.open .faq-ans{padding-top:13px;padding-bottom:14px}
/* 航铂课程 */
.plan{margin:16px 0}
.plan .ph{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:8px}
.plan .pn{font-size:16px;font-weight:700}
.plan .pl{font-size:13px;font-weight:700;color:var(--acc);background:var(--acc-soft);padding:2px 10px;border-radius:7px}
.plan .pf{font-size:12.5px;color:var(--mut)}
.course-intro{color:#454e60;font-size:14px;margin:0 0 4px}
.cta{margin-top:6px;color:var(--mut);font-size:13px}
.tnum{white-space:nowrap;color:var(--mut);width:14%}
.thr{white-space:nowrap;width:14%}
.grp{margin:14px 0}
.grp .gh{font-size:15px;font-weight:700;margin:0 0 8px;display:flex;align-items:center;gap:8px}
.grp .gh .y{color:var(--acc)}
.files{display:grid;gap:8px}
.f{display:flex;align-items:center;gap:11px;padding:11px 13px;background:var(--card);border:1px solid var(--line);border-radius:11px;transition:.12s}
.f:hover{border-color:var(--acc);box-shadow:var(--shadow)}
.f:active{transform:scale(.997)}
.pill{font-size:12px;font-weight:700;padding:3px 10px;border-radius:7px;white-space:nowrap}
.p-试卷{background:#e7f0ff;color:#2f6bff}
.p-答案{background:#e6f7ee;color:#16a163}
.p-报告{background:#fdeede;color:#c9821a}
.f .nm{flex:1;font-size:14px;color:var(--ink)}
.f .sz{color:var(--mut);font-size:12px;white-space:nowrap}
.res{display:grid;grid-template-columns:1fr;gap:8px}
.muted{color:var(--mut);font-size:13px}
.pnote{background:#fff8ec;border:1px solid #f2e2c2;color:#7a5a1e;font-size:13px;line-height:1.7;padding:10px 13px;border-radius:10px;margin-bottom:14px}
.pintro{margin:0;padding-left:20px}
.pintro li{font-size:13.5px;color:#39414f;line-height:1.75;margin:6px 0}
.pintro li::marker{color:var(--acc)}
footer{border-top:1px solid var(--line);background:var(--card);padding:28px 18px;margin-top:22px}
.foot{max-width:1040px;margin:0 auto;display:flex;align-items:center;justify-content:center;gap:22px;flex-wrap:wrap}
.foot .qr{width:158px;border-radius:12px;box-shadow:var(--shadow);display:block}
.foot-txt{text-align:left;max-width:340px}
.foot-h{font-size:17px;font-weight:800;color:var(--ink)}
.foot-p{font-size:13.5px;color:#454e60;margin-top:7px;line-height:1.7}
.foot-sub{font-size:12px;color:var(--mut);margin-top:16px}
@media(max-width:540px){.foot{flex-direction:column;gap:14px}.foot-txt{text-align:center;max-width:100%}.foot .qr{width:100%}}
@media(min-width:680px){.res{grid-template-columns:1fr 1fr}}
@media(max-width:560px){.brand .sb{display:none}.hero .l1{font-size:22px}.nav button{padding:6px 12px;font-size:13px}}
</style>
</head>
<body>
<div class="bar"><div class="in">
  <span class="brand"><b>航铂教育</b><span class="sb">英国 G5 入学笔试真题库</span></span>
  <nav class="nav" id="nav"></nav>
</div></div>
<div class="wrap">
  <div class="hero" id="hero"></div>
  <div class="subtabs" id="subtabs"></div>
  <div id="content"></div>
</div>
<footer><div class="foot">
  <img class="qr" src="assets/advisor-qr.png" alt="课程顾问企业微信二维码">
  <div class="foot-txt">
    <div class="foot-h">扫码添加课程顾问企业微信</div>
    <div class="foot-p">获取专属课程资源、历年真题与一对一备考规划，了解航铂教育各考试课程方案。</div>
    <div class="foot-sub">航铂教育　·　共 <span id="tot"></span> 份资料　·　仅供个人备考学习使用</div>
  </div>
</div></footer>
<script>
const D=__DATA__;
let curExam=D.EXAMS[0], curTab="intro";
const TABS=[["intro","考试介绍"],["course","航铂课程"],["res","考纲资源"],["papers","历年真题"]];
const esc=s=>(s==null?"":String(s)).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
const enc=p=>p.split("/").map(encodeURIComponent).join("/");
const pdfHref=p=>"viewer.html?f="+encodeURIComponent(p);
const sz=b=>b>1048576?(b/1048576).toFixed(1)+" MB":Math.round(b/1024)+" KB";

function nav(){
  document.getElementById("nav").innerHTML=D.EXAMS.map(e=>`<button data-e="${e}" class="${e===curExam?'on':''}">${e}</button>`).join("");
  document.querySelectorAll("#nav button").forEach(b=>b.onclick=()=>{curExam=b.dataset.e;curTab="intro";render();window.scrollTo(0,0)});
  const d=D.DESC[curExam]||{};
  document.getElementById("hero").innerHTML=
    `<div class="l1"><span class="abbr">${esc(curExam)}</span>${esc(d.name_zh||"")}</div>`+
    (d.name_en?`<div class="l2">${esc(d.name_en)}</div>`:"")+
    (d.tagline?`<div class="l3">${esc(d.tagline)}</div>`:"");
}
function subtabs(){
  document.getElementById("subtabs").innerHTML=TABS.map(([k,t])=>`<button data-t="${k}" class="${k===curTab?'on':''}">${t}</button>`).join("");
  document.querySelectorAll("#subtabs button").forEach(b=>b.onclick=()=>{curTab=b.dataset.t;render()});
}
function tbl(o){
  if(!o||!o.headers)return"";
  return`<table><thead><tr>${o.headers.map(h=>`<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${
    o.rows.map(r=>`<tr>${r.map(c=>`<td>${esc(c)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
}
function sec(title,body){return body?`<section class="card"><h3>${esc(title)}</h3>${body}</section>`:""}
function block(o){ // {text, table}
  if(!o)return"";
  if(typeof o==="string")return`<p class="para">${esc(o)}</p>`;
  let h="";if(o.text)h+=`<p class="para">${esc(o.text)}</p>`;if(o.table)h+=tbl(o.table);return h;
}
function renderIntro(){
  const d=D.DESC[curExam];
  if(!d||!d.summary&&!d.background)return`<section class="card"><div class="muted">考试介绍整理中…</div></section>`;
  let h="";
  if(d.summary)h+=`<section class="card"><h3>速览</h3><table class="kv"><tbody>${d.summary.map(r=>`<tr><td>${esc(r[0])}</td><td>${esc(r[1])}</td></tr>`).join("")}</tbody></table></section>`;
  h+=sec("背景与目的",block(d.background));
  h+=sec("考试日期",block(d.dates));
  h+=sec("考试内容",block(d.content));
  h+=sec("适用学校",block(d.schools));
  h+=sec("试卷难度",block(d.difficulty));
  h+=sec("评分方式",block(d.scoring));
  if(d.faq&&d.faq.length)h+=`<section class="card"><h3>常见问题</h3><div class="faq">${d.faq.map(f=>`<div class="faq-item"><div class="faq-q"><span class="qi">Q</span><span>${esc(f.q)}</span><span class="chev">▼</span></div><div class="faq-panel"><div class="faq-ans-in"><div class="faq-ans">${esc(f.a)}</div></div></div></div>`).join("")}</div></section>`;
  return h;
}
function renderCourse(){
  const c=(D.COURSES||{})[curExam];const meta=(D.COURSES||{})._plans_meta||[];
  if(!c||!meta.length)return`<section class="card"><div class="muted">课程方案整理中…</div></section>`;
  let h=`<section class="card"><h3>航铂课程方案</h3><p class="course-intro">${esc(D.COURSES._intro||"")}</p></section>`;
  meta.forEach(m=>{
    const rows=c[m.key];if(!rows)return;
    h+=`<section class="card"><div class="plan"><div class="ph"><span class="pn">${esc(m.name)}</span><span class="pl">${esc(m.load)}</span></div><div class="pf">适合：${esc(m.fit)}</div></div>`+
      `<table style="margin-top:10px"><thead><tr><th class="tnum">节次</th><th class="thr">课时</th><th>授课内容</th></tr></thead><tbody>`+
      rows.map(r=>`<tr><td class="tnum">${esc(r[0])}</td><td class="thr">${esc(r[1])}</td><td>${esc(r[2])}</td></tr>`).join("")+
      `</tbody></table></section>`;
  });
  h+=`<section class="card"><div class="cta">以上为标准课表，可按学员基础与目标分数定制调整。课程详情与排课请咨询 <b>航铂教育</b>。</div></section>`;
  return h;
}
function renderRes(){
  const r=D.RES[curExam]||[];if(!r.length)return`<section class="card"><div class="muted">暂无</div></section>`;
  const specs=r.filter(x=>x.cat==="Specifications"),refs=r.filter(x=>x.cat!=="Specifications");
  const card=(title,arr)=>arr.length?`<section class="card"><h3>${title}</h3><div class="res">${arr.map(x=>`<a class="f" href="${pdfHref(x.path)}" target="_blank"><span class="pill p-报告">${x.kind}</span><span class="nm">${esc(x.name)}</span><span class="sz">${sz(x.size)}</span></a>`).join("")}</div></section>`:"";
  return card("官方考纲",specs)+card("教材与参考资料",refs);
}
function renderPapers(){
  const g=D.PAPERS[curExam]||[];if(!g.length)return`<section class="card"><div class="muted">暂无</div></section>`;
  const intro=(D.INTRO||{})[curExam]||[];
  const introHtml=intro.length?`<section class="card"><h3>如何使用本页</h3><ul class="pintro">${intro.map(x=>`<li>${esc(x)}</li>`).join("")}</ul></section>`:"";
  const note=(D.NOTES||{})[curExam];
  const noteHtml=note?`<div class="pnote">${esc(note)}</div>`:"";
  return introHtml+`<section class="card">${noteHtml}${g.map(grp=>`<div class="grp"><div class="gh"><span class="y">${esc(grp.header)}</span><span class="muted">· ${grp.files.length} 份</span></div><div class="files">${
    grp.files.map(f=>`<a class="f" href="${pdfHref(f.path)}" target="_blank"><span class="pill p-${f.pill}">${f.pill}</span><span class="nm">${esc(f.name)}</span><span class="sz">${sz(f.size)}</span></a>`).join("")
  }</div></div>`).join("")}</section>`;
}
function render(){
  nav();subtabs();
  document.getElementById("content").innerHTML=
    curTab==="intro"?renderIntro():curTab==="course"?renderCourse():curTab==="res"?renderRes():renderPapers();
}
document.getElementById("content").addEventListener("click",e=>{
  const q=e.target.closest(".faq-q");if(q)q.closest(".faq-item").classList.toggle("open");
});
document.getElementById("tot").textContent=D.TOTAL;
render();
</script>
</body>
</html>'''

out = TPL.replace("__DATA__", payload)
open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(out)
print("index.html written:", len(out), "bytes; total files:", total, counts)

VIEWER = r'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>航铂教育 · 文档查看</title>
<style>
:root{--acc:#2f6bff}
*{box-sizing:border-box}html,body{margin:0;height:100%}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:#f6f8fc;display:flex;flex-direction:column;height:100vh;height:100dvh}
.vbar{background:#fff;border-bottom:1px solid #e6eaf2;padding:10px 14px;display:flex;align-items:center;gap:12px;flex-shrink:0}
.vbar .b{font-weight:800;color:var(--acc);white-space:nowrap}
.vbar .nm{font-size:13px;color:#454e60;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.vbar a{font-size:13px;color:var(--acc);text-decoration:none;white-space:nowrap;font-weight:600}
.stage{flex:1;position:relative;min-height:0}
iframe{width:100%;height:100%;border:0;background:#fff;display:block}
.load{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;background:#f6f8fc;transition:opacity .35s}
.load.hide{opacity:0;pointer-events:none}
.spin{width:44px;height:44px;border:4px solid #d8e2f5;border-top-color:var(--acc);border-radius:50%;animation:spin .9s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.lt{color:#6b7488;font-size:14px;font-weight:600}
.slow{font-size:13px;color:#8b93ad}.slow a{color:var(--acc);font-weight:600}
</style>
</head>
<body>
<div class="vbar"><span class="b">航铂教育</span><span class="nm" id="nm"></span><a id="dl">下载 ⬇</a><a id="open" target="_blank" rel="noopener">在新标签打开 ↗</a></div>
<div class="stage">
  <iframe id="fr" title="PDF" allow="fullscreen"></iframe>
  <div class="load" id="load">
    <div class="spin"></div>
    <div class="lt" id="lt">正在加载 PDF…</div>
    <div class="slow" id="slow" style="display:none">没有自动打开？<a id="open2" target="_blank" rel="noopener">点此打开</a> · <a id="dl2">下载</a></div>
  </div>
</div>
<script>
var p=new URLSearchParams(location.search).get("f")||"";
var isHttp=/^https?:\/\//i.test(p);
var raw=isHttp?p:p.split("/").map(encodeURIComponent).join("/");
// COS 公有读对象用「数据万象文档预览」渲染为 HTML，规避浏览器把 PDF 当下载
var preview=isHttp?(raw+(raw.indexOf("?")>-1?"&":"?")+"ci-process=doc-preview&dstType=html"):raw;
var name=decodeURIComponent((p.split("/").pop()||"")).replace(/\?.*$/,"").replace(/\.pdf$/i,"");
document.getElementById("nm").textContent=name;
if(name)document.title="航铂教育 · "+name;
var fname=decodeURIComponent((p.split("/").pop()||"")).replace(/\?.*$/,"");
["open","open2"].forEach(function(id){document.getElementById(id).href=preview;});
["dl","dl2"].forEach(function(id){var a=document.getElementById(id);a.href=raw;a.setAttribute("download",fname);});
var fr=document.getElementById("fr"),load=document.getElementById("load");
if(!p){
  document.getElementById("lt").textContent="未指定文件";
}else{
  fr.onload=function(){load.classList.add("hide");};
  fr.src=preview;
  setTimeout(function(){if(!load.classList.contains("hide"))document.getElementById("slow").style.display="block";},5000);
}
</script>
</body>
</html>'''
open(os.path.join(ROOT, "viewer.html"), "w", encoding="utf-8").write(VIEWER)
print("viewer.html written:", len(VIEWER), "bytes")
