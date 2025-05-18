# domestic_stock_mvp

# Create a roadmap markdown file with the comprehensive project plan inspired by Perplexity's guide.

roadmap_content = """
# 🧭 국내 주식 분석 SaaS MVP 실행 로드맵

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

---

## 6. 📢 유저 피드백 전략

- Threads 등 SNS에 MVP 데모 배포
- 사용 영상/스크린샷 공유, 종목 추천 콘텐츠 제작
- 피드백 설문, 버그 제보 이벤트
- A/B 테스트 (해석 문구 순서 등)
- 핵심 지표: DAU, 세션 시간, 재방문률 등 모니터링

---

## 7. 🚀 확장 및 고도화 로드맵

- 실시간 데이터: 키움 API, 해외 API 연동
- 프리미엄 기능: PDF 리포트, 알림, 구독 결제 (Stripe)
- AI 해석 고도화: GPT 활용, 감정 분석 추가
- DB 확장: PostgreSQL, 사용자별 데이터 분리

---

## 8. ⚖️ 법적/운영 리스크 관리

- 화면마다 투자 책임 고지
- 금융감독원 신고제 확인
- 비공식 API는 남용 금지

---

## 9. ⏱ 실행 플로우 요약

1. 데이터 수집 → 테스트
2. 기술/재무 분석 기능 구현
3. AI 해석 문장 생성
4. 캐시/에러처리 등 안정성 확보
5. MVP 배포 → 피드백 수집
6. 개선 후 확장 단계 진입

---

## 💡 실행 팁

- “완벽”보다 “빠른 피드백”
- 한 번에 한 기능만, 작게 테스트
- 데이터 차단 시 대비 루트 항상 확보
- 유저가 원하는 인사이트에 집중
"""

file_path = "/mnt/data/README_roadmap.md"
with open(file_path, "w", encoding="utf-8") as f:
    f.write(roadmap_content)

file_path
