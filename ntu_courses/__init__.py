"""Scraper for NTU undergraduate class schedules and course content."""
from .client import NTUClient, merge_courses
from .models import ClassIndex, ClassSession, Course, Programme, Semester

__all__ = ["NTUClient", "merge_courses", "ClassIndex", "ClassSession", "Course", "Programme", "Semester"]
