#!/bin/bash
# ============================================
# 더블클릭하면 자동으로 앱이 실행됩니다!
# 외부에서도 모바일 접속 가능!
# ============================================

cd "$(dirname "$0")"

# 종료 시 백그라운드 프로세스 정리
cleanup() {
    echo ""
    echo "앱을 종료합니다..."
    kill $TUNNEL_PID 2>/dev/null
    kill $STREAMLIT_PID 2>/dev/null
    exit 0
}
trap cleanup EXIT INT TERM

echo ""
echo "========================================="
echo "  📋 프로젝트 관리 에이전트 설치 & 실행"
echo "========================================="
echo ""

# 1. Python 확인
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3가 설치되어 있지 않습니다."
    echo ""
    echo "👉 아래 사이트에서 Python을 다운로드해주세요:"
    echo "   https://www.python.org/downloads/"
    echo ""
    echo "설치 후 이 파일을 다시 더블클릭하세요."
    echo ""
    read -p "아무 키나 누르면 종료됩니다..."
    exit 1
fi

echo "✅ Python3 확인 완료"

# 2. Homebrew 확인 & 설치
if ! command -v brew &> /dev/null; then
    echo "📦 Homebrew 설치 중... (최초 1회, 1~2분 소요)"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Apple Silicon Mac 경로 설정
    if [ -f "/opt/homebrew/bin/brew" ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
    echo "✅ Homebrew 설치 완료"
fi

# Apple Silicon Mac brew 경로 보장
if [ -f "/opt/homebrew/bin/brew" ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi

# 3. cloudflared 확인 & 설치 (외부 접속용)
if ! command -v cloudflared &> /dev/null; then
    echo "📦 외부 접속 도구 설치 중... (최초 1회)"
    brew install cloudflared
    echo "✅ 외부 접속 도구 설치 완료"
fi

# 4. 가상환경 생성 (최초 1회)
if [ ! -d "venv" ]; then
    echo "📦 가상환경 생성 중... (최초 1회만)"
    python3 -m venv venv
    echo "✅ 가상환경 생성 완료"
fi

# 5. 가상환경 활성화
source venv/bin/activate

# 6. 패키지 설치 (최초 1회)
if [ ! -f "venv/.installed" ]; then
    echo "📦 필요한 패키지 설치 중... (최초 1회만, 1~2분 소요)"
    pip install --quiet streamlit openai plotly python-dotenv
    touch venv/.installed
    echo "✅ 패키지 설치 완료"
fi

# 7. .env 파일 생성 (최초 1회)
if [ ! -f ".env" ]; then
    echo ""
    echo "========================================="
    echo "  🔐 초기 설정 (최초 1회만)"
    echo "========================================="
    echo ""

    # 비밀번호 설정
    echo "📌 앱 접속 비밀번호를 정해주세요."
    read -p "   비밀번호 입력: " APP_PW
    if [ -z "$APP_PW" ]; then
        APP_PW="1234"
        echo "   → 기본 비밀번호 '1234'로 설정됨"
    fi
    echo ""

    # OpenAI 키 설정
    echo "📌 OpenAI API 키를 입력해주세요."
    echo "   (없으면 그냥 엔터 → AI 자동분류 없이 수동 사용)"
    read -p "   API 키 입력: " API_KEY
    if [ -z "$API_KEY" ]; then
        API_KEY="sk-없음"
        echo "   → API 키 없이 진행 (수동 분류 모드)"
    fi

    echo "OPENAI_API_KEY=$API_KEY" > .env
    echo "APP_PASSWORD=$APP_PW" >> .env

    echo ""
    echo "✅ 설정 완료!"
fi

# 8. Streamlit 백그라운드 실행
echo ""
echo "🚀 앱 시작 중..."
streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true &
STREAMLIT_PID=$!
sleep 4

# 9. 외부 접속 터널 시작 + URL 추출
TUNNEL_LOG=$(mktemp)
cloudflared tunnel --url http://localhost:8501 > "$TUNNEL_LOG" 2>&1 &
TUNNEL_PID=$!

# URL이 나올 때까지 대기 (최대 15초)
echo "🌐 외부 접속 주소 생성 중..."
TUNNEL_URL=""
for i in $(seq 1 30); do
    TUNNEL_URL=$(grep -o 'https://[a-z0-9\-]*\.trycloudflare\.com' "$TUNNEL_LOG" 2>/dev/null | head -1)
    if [ -n "$TUNNEL_URL" ]; then
        break
    fi
    sleep 0.5
done

# 10. 브라우저 자동 열기
open "http://localhost:8501" 2>/dev/null

# 11. 접속 정보 표시
echo ""
echo ""
echo "========================================="
echo ""
echo "  ✅ 앱이 실행되었습니다!"
echo ""
echo "========================================="
echo ""
echo "  💻 이 컴퓨터에서 접속:"
echo "     http://localhost:8501"
echo ""

if [ -n "$TUNNEL_URL" ]; then
    echo "  ✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨"
    echo ""
    echo "  📱 모바일 접속 주소 (어디서든!):"
    echo ""
    echo "     $TUNNEL_URL"
    echo ""
    echo "  ✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨"
    echo ""
    echo "  👆 이 주소를 핸드폰 브라우저에 입력하세요!"
else
    echo "  ⚠️  외부 접속 주소 생성 실패"
    echo "     (인터넷 연결을 확인해주세요)"
fi

echo ""
echo "  🔐 비밀번호는 .env 파일에서 변경 가능"
echo ""
echo "  ⛔ 종료하려면 이 창을 닫으세요"
echo ""
echo "========================================="
echo ""

# 12. 앱이 종료될 때까지 대기
wait $STREAMLIT_PID
