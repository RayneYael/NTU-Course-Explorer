# NTU 本科课程爬虫

[English](README.md) | 中文

抓取 NTU 本科各专业、各年级、各学期的完整课程信息，按快照存档。

| 数据来源 | 内容 |
|---|---|
| [Class Schedule](https://wish.wis.ntu.edu.sg/webexe/owa/AUS_SCHEDULE.main)（`AUS_SCHEDULE`） | index、类型、组别、星期、时间、地点、教学周、学分、UE/BDE/GE 标记 |
| [Content of Courses](https://wish.wis.ntu.edu.sg/webexe/owa/aus_subj_cont.main)（`AUS_SUBJ_CONT`） | 课程描述、先修要求、互斥课程、成绩类型、不开放的专业 |

两者按课程号合并。

## 安装

需要 Python 3.10 或更高版本。

```bash
pip install -r requirements.txt
```

## 常用命令

`--sem` 可以写学期编号，也可以写 NTU 网站上显示的学期名称（不区分大小写）。不写时默认使用网站下拉框的第一项，也就是最新学期。

| 编号 | 名称 |
|---|---|
| `2026_1` | `"Acad Yr 2026 Semester 1"` |
| `2025_2` | `"Acad Yr 2025 Semester 2"` |
| `2025_S` | `"Acad Yr 2025 Special Term"` |

编号也可以写成 `2026-1` 或 `2026;1`。注意分号在 shell 里是命令分隔符，用分号写法时必须加引号（`'2026;1'`）。完整列表可以用 `python -m ntu_courses semesters` 查看。

```bash
# 查看网站上可选的学期（编号和名称）
python -m ntu_courses semesters

# 查看某学期的专业/年级列表，-f 按关键字过滤
python -m ntu_courses programmes --sem 2026_1 -f computer

# 实时查看某个专业/年级的课程；-c 只看一门课，--no-desc 不显示描述
python -m ntu_courses show -p 'CSC;;1;F' --sem "Acad Yr 2026 Semester 1" -c SC1005

# 按课程号或关键字搜索课表
python -m ntu_courses search SC100 --sem 2026_1

# 抓取并存档（写入一个新快照）
python -m ntu_courses crawl                           # 最新学期
python -m ntu_courses crawl --sem 2025_2 --sem 2025_S # 指定学期，可重复
python -m ntu_courses crawl --all                     # 下拉框里的全部学期
python -m ntu_courses crawl --limit 5 --data /tmp/t   # 试跑：只抓前 5 个专业，写到临时目录

# 列出已保存的快照（* 为当前 LATEST）
python -m ntu_courses snapshots

# 为网页界面导出每个已抓取学期的最新数据（不联网）
python -m ntu_courses export-web
```

全局参数 `--delay`（默认 0.5 秒）控制两次请求之间的最小间隔，要放在子命令前面，例如 `python -m ntu_courses --delay 1 crawl`。一个学期大约有 680 个专业/年级，全量抓取约 15–20 分钟。建议把输出重定向到日志文件：

```bash
mkdir -p logs && python -m ntu_courses crawl > logs/crawl_$(date +%F).log 2>&1
```

## 快照存档

```
data/
  LATEST                         最新一次完整成功的快照名
  snapshots/
    2026-09-26T053215Z/          每次抓取新建一个目录（UTC 时间），从不修改或覆盖
      manifest.json              抓取时间、每个学期的哈希、专业/课程/index 数量、错误列表
      2026_1.json.gz             每个学期一个文件
```

- **只新增，不覆盖**：每次 `crawl` 都会新建快照，旧快照原样保留。
- **按学期去重**：某学期的内容和上一次完全一样时，manifest 里只记一个 `stored_in`，指向已有文件，不重复存数据。
- **只有完整快照才会成为 LATEST**：有专业/年级重试一次后仍然失败时，快照照样保存，但标记为 `complete=false`，`LATEST` 不变。
- **不会留下写到一半的快照**：数据先写到 `.tmp` 目录，全部完成后才改名。

## 数据格式

每个学期文件（gzip 压缩的 JSON）结构如下：

```jsonc
{
  "format": 2,
  "semester": {"key": "2026;1", "year": 2026, "sem": "1", "label": "Acad Yr 2026 Semester 1"},
  "fetched_at": "2026-09-26T05:14:49+00:00",
  "errors": [],                       // 抓取失败的专业/年级
  "courses": {                        // 每门课只存一份
    "SC1005": {
      "code": "SC1005", "title": "DIGITAL LOGIC", "au": 3.0,
      "description": "This course aims to ...",
      "attributes": {"Mutually exclusive with": "CE1005, ...", "Prerequisite": "..."},
      "indexes": [                    // 所有专业页面中出现过的 index 的并集
        {"index": "10081", "sessions": [
          {"type": "LEC/STUDIO", "group": "LE1", "day": "MON", "time": "0830-0920",
           "venue": "LT1A", "remark": ""}
        ]}
      ]
    }
  },
  "programmes": [                     // 网站下拉框里的每个专业/年级都会列出
    {"value": "CSC;;1;F", "label": "Computer Science Year 1", "content_value": "CSC;;1;F",
     "status": "ok",                  // ok | empty（网站上本学期无排课）| error（抓取失败）
     "courses": [
       {"code": "SC1005", "is_ue": false, "is_bde": true, "is_self_paced": false, "is_ge_pe": false,
        "remark": "...",              // 可选：该专业页面上的 Remark
        "indexes": ["10081", "..."]}  // 可选：该专业页面上显示的 index；不写表示全部
     ]},
    {"value": "ACBS;RMI;2;F", "label": "Accountancy And Business (RMI) Year 2",
     "content_value": "ACBS;RMI;2;F", "status": "empty", "courses": []}
  ]
}
```

说明：

- **专业/年级不会被删除**：没有排课或抓取失败的专业/年级也会保留，`courses` 为空列表，原因看 `status`。展示时可以照常列出这些专业名。
- **因专业而异的字段放在专业这一层**：UE/BDE/GE 标记、Remark 和可见的 index 都取决于学生所在的专业，所以存在 `programmes[].courses[]` 里。`courses` 里只存与专业无关的信息。
- **没有排课的课**：`indexes` 为空的课程只出现在课程内容页，本学期没有排课。
- **专业代码的格式**：`value` 的格式是 `专业;方向;年级;F/P`（F 为全日制，P 为非全日制）。辅修是 `MLOAD;…`，BDE/UE 是 `GLOAD;…`，GE 是 `GERP;…`。

### 在 Python 中读取

```python
from ntu_courses.snapshot import Archive

archive = Archive("data")
data = archive.load_semester(archive.latest(), "2026;1")   # 旧格式的快照会在读取时自动转换

prog = next(p for p in data["programmes"] if p["value"] == "CSC;;1;F")
for entry in prog["courses"]:
    course = data["courses"][entry["code"]]
    print(course["code"], course["title"], len(course["indexes"]))
```

也可以不经过快照，直接查询网站：

```python
from ntu_courses import NTUClient, Semester

client = NTUClient()
courses = client.courses(Semester(2026, "1"), "CSC;;1;F")   # 返回 list[Course]
```

## 网页界面

`web/` 是一个 React + TypeScript + Tailwind + shadcn/ui 应用（用 `web-artifacts-builder` skill 搭建）。可以选择学期（所有抓取过的学期都会出现，显示 NTU 网站上的学期名称）和专业（包括没有排课的专业），按课程号、课程名或描述搜索，打开一门课可以看到详细信息、全部 index，以及所选 index 的每周课表。

它读取的是静态 JSON 文件，没有后端。先导出每个已抓取学期的最新数据：

```bash
python -m ntu_courses export-web      # 生成 web/public/data/semesters.json 和各学期的 <编号>.json
```

然后在 Node 20+ 和 pnpm 环境下：

```bash
cd web
pnpm install
pnpm dev            # 开发服务器，支持热更新
pnpm run bundle     # 打包成单个文件：bundle.html（另有给 claude.ai 用的 dist/artifact.html）
```

`bundle.html` 包含整个应用，但不包含数据。部署时把它和存放导出 JSON 的 `data/` 文件夹放在一起，用任意静态文件服务器提供访问，例如：

```bash
mkdir -p site && cp web/bundle.html site/index.html && cp -r web/public/data site/
python -m http.server -d site 8000
```

每次抓取后重新运行一次 `export-web`；之前抓过的学期仍会保留在下拉框里。

### 部署到 GitHub Pages

```bash
scripts/deploy_pages.sh            # 导出数据、打包、提交到 gh-pages 并推送
scripts/deploy_pages.sh --dry-run  # 同上，但只在本地提交，不推送
```

脚本会先运行 `export-web` 和单文件打包，然后在一个临时的 git worktree 里把 `index.html` 和 `data/` 提交到 `gh-pages` 分支。`main` 分支和你的工作区都不会被改动，数据也仍然不会提交到 `main`。每次部署都是一个普通提交，网站的历史版本会保留在分支历史里。Pages 会在 `https://<owner>.github.io/<repo>/` 提供访问（首次需要在 **Settings → Pages → Deploy from a branch → gh-pages / root** 启用一次）。

日常更新流程：先 `python -m ntu_courses crawl`，再 `scripts/deploy_pages.sh`。

### 访问量统计

Pages 网站会把访问记录发送到 [GoatCounter](https://www.goatcounter.com)（站点 `rayneyael`，配置在 `web/src/lib/analytics.ts`）。只有在 `rayneyael.github.io` 上才会统计；本地开发、`bundle.html` 和 claude.ai 预览都不会加载统计脚本。在 GoatCounter 设置里打开 "Allow adding visitor counts on your website" 后，页面顶部会显示总访问量（数字最多有 4 小时缓存）。同一个人 8 小时内刷新或重复访问只算一次。

要排除你自己的访问，在每个常用的浏览器里打开一次 `https://rayneyael.github.io/NTU-Course-Explorer/#toggle-goatcounter`（再打开一次即恢复统计），或者在 Settings → Tracking → Ignore IPs 里填上你的 IP。

## 测试

```bash
pytest              # 离线测试：用 tests/fixtures 里保存的网页样本
pytest -m live      # 联网测试：请求真实网站
```

如果离线测试通过但联网测试失败，通常是网站改版、页面结构变了。这时用新页面替换 `tests/fixtures` 里的样本，再调整 `ntu_courses/parsers.py`。

## 代码结构

```
ntu_courses/
  models.py     数据结构：学期、专业、课程、index、上课时段
  parsers.py    HTML 解析（纯函数）
  client.py     HTTP 请求（重试、限速）、两个网站之间的专业代码对应、按课程号补全描述
  crawler.py    整个学期的抓取与去重，旧格式数据的转换
  snapshot.py   快照存档的读写
  export.py     为网页界面导出静态 JSON
  __main__.py   命令行
web/
  src/lib/data.ts        数据加载、专业分组、搜索、时间处理
  src/components/        专业选择器、课程列表、课程详情、每周课表
  scripts/bundle.sh      单文件打包
```
