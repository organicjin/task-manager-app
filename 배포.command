#!/bin/bash
# ============================================
# 더블클릭하면 GitHub에 올리고
# 고정 주소 배포를 안내해줍니다!
# ============================================

cd "$(dirname "$0")"

echo ""
echo "========================================="
echo "  🚀 고정 주소 배포 시작!"
echo "========================================="
echo ""

# 1. gh (GitHub CLI) 확인 & 설치
if ! command -v gh &> /dev/null; then
    echo "📦 GitHub 도구 설치 중... (최초 1회)"

    # Homebrew 확인
    if ! command -v brew &> /dev/null; then
        echo "📦 Homebrew도 같이 설치 중..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        if [ -f "/opt/homebrew/bin/brew" ]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
    fi

    if [ -f "/opt/homebrew/bin/brew" ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi

    brew install gh
    echo "✅ GitHub 도구 설치 완료"
fi

if [ -f "/opt/homebrew/bin/brew" ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi

# 2. GitHub 로그인 확인
if ! gh auth status &> /dev/null; then
    echo ""
    echo "🔐 GitHub 로그인이 필요합니다."
    echo "   브라우저가 열리면 로그인해주세요."
    echo ""
    gh auth login --web --git-protocol https
    echo ""
fi

echo "✅ GitHub 로그인 확인 완료"
echo ""

# 3. Git 저장소 초기화
if [ ! -d ".git" ]; then
    git init
    echo "✅ Git 저장소 생성"
fi

# 4. GitHub 저장소 생성 & 업로드
REPO_NAME="task-manager-app"
GH_USER=$(gh api user --jq '.login' 2>/dev/null)

if ! gh repo view "$GH_USER/$REPO_NAME" &> /dev/null; then
    echo "📦 GitHub 저장소 생성 중..."
    gh repo create "$REPO_NAME" --private --source=. --remote=origin
    echo "✅ GitHub 저장소 생성 완료"
else
    echo "✅ GitHub 저장소가 이미 존재합니다"
    # origin이 없으면 추가
    if ! git remote get-url origin &> /dev/null; then
        git remote add origin "https://github.com/$GH_USER/$REPO_NAME.git"
    fi
fi

# 5. 코드 업로드
echo "📤 코드 업로드 중..."
git add app.py database.py models.py ai_classifier.py requirements.txt .gitignore .streamlit/config.toml .env.example
git commit -m "프로젝트 관리 에이전트 배포" 2>/dev/null || echo "(변경사항 없음)"
git branch -M main
git push -u origin main 2>/dev/null || git push --force origin main
echo "✅ 코드 업로드 완료!"

# 6. 배포 안내
echo ""
echo ""
echo "========================================="
echo ""
echo "  ✅ GitHub 업로드 완료!"
echo ""
echo "  이제 마지막 한 단계만 남았어요."
echo "  아래 순서대로 따라해주세요:"
echo ""
echo "========================================="
echo ""
echo "  📌 STEP 1. 아래 주소를 브라우저에서 열기"
echo ""
echo "     https://share.streamlit.io"
echo ""
echo "  📌 STEP 2. 'Continue with GitHub' 클릭"
echo ""
echo "  📌 STEP 3. 배포 설정"
echo "     - Repository: $GH_USER/$REPO_NAME"
echo "     - Branch: main"
echo "     - Main file path: app.py"
echo ""
echo "  📌 STEP 4. 'Advanced settings' 클릭 후"
echo "     Secrets에 아래 내용 입력:"
echo ""
echo "     APP_PASSWORD = \"원하는비밀번호\""
echo "     OPENAI_API_KEY = \"sk-여기에API키\""
echo ""
echo "     (API 키 없으면 APP_PASSWORD만 입력)"
echo ""
echo "  📌 STEP 5. 'Deploy!' 클릭"
echo ""
echo "  🎉 끝! 고정 주소가 생깁니다:"
echo "     https://$REPO_NAME-$GH_USER.streamlit.app"
echo ""
echo "========================================="
echo ""
echo "  지금 바로 브라우저를 열어드릴까요?"
echo ""
read -p "  열기 (y/n): " OPEN_BROWSER
if [ "$OPEN_BROWSER" = "y" ] || [ "$OPEN_BROWSER" = "Y" ] || [ -z "$OPEN_BROWSER" ]; then
    open "https://share.streamlit.io"
fi

echo ""
read -p "아무 키나 누르면 종료됩니다..."
