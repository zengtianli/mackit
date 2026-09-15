# Optional helpers; dependencies are checked when the function is used.
sdr() { sd "$1" "$2" "${3:-.}"; }  # sd replace function

yaml2json() { yq -o=json '.' "$1"; }

json2yaml() { yq -P '.' "$1"; }

psj() { ps aux | jc --ps; }

dfj() { df -h | jc --df; }

lsj() { ls -la | jc --ls; }

encrypt() { age -r "$1" -o "$2.age" "$2"; }

decrypt() { age -d -i ~/.config/age/key.txt -o "${1%.age}" "$1"; }

project_init() {
  local project_name="$1"
  local project_type="${2:-general}"
  
  if [[ -z "$project_name" ]]; then
    echo "用法: project_init <项目名> [类型]"
    echo "支持的类型: node, python, rust, go, general"
    return 1
  fi
  
  echo "🚀 初始化项目: $project_name (类型: $project_type)"
  
  # 创建项目目录
  mkdir -p "$project_name"
  cd "$project_name"
  
  # 初始化Git
  git init
  echo "# $project_name" > README.md
  
  # 根据项目类型创建基础文件
  case $project_type in
    node)
      npm init -y
      echo "node_modules/\n.env\n*.log" > .gitignore
      if command -v just &> /dev/null; then
        cat > justfile <<'EOF'
# 安装依赖
install:
  npm install

# 开发模式
dev:
  npm run dev

# 构建
build:
  npm run build

# 测试
test:
  npm test

# 清理
clean:
  rm -rf node_modules dist
EOF
      fi
      ;;
    python)
      echo "*.pyc\n__pycache__/\n.env\nvenv/\n.venv/" > .gitignore
      echo "# -*- coding: utf-8 -*-\n\ndef main():\n    print('Hello, $project_name!')\n\nif __name__ == '__main__':\n    main()" > main.py
      if command -v just &> /dev/null; then
        cat > justfile <<'EOF'
# 创建虚拟环境
venv:
  python3 -m venv venv
  source venv/bin/activate && pip install --upgrade pip

# 安装依赖
install:
  pip install -r requirements.txt

# 运行
run:
  python main.py

# 测试
test:
  pytest

# 清理
clean:
  rm -rf __pycache__ .pytest_cache *.pyc
EOF
      fi
      touch requirements.txt
      ;;
    *)
      echo "*.tmp\n*.log\n.env" > .gitignore
      ;;
  esac
  
  # 提交初始版本
  git add .
  git commit -m "Initial commit"
  
  echo "✅ 项目 '$project_name' 初始化完成!"
  echo "📁 位置: $(pwd)"
  lsmart
}

serve() {
  local port="${1:-8000}"
  local dir="${2:-.}"
  
  echo "🌐 启动HTTP服务器..."
  echo "📁 目录: $(realpath $dir)"
  echo "🔗 地址: http://localhost:$port"
  echo "⏹️  按 Ctrl+C 停止服务器"
  echo
  
  if command -v python3 &> /dev/null; then
    cd "$dir" && python3 -m http.server "$port"
  elif command -v python &> /dev/null; then
    cd "$dir" && python -m SimpleHTTPServer "$port"
  else
    echo "❌ 需要Python来运行HTTP服务器"
    return 1
  fi
}

jf() {
  local file="$1"
  local query="$2"
  
  if [[ -z "$file" ]]; then
    echo "用法: jf <文件或URL> [jq查询]"
    echo "示例: jf data.json '.users[] | select(.active)'"
    return 1
  fi
  
  if ! command -v jq &> /dev/null; then
    echo "❌ 需要安装 jq: brew install jq"
    return 1
  fi
  
  # 支持URL和文件
  if [[ "$file" =~ ^https?:// ]]; then
    if command -v http &> /dev/null; then
      if [[ -n "$query" ]]; then
        http "$file" | jq "$query"
      else
        http "$file" | jq '.'
      fi
    else
      curl -s "$file" | jq "${query:-.}"
    fi
  else
    if [[ -n "$query" ]]; then
      jq "$query" "$file"
    else
      jq '.' "$file"
    fi
  fi | bat -l json
}

csv() {
  local file="$1"
  local action="${2:-view}"
  
  if [[ -z "$file" ]]; then
    echo "用法: csv <文件> [action]"
    echo "Actions: view, head, stats, query"
    return 1
  fi
  
  case $action in
    view)
      if command -v visidata &> /dev/null; then
        visidata "$file"
      elif command -v mlr &> /dev/null; then
        mlr --csv cat "$file" | head -20
      else
        head -20 "$file" | column -t -s ','
      fi
      ;;
    head)
      head -10 "$file"
      ;;
    stats)
      if command -v mlr &> /dev/null; then
        mlr --csv stats1 -a count,mean,min,max -f all "$file"
      else
        echo "❌ 需要安装 miller: brew install miller"
      fi
      ;;
    query)
      echo "请输入Miller查询表达式:"
      read -r query
      mlr --csv "$query" "$file"
      ;;
  esac
}
