# Streamlit 앱 배포 가이드

## 방법 1: Streamlit Cloud (추천) ⭐

가장 간단하고 무료로 배포할 수 있는 방법입니다.

### 준비사항
1. GitHub 계정
2. Streamlit Cloud 계정 (https://share.streamlit.io)

### 배포 단계

#### 1. GitHub에 코드 업로드
```bash
# Git 초기화 (아직 안 했다면)
git init
git add .
git commit -m "Initial commit"

# GitHub에 새 repository 생성 후
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

#### 2. Streamlit Cloud에 배포
1. https://share.streamlit.io 접속
2. GitHub 계정으로 로그인
3. "New app" 클릭
4. Repository 선택
5. Main file path: `app.py` 입력
6. "Deploy!" 클릭

#### 3. 환경 변수 설정 (중요!)
`.env` 파일의 내용을 Streamlit Cloud Secrets에 추가해야 합니다:

1. Streamlit Cloud 앱 페이지에서 "☰" 메뉴 클릭
2. "Settings" → "Secrets" 선택
3. 아래 형식으로 환경 변수 추가:

```toml
[secrets]
# BigOAds
BIGOADS_DEVELOPER_ID = "your_developer_id"
BIGOADS_TOKEN = "your_token"

# IronSource
IRONSOURCE_SECRET_KEY = "your_secret_key"
IRONSOURCE_REFRESH_TOKEN = "your_refresh_token"
IRONSOURCE_BEARER_TOKEN = "your_bearer_token"

# Pangle
PANGLE_SECURITY_KEY = "your_security_key"
PANGLE_USER_ID = "your_user_id"
PANGLE_ROLE_ID = "your_role_id"

# Mintegral
MINTEGRAL_SKEY = "your_skey"
MINTEGRAL_SECRET = "your_secret"
```

#### 4. 코드 수정 필요
`.env` 파일 대신 Streamlit Secrets를 사용하도록 코드 수정:

`utils/network_manager.py`와 다른 파일에서:
```python
# 기존
import os
from dotenv import load_dotenv
load_dotenv(override=True)
token = os.getenv("BIGOADS_TOKEN")

# 변경 후 (Streamlit Cloud 호환)
import os
import streamlit as st
from dotenv import load_dotenv

# Streamlit Cloud에서는 secrets 사용, 로컬에서는 .env 사용
if hasattr(st, 'secrets') and 'BIGOADS_TOKEN' in st.secrets:
    token = st.secrets["BIGOADS_TOKEN"]
else:
    load_dotenv(override=True)
    token = os.getenv("BIGOADS_TOKEN")
```

---

## 방법 2: Heroku

### 준비사항
1. Heroku 계정
2. Heroku CLI 설치

### 배포 단계

#### 1. 필요한 파일 생성

**Procfile** 생성:
```
web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

**setup.sh** 생성:
```bash
mkdir -p ~/.streamlit/

echo "\
[server]\n\
headless = true\n\
port = $PORT\n\
enableCORS = false\n\
\n\
" > ~/.streamlit/config.toml
```

#### 2. Heroku에 배포
```bash
heroku login
heroku create your-app-name
heroku config:set BIGOADS_TOKEN=your_token
heroku config:set BIGOADS_DEVELOPER_ID=your_id
# ... 다른 환경 변수들도 설정
git push heroku main
```

---

## 방법 3: Docker + 클라우드 플랫폼

### Dockerfile 생성
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### 배포
- AWS ECS/Fargate
- Google Cloud Run
- Azure Container Instances
- DigitalOcean App Platform

---

## 보안 주의사항

⚠️ **중요**: `.env` 파일은 절대 GitHub에 커밋하지 마세요!
- `.gitignore`에 `.env`가 포함되어 있는지 확인
- 환경 변수는 배포 플랫폼의 Secrets/Config 기능 사용

---

## 빠른 시작 (Streamlit Cloud)

1. GitHub에 코드 푸시
2. Streamlit Cloud에서 "New app" 클릭
3. Repository 선택
4. Main file: `app.py`
5. Secrets에 환경 변수 추가
6. Deploy!

배포 후 URL이 생성되며, 코드를 푸시할 때마다 자동으로 재배포됩니다.

