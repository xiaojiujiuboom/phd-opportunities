# 博士机会网站现状与扩展方案

分析日期：2026-09-27。上游：<https://github.com/Zeshengliu213/phd-europe-app>。
本地基线：main，commit `878534c`（2026-04-23）。
本轮完成源码和已提交数据审计；没有重新抓取全部来源，没有上线新站。

## 结论

适合在现有项目上扩展。保留中英双语、搜索、国家/学校分组、收藏和详情视图；优先修复数据时效、职位分类、抓取失败处理，再增加国家。
“全额资助”“雇员身份”“居留类型”是三个独立判断。不能根据国家、R1 标签、有 stipend 或 RA/TA 推断工作签证。
美国、加拿大、澳大利亚、新西兰的机会应独立区分院系招生、具体项目和奖学金，再与欧洲雇员博士统一检索。

## 已核验现状

### 实现

- 静态 SPA：`index.html` 集中包含 HTML、CSS、JavaScript，没有 package.json，也没有前端构建步骤。
- `scraper/fetch.py` 顺序运行来源适配器，写入 JSON；Python 依赖为 requests、BeautifulSoup、lxml。
- 11 个顶层适配器模块；Varbi 覆盖多个大学子来源。博士快照实际有 15 个 source 值。
- 已有博士/博后切换、中英双语、国家/学科筛选、日期排序、URL 查询状态、localStorage 收藏、学校名称归一化和 QS 徽章。
- Supabase 文件仅提供收藏表；现前端已经移除账号集成，不需要为了扩展而立即增加数据库。
- 地图目前仅支持欧洲。AU/NZ/CA/US 尚未加入国家名称、国旗和中文映射。

### 数据质量（博士快照）

| 指标 | 结果 |
| --- | ---: |
| 最后更新 | 2026-04-20T13:33:22Z |
| 总记录 | 1,151 |
| 非空国家代码 | 23；另有 5 条国家未知 |
| 截止日早于分析日期 | 820（71.2%） |
| 缺截止日 | 326（28.3%） |
| 有日期且尚未过截止日 | 5（仍须在原网站核实是否开放） |
| 缺 description_html | 748（65.0%） |
| 缺联系人 | 1,104（95.9%） |
| 缺研究领域 | 340（29.5%） |
| 缺城市 | 488 |
| 缺发布日期 | 230 |
| 同标题同学校的额外记录 | 110；仅是重复候选，不能直接删除 |

前端会隐藏已过截止日的记录，保留缺日期记录。以快照计算，最多留下 331 条；326 条没有截止日，占 98.5%，不能据此视为“开放岗位”。
博后快照是 2026-04-21：711 条，619 条已过截止日，其余 92 条全部缺日期。

主要来源的详情缺失：EURAXESS 487/487，jobs.ac.uk 200/200，academics 21/21，PhDGermany 40/40。
部分来源支持详情抓取，但默认关闭，所以数据不全不仅来自覆盖不足，也来自采集策略。

### 可定位的问题

