#!/bin/bash
# 프로젝트 관리 에이전트 실행 스크립트
# 사용법:
#   ./start.sh          → 로컬만 (같은 와이파이에서 접속 가능)
#   ./start.sh tunnel   → 외부 접속 (모바일 어디서든 접속 가능)

cd "$(dirname "$0")"

echo "========================================="
echo "  📋 프로젝트 관리 에이전트 시작"
echo "========================================="

# .env 파일 확인
if [ ! -f .env ]; then
    echo ""
    echo "⚠️  .env 파일이 없습니다. .env.example을 복사합니다."
    cp .env.example .env
    echo "📝 .env 파일을 열어 OPENAI_API_KEY와 APP_PASSWORD를 설정해주세요."
    echo ""
fi

# 로컬 IP 가져오기
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')

if [ "$1" = "tunnel" ]; then
    # cloudflared 터널 모드 (외부 접속)
    if ! command -v cloudflared &> /dev/null; then
        echo ""
        echo "❌ cloudflared가 설치되어 있지 않습니다."
        echo "   설치 방법: brew install cloudflared"
        echo ""
        exit 1
    fi

    echo ""
    echo "🌐 외부 접속 터널을 시작합니다..."
    echo "   (터널 URL이 표시되면 모바일에서 접속하세요)"
    echo ""

    # Streamlit을 백그라운드로 실행
    streamlit run app.py &
    STREAMLIT_PID=$!

    # 잠시 대기 후 터널 시작
    sleep 3
    echo ""
    echo "📱 아래 터널 URL을 모바일 브라우저에 입력하세요:"
    echo "-----------------------------------------"
    cloudflared tunnel --url http://localhost:8501

    # 종료 시 Streamlit도 정리
    kill $STREAMLIT_PID 2>/dev/null
else
    # 로컬 모드
    echo ""
    echo "📱 같은 와이파이에서 접속:"
    echo "   http://${LOCAL_IP}:8501"
    echo ""
    echo "💻 이 컴퓨터에서 접속:"
    echo "   http://localhost:8501"
    echo ""
    echo "🌐 외부에서도 접속하려면: ./start.sh tunnel"
    echo "========================================="
    echo ""

    streamlit run app.py
fi
