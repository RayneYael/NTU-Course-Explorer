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
  __main__.py   命令行
```