1. README 声称存在 `.github/workflows/scrape.yml` 并每 6 小时更新；当前仓库树没有 `.github` 目录。无法仅凭仓库断定线上是否有外部更新机制。
2. README 所述单来源、字段及 `--with-details` 参数与现实现不一致；当前详情抓取由各来源环境变量控制。
3. EURAXESS 以 R1 作为博士代理条件，但列表中明确包含 Postdoctoral、Assistant Professor、Research Technician 等非博士职位。R1 不能作为充分条件。
4. AcademicTransfer 固定截断前 120 个匹配 URL；jobs.ac.uk 默认最多约 200 条；其他来源也有页数上限。没有报告未采集覆盖量。
5. AcademicTransfer 能读 JSON-LD，却未保留其中可能存在的薪酬、雇佣类型等属性。
6. 编排器在来源失败后继续，并以成功来源覆盖整个旧快照；即便全部失败也会写空数据，最后返回成功。缺少保留旧数据、部分失败标志、原子写入和失败退出策略。
7. `stats.py` 有来源骤降告警，但未集成进 fetch.py；没有独立的来源运行状态和抓取尝试时间。
8. 未发现跨来源统一去重步骤。同标题同学校可能包含复发广告、多职位或不同地点，应结合官方 vacancy ID 和 URL 判定。
9. `research_fields` 是粗关键词分类，未覆盖 PIC、kinetic modelling、HPC、Bayesian optimisation、Scientific ML 等技能筛选。
10. 原站详情把外部 description_html 直接插入 HTML；扩展来源前应加入清洗和 URL scheme 检查。
11. 部分现有抓取请求设为 `verify=False`；应恢复 TLS 验证，来源证书错误独立记录。
12. 现数据没有结构化薪酬、学费覆盖、雇员身份、合同期限、国际生资格、签证证据或导师字段；原文有提及也不能可靠筛选。
13. SEO、站名、说明、地图、反馈链接均写死欧洲或上游域名。Fork 发布前需替换自身站点信息。

## 新国家的数据设计

先提供统一卡片，用 opportunity_type 区分四类：

- employed_phd：明确有博士雇佣合同。
- funded_project：导师发布的具体博士项目；资助和身份分别核验。
- scholarship：奖学金机会；不等于已被博士项目录取。
- doctoral_program：院系/研究生院招生； funding policy 不等于个人已获资助。

可存在多个关联记录：项目关联导师、院系项目和可申请奖学金，不把它们简单去重成同一个岗位。

建议字段：

| 类别 | 关键字段 |
| --- | --- |
| 身份 | opportunity_type, employment_status, contract_duration_months |
| 经费 | funding_type, amount_min/max, currency, period, gross_or_net, guaranteed_years |
| 学费 | tuition_coverage, international_fee_gap, mandatory_fees |
| 时间 | deadline, deadline_timezone, deadline_kind, start_date, intake_year, status |
| 资格 | international_eligible, citizenship_restrictions, degree_requirements, language_requirements |
| 研究 | supervisor, group_url, research_topics, methods, required_skills |
| 居留 | permit_route, permit_evidence_url, permit_last_verified；不能填 guaranteed_work_visa |
| 溯源 | source_url, official_url, apply_url, vacancy_id, first_seen, last_seen, last_verified |
| 证据 | field_evidence（原文片段、URL、核验时间）, extraction_method, confidence |

未知值显示“未说明/待核验”，不能默认为全奖、可招国际生或有工作居留。
金额保留原币种及月/年口径；月工资与年度 stipend 不应直接按裸数字排序。

## 来源接入建议

以下是第一批接入候选，并非已经完成或承诺覆盖全国。需逐来源验证页面结构、官方权限规则、分页、robots 和数据可用性。

| 地区 | 推荐首批官方入口 | 应收录的信息 |
| --- | --- | --- |
| 欧洲 | 现有来源 + 按优先国家补大学官方招聘源 | 雇员岗位、合同证据、完整详情、国际生限制 |
| 澳大利亚 | ANU、Melbourne、Monash、UNSW、Sydney、UQ 的 HDR 项目和奖学金目录 | 具体导师项目、stipend、国际学费覆盖、RTP/校奖申请流程 |
| 新西兰 | Auckland、Otago、Victoria University of Wellington、Canterbury | 具体项目、doctoral scholarship、导师联系流程、国际生适用条件 |
| 加拿大 | UBC、Toronto、McGill、Waterloo、Alberta 的项目/院系及官方资金政策 | 录取轮次、导师招生、funding package 及学费扣除情况 |
| 美国 | MIT、Ohio State、UCSD、Rochester 等与用户背景相关的院系和研究组 | 2027 招生、导师/组、RA/TA/fellowship 保证期限、院系截止日期 |

