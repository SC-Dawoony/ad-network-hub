# Google OAuth 로그인 설정

## .env / Streamlit Secrets 설정

### 필요한 환경 변수

| 변수명 | 필수 | 설명 | 예시 |
|--------|------|------|------|
| `GOOGLE_CLIENT_ID` | ✅ | Google OAuth 클라이언트 ID | `xxx.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | ✅ | Google OAuth 클라이언트 시크릿 | `GOCSPX-xxx` |
| `GOOGLE_REDIRECT_URI` | ❌ | OAuth 리다이렉트 URI (기본: `http://localhost:8501/`) | `http://localhost:8501/` |

### .env (로컬)

프로젝트 루트에 `.env` 파일을 만들고:

```
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8501/login
```

### Streamlit Secrets (배포)

Streamlit Cloud 배포 시:

1. 앱 설정 → **Secrets** 탭
2. 아래 형식으로 추가:

```toml
GOOGLE_CLIENT_ID = "your_client_id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "your_client_secret"
GOOGLE_REDIRECT_URI = "https://your-app.streamlit.app/login"
```

## OAuth 클라이언트 ID 발급

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 프로젝트 생성 또는 선택
3. **APIs & Services** → **Credentials**
4. **Create Credentials** → **OAuth client ID**
5. Application type: **Web application**
6. **Authorized redirect URIs** 추가:
   - 로컬: `http://localhost:8501/login`
   - Streamlit Cloud: `https://<your-app>.streamlit.app/login`
   - (Login 페이지 URL: `0_Login.py` → `/login`)
7. **Client ID**, **Client Secret** 복사

## 로컬 vs 프로덕션

| 환경 | 인증 | 설정 |
|------|------|------|
| **로컬 (localhost)** | 비활성화 | `ENABLE_AUTH` 설정 안 함 (기본값) |
| **프로덕션** | 활성화 | `ENABLE_AUTH=true` 추가 |

Streamlit Cloud 배포 시 **Secrets**에 추가:
```toml
ENABLE_AUTH = "true"
GOOGLE_CLIENT_ID = "..."
GOOGLE_CLIENT_SECRET = "..."
GOOGLE_REDIRECT_URI = "https://your-app.streamlit.app/login"
```

로컬에서는 `ENABLE_AUTH`를 설정하지 않으면 로그인 없이 바로 앱에 접근할 수 있습니다.

## 로그인 유지

- Refresh token이 `auth_tokens/tokens.json`에 저장됩니다
- 서버 재시작, 브라우저 재접속 시에도 자동으로 로그인 유지
- `auth_tokens/` 폴더는 `.gitignore`에 포함되어 Git에 커밋되지 않습니다
