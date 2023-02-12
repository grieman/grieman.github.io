@echo off
>C:\Users\Graeham\Documents\GITHUB_PROJECTS\grieman.github.io\update.log (
  C:\Users\Graeham\AppData\Local\Programs\Python\Python310\python.exe "C:\Users\Graeham\Documents\GITHUB_PROJECTS\grieman.github.io\site_resources\weekly_update.py"
)
git add .
git commit -am "auto update: %date%"
git push public main