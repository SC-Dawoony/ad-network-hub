# Ad Network Management Streamlit App

멀티 네트워크 광고 네트워크 관리 애플리케이션입니다. 여러 광고 네트워크를 하나의 인터페이스에서 관리할 수 있습니다.

## 기능

- 🌐 **멀티 네트워크 지원**: BigOAds, Fyber, InMobi 등 여러 네트워크 지원
- 📱 **앱 생성**: 네트워크별 동적 폼을 통한 앱 생성
- 🎯 **슬롯 생성**: 조건부 필드를 지원하는 슬롯 생성
- 📋 **목록 조회**: 앱 및 슬롯 목록 조회 및 내보내기
- 🔄 **세션 관리**: 네트워크별 데이터 캐싱 및 상태 관리

## 설치

1. 가상 환경 활성화:
```bash
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate  # Windows
```

2. 의존성 설치:
```bash
pip install -r requirements.txt
```

## 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501`로 접속하세요.

## 프로젝트 구조

```
my-streamlit-app/
├── app.py                      # 메인 앱 (Home - Network Hub)
├── pages/                       # Streamlit 페이지들
│   ├── 1_📱_Create_App.py      # 앱 생성 페이지
│   ├── 2_🎯_Create_Unit.py     # 슬롯 생성 페이지
│   └── 3_📋_View_Lists.py     # 목록 조회 페이지
├── network_configs/             # 네트워크별 설정
│   ├── __init__.py             # 네트워크 레지스트리
│   ├── base_config.py          # 기본 설정 인터페이스
│   └── bigoads_config.py       # BigOAds 설정
├── utils/                       # 유틸리티 모듈
│   ├── session_manager.py      # 세션 상태 관리
│   ├── ui_components.py        # 동적 폼 렌더링
│   ├── validators.py           # 검증 함수들
│   └── network_manager.py      # 네트워크 API 매니저
└── requirements.txt            # 의존성 목록
```

## 현재 지원 네트워크

- ✅ **BigOAds**: 앱 생성, 슬롯 생성, 목록 조회 지원
- 🚧 **Fyber, InMobi, IronSource**: Phase 2 예정
- 🚧 **Mintegral, Pangle, Liftoff**: Phase 3 예정

## 사용 방법

### 1. 네트워크 선택
사이드바에서 관리할 네트워크를 선택합니다.

### 2. 앱 생성
1. "Create App" 페이지로 이동
2. 네트워크별 필수 필드 입력
3. "Create App" 버튼 클릭

### 3. 슬롯 생성
1. "Create Unit" 페이지로 이동
2. 앱 선택
3. 슬롯 정보 입력 (Ad Type에 따라 조건부 필드 표시)
4. "Create Slot" 버튼 클릭

### 4. 목록 조회
1. "View Lists" 페이지로 이동
2. Apps 또는 Slots 선택
3. 데이터 확인 및 CSV/JSON 내보내기

## 확장성

새로운 네트워크를 추가하려면:

1. `network_configs/` 폴더에 새 설정 파일 생성
2. `NetworkConfig` 클래스 상속
3. `network_configs/__init__.py`의 레지스트리에 추가

자세한 내용은 `bigoads_streamlit_design.md`를 참조하세요.

## 참고

- 이 앱은 Phase 1 구현으로 BigOAds를 완전히 지원합니다
- 다른 네트워크는 Phase 2, 3에서 추가될 예정입니다
- API 연동은 `utils/network_manager.py`에서 관리됩니다