聚合网站可用于发现，再用大学、机构或政府页面核实。避免仅增加国家代码却没有真实来源。
美国/加拿大从适合用户的物理、工程、计算科学院系起步，比立即抓全国全部学科更可维护。
如果目标是公共综合网站，应保留全学科；用户专属研究偏好作为独立筛选，不写死在采集条件中。

## 制度差异的官方例证

- Melbourne 的 stipend 与 fee offset 是不同福利项目；部分申请可能获得仅学费减免，不能自动标为覆盖生活费。
  <https://scholarships.unimelb.edu.au/awards/graduate-research-scholarships>
- Auckland 给国际生提供 doctoral scholarship，并要求符合适用学费政策；有奖学金候选资格不等于已经获奖。
  <https://www.auckland.ac.nz/en/study/scholarships-and-awards/scholarship-types/scholarships-for-international-students/doctoral-scholarships-for-international-students.html>
- UBC-Vancouver 自 2026 年 9 月起的最低博士 funding package 覆盖前四年，资金可来自奖项、助教、RA 等组合。不得自动覆盖其他校区或加拿大所有大学。
  <https://www.grad.ubc.ca/awards/minimum-funding-policy-phd-students>
- MIT 的 doctoral funding 可来自 RA/TA/fellowship，具体支持范围需核对部门和 offer；部分九个月资助需要另查暑期支持。
  <https://oge.mit.edu/graduate-admissions/costs-funding/stipend-rates/>

## 用户专属筛选

- 首选有雇佣合同且能核验研究/工作居留路径的机会。
- 德国可以排除；不从公共数据库删掉德国。
- 同时提供全额资助但属于学生路线的澳新/北美机会，明确身份差异。
- 匹配词：PIC / particle-in-cell / kinetic plasma / laser-plasma / accelerator physics / computational electromagnetics / HPC / Bayesian optimisation / surrogate model / uncertainty quantification / scientific machine learning。
- 对匹配结果展示“已有能力、可迁移点、需要补的知识”；不能因通用 machine learning 词汇命中而声称高度适合。

## 实施顺序与验收

1. 数据基础：标准化 schema、来源运行日志、失败保留策略、原子写入、有效期状态和职位分类。测试涵盖缺日期、过期、所有来源失败、混合职位及重复职位。
2. 欧洲详情：启用带缓存的详情补全，明确每来源采集上限，先恢复现有优势国家的可用数据。
3. 新国家 MVP：每个 AU/NZ/CA/US 接入少量已验证官方来源，至少能展示真实机会、证据和最后核验日期。
4. 界面：洲/地区导航、四类机会、合同/资助/国际生资格筛选；保留来源未知数据但不误标“在招”。
5. 申请工作流：收藏之外增加申请状态、导师联系记录、截止提醒和导出；先本地保存即可。
6. 定时采集：补 CI、来源失败告警、重试和保守频率。显示 last_successful_fetch，不能把尝试时间当成数据更新时间。
7. 发布：核验上游许可、替换域名和作者信息、检查移动端，然后部署。

## 本轮边界与待解决事项

- 本地 clone 已完成；upstream 指向原作者，origin 指向 xiaojiujiuboom/phd-opportunities；没有向原作者仓库推送。
- 已通过 GitHub Import 创建保留历史的独立私有副本。公开仓库的 GitHub Fork 不能改为私有，因此采用独立副本。
- 当前仓库未见 LICENSE；保留作者信息。在公开分发改版前需核实许可或取得授权，不能自行补 MIT 许可。
- 后续清理已实现：仅博士、排除过期/关闭/混合职位，缺截止日期且超过7天未观察的记录淘汰；删除博士后数据文件和页面入口。
- 2026-09-27清理旧快照后剩5条截止日期未过的德国记录，尚未逐条核验在招；页面保留原始更新时间并提示陈旧。澳新加美来源尚未接入，也未做新的完整抓取。
