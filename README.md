# domestic_stock_mvp

# Create a roadmap markdown file with the comprehensive project plan inspired by Perplexity's guide.

## 1. 🎯 프로젝트 목표와 방향성

- **목표**: AI 기반 전략 해석과 개인화 기능을 갖춘 국내 주식 분석 도구(MVP) 개발
- **우선순위**:
  - 빠른 MVP 완성
  - 실제 사용자 반응(Threads 등) 테스트
  - 데이터 신뢰성과 서비스 안정성 확보

---

## 2. 📊 데이터 수집 및 안정화 전략

### 2-1. 공식 API 우선 활용
- **OpenDART**: 재무제표, 공시 등 기업의 공식 재무 데이터 확보
- **KRX**: 시세, 업종, 거래량 등 구조적 데이터

> ✅ 장점: 신뢰성, 무료, 법적 안정성  
> ❌ 단점: 실시간/초단위 트레이딩은 어려움

### 2-2. 보조 소스
- **네이버 금융 크롤링**: 실시간에 가까운 시세 확보 (차단 리스크 존재)
- **키움증권 모의투자 API**: 실시간 체결 데이터 (무료, 실전과 동일하진 않음)

### 2-3. 백업 및 차단 대응 전략
- 1차: 공식 API  
- 2차: 크롤링 기반  
- 3차: CSV 샘플 데이터  
- 캐시 / 재시도 / 에러 핸들링 포함

---

## 3. 🔧 MVP 핵심 기능 설계

- **기술적 분석**: RSI, MACD, VWAP, 볼린저밴드, 피보나치
- **재무제표 분석**: OpenDART 기반 재무비율 요약
- **AI 해석**: 시나리오 기반 전략 멘트 (템플릿 기반 → LLM 확장 가능)
- **시각화**: Plotly (재무), Highcharts (캔들)
- **사용자 기록**: SQLite, Firebase Auth 기반 로그인 준비

---

## 4. 🛠 개발 및 운영 환경

| 항목 | 기술 |
|------|------|
| 앱 프레임워크 | Streamlit |
| 분석 언어 | Python (pandas, numpy 등) |
| DB | SQLite (→ PostgreSQL 확장 가능) |
| 인증 | Firebase Authentication |
| 배포 | Streamlit Cloud, Supabase 등 무료 티어

---

## 5. 🧱 안정성 확보 및 크롤링 차단 방지 팁

- API 호출 최소화 → TTL 캐시 사용
- 크롤링은 User-Agent 변경 + 호출 간격 랜덤화
- 에러 시 대체 소스 또는 CSV 사용
- 사용자에게 “조회 실패” 안내 메시지 제공

"""

file_path = "/mnt/data/README_roadmap.md"
with open(file_path, "w", encoding="utf-8") as f:
    f.write(roadmap_content)

file_path
