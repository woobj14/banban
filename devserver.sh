#!/bin/bash
# 반반 개발 서버 관리 (Streamlit + ngrok, launchd 기반 자동 재시작)
# 사용법: ./devserver.sh [status|start|stop|restart|logs|url]
set -e
UID_N=$(id -u)
ST=com.banban.streamlit
NG=com.banban.ngrok
URL=https://steering-pumice-visiting.ngrok-free.dev

case "${1:-status}" in
  status)
    echo "── 서비스 상태 ──"
    for s in $ST $NG; do
      pid=$(launchctl print gui/$UID_N/$s 2>/dev/null | awk '/pid =/{print $3; exit}')
      if [ -n "$pid" ]; then echo "  $s: running (pid $pid)"; else echo "  $s: stopped"; fi
    done
    echo "── 헬스 ──"
    curl -s -o /dev/null -w "  로컬:  HTTP %{http_code}\n" http://localhost:8501/_stcore/health
    curl -s -o /dev/null -w "  공개:  HTTP %{http_code}\n" -H "ngrok-skip-browser-warning: 1" $URL/_stcore/health
    echo "  공개 URL: $URL"
    ;;
  start)
    launchctl bootstrap gui/$UID_N ~/Library/LaunchAgents/$ST.plist 2>/dev/null || true
    launchctl bootstrap gui/$UID_N ~/Library/LaunchAgents/$NG.plist 2>/dev/null || true
    echo "시작 요청 완료. 몇 초 후 ./devserver.sh status 로 확인."
    ;;
  stop)
    launchctl bootout gui/$UID_N/$ST 2>/dev/null || true
    launchctl bootout gui/$UID_N/$NG 2>/dev/null || true
    echo "중지 완료."
    ;;
  restart)
    pkill -f "streamlit run" 2>/dev/null || true
    pkill -f "ngrok http"    2>/dev/null || true
    echo "재시작(launchd가 자동으로 다시 띄움). 몇 초 후 status 확인."
    ;;
  logs)
    echo "── streamlit (tail) ──"; tail -n 20 /tmp/banban_streamlit.log 2>/dev/null
    echo "── ngrok (tail) ──";     tail -n 10 /tmp/banban_ngrok.log 2>/dev/null
    ;;
  url)
    echo "$URL"
    ;;
  *)
    echo "사용법: ./devserver.sh [status|start|stop|restart|logs|url]"
    ;;
esac
