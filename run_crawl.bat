@echo off
cd /d C:\workspace\simple_crawler
python daily_crawl.py >> crawl_log.txt 2>&1
