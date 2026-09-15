# Optional helpers; dependencies are checked when the function is used.
kill_process() {
  if command -v procs &> /dev/null && command -v fzf &> /dev/null; then
    local pid=$(procs | fzf | awk 'NR>1 {print $1}')
    if [[ -n "$pid" ]]; then
      kill -${1:-15} "$pid"
    fi
  else
    echo "需要安装 procs 和 fzf"
  fi
}

sysinfo() {
  echo "🖥️  系统信息概览"
  echo "===================="
  
  # 基本系统信息
  echo "📊 系统基本信息:"
  uname -a
  echo
  
  # CPU和内存使用情况
  echo "⚡ CPU和内存使用:"
  if command -v btop &> /dev/null; then
    echo "💡 运行 'btop' 查看详细的系统监控"
  else
    top -l 1 | head -10
  fi
  echo
  
  # 磁盘使用情况
  echo "💾 磁盘使用情况:"
  if command -v duf &> /dev/null; then
    duf
  else
    df -h
  fi
  echo
  
  # 网络连接
  echo "🌐 网络连接:"
  netstat -an | grep ESTABLISHED | wc -l | awk '{print "活跃连接数: " $1}'
  echo
  
  # 运行时间和负载
  echo "⏰ 系统运行时间:"
  uptime
}

perf() {
  echo "🔍 快速性能诊断"
  echo "=================="
  
  # 高CPU进程
  echo "🔥 CPU使用率最高的5个进程:"
  if command -v procs &> /dev/null; then
    procs --sortd cpu | head -6
  else
    ps aux | sort -nrk 3,3 | head -6
  fi
  echo
  
  # 高内存进程
  echo "🧠 内存使用率最高的5个进程:"
  if command -v procs &> /dev/null; then
    procs --sortd memory | head -6
  else
    ps aux | sort -nrk 4,4 | head -6
  fi
  echo
  
  # 磁盘IO
  echo "💾 磁盘IO活动:"
  iostat -d 1 1 2>/dev/null || echo "iostat 不可用，请安装或检查磁盘活动"
}

netcheck() {
  local target="${1:-google.com}"
  
  echo "🌐 网络连接诊断: $target"
  echo "========================="
  
  # DNS解析
  echo "🔍 DNS解析:"
  if command -v dog &> /dev/null; then
    dog "$target" A
  else
    nslookup "$target"
  fi
  echo
  
  # Ping测试
  echo "📡 连通性测试:"
  if command -v gping &> /dev/null; then
    echo "💡 运行 'gping $target' 查看图形化延迟"
    ping -c 4 "$target"
  else
    ping -c 4 "$target"
  fi
  echo
  
  # 路由追踪
  echo "🛣️  路由追踪:"
  traceroute "$target" 2>/dev/null || echo "traceroute 不可用"
}

portscan() {
  local host="${1:-localhost}"
  local port_range="${2:-1-1000}"
  
  echo "🔍 端口扫描: $host (端口范围: $port_range)"
  
  if command -v nmap &> /dev/null; then
    nmap -p "$port_range" "$host"
  else
    echo "❌ 需要安装 nmap: brew install nmap"
    echo "💡 或使用简单的端口检查:"
    echo "nc -z $host 22 80 443 8080"
  fi
}

check_modern_tools() {
  echo "🔍 现代工具安装状态检查:"
  echo "===================="
  
  local tools=(
    "eza:文件列表"
    "bat:文件查看"
    "fd:文件查找" 
    "dust:磁盘使用"
    "duf:磁盘信息"
    "procs:进程列表"
    "btop:系统监控"
    "sd:文本替换"
    "delta:差异显示"
    "dog:DNS查询"
    "gping:网络延迟"
    "httpie:HTTP客户端"
    "yq:YAML处理"
    "jc:JSON转换"
    "just:任务运行"
    "hyperfine:基准测试"
    "croc:文件传输"
    "age:文件加密"
    "czkawka_cli:重复文件检测"
  )
  
  for tool_info in "${tools[@]}"; do
    local tool="${tool_info%%:*}"
    local desc="${tool_info##*:}"
    if command -v "$tool" &> /dev/null; then
      echo "✅ $tool - $desc"
    else
      echo "❌ $tool - $desc (未安装)"
    fi
  done
  
  echo "===================="
  echo "💡 安装缺失工具: brew install <tool_name>"
}
