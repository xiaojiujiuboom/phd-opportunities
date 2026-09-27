#!/bin/zsh
cd "$(dirname "$0")" || exit 1
if [[ ! -x .venv/bin/python ]]; then
  echo "请先创建 .venv 并安装 scraper/requirements.txt 中的依赖。"
  exit 1
fi
.venv/bin/python -u scraper/fetch.py
result=$?
if [[ $result -eq 0 ]]; then
  .venv/bin/python scraper/stats.py
fi
python3 scraper/bundle.py
echo "抓取退出码: $result。来源结果见 data/collection-report.json。"
read "?按回车结束。"
