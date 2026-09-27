# NTU Course Explorer

[English](README.md) | 中文

按学期和专业浏览 NTU 本科课程：课表、课程描述，以及每个 index 的每周课表。

**在线访问：https://rayneyael.github.io/NTU-Course-Explorer/**

## 功能

- 覆盖所有可查学期的全部专业、年级、辅修和选修类别
- 按课程号、课程名或描述搜索
- 课程详情：学分、先修要求、选课限制和课程描述
- 全部 index，并可查看每周课表
- 显示所选专业下的 BDE / UE / GE 标签

数据来自 NTU 公开的 [Class Schedule](https://wish.wis.ntu.edu.sg/webexe/owa/AUS_SCHEDULE.main) 和 [Content of Courses](https://wish.wis.ntu.edu.sg/webexe/owa/aus_subj_cont.main) 页面。

## 快速开始

需要 Python 3.10+、Node 20+ 和 pnpm。

```bash
pip install -r requirements.txt
python -m ntu_courses crawl          # 抓取最新学期（约 15 分钟）
python -m ntu_courses export-web     # 为网页准备数据

cd web && pnpm install && pnpm dev   # 打开终端里显示的本地地址
```

## 爬虫命令

| 命令 | 作用 |
|---|---|
| `python -m ntu_courses crawl` | 抓取最新学期 |
| `python -m ntu_courses crawl --sem 2025_2` | 抓取指定学期 |
| `python -m ntu_courses crawl --all` | 抓取全部学期 |
| `python -m ntu_courses export-web` | 为网页导出数据 |

`--sem` 可以写编号（如 `2026_1`），也可以写网站上的学期名称（如 `"Acad Yr 2026 Semester 1"`）。

## 项目结构

```
ntu_courses/   Python 爬虫和命令行
web/           React 网页
scripts/       维护脚本
```
