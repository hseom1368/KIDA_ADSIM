# v0.6.x Cesium 3D 시각화 통합 계획 + v0.7 Monte Carlo 계획

> 작성일: 2026-03-24 (v0.5.1 기준)
> 기반: v0.5.1 (146개 테스트 PASS) + cesium_integration_plan.md

---

## 버전 로드맵

| 버전 | 이름 | 핵심 산출물 | Task 수 |
|------|------|-----------|---------|
| **v0.6.1** | CZML Exporter 고도화 | `exporters.py` v2 + 스키마 검증 | 6 |
| **v0.6.2** | CesiumJS 통합 뷰어 기반 | `cesium-viewer/` 프레임워크 | 4 |
| **v0.6.3** | 3D 센서 볼륨 & 교전 시각화 | 레이더 볼륨, 요격 궤적, 폭발 | 4 |
| **v0.6.4** | 성능 최적화 & HUD | Primitive API, Military HUD | 3 |
| **v0.6.5** | 통합 검증 & 문서화 | E2E 테스트, 자동화, 문서 | 3 |
| **v0.7** | Monte Carlo 통계 분석 | (아래 별도 섹션) | 6 |

**실행 순서**: v0.6.1 → v0.6.2 → v0.6.3 → v0.6.4 → v0.6.5 → v0.7
**핵심 불변 조건**: 시뮬레이션 로직(model.py, agents.py) 변경 금지. exporters.py + 프론트엔드만 수정.
**상세 Spec**: `cesium_integration_plan.md` 참조 (정규 스키마, Acceptance Criteria 등)

---

## v0.6.1 — CZML Exporter 고도화 (P1)

**범위**: Python 백엔드만 변경
**세션**: 1~2회 (T0~T3 / T4~T5)

| Task | 내용 | 변경 파일 |
|------|------|----------|
| P1-T0 | 스키마 준수 검증 테스트 (TDD 진입점) | `tests/test_schema_compliance.py` 신규 |
| P1-T1 | 위협 궤적 보간 (LAGRANGE/LINEAR) | `modules/exporters.py` |
| P1-T2 | 교전 이벤트 CZML 패킷 | `modules/exporters.py` |
| P1-T3 | C2 토폴로지 CZML (polyline) | `modules/exporters.py` |
| P1-T4 | `CesiumConfigExporter` (viewer_config.json) | `modules/exporters.py` |
| P1-T5 | 통합 테스트 + CZML 출력 검증 | `tests/test_exporters.py` 확장 |

**완료 기준**: 14개 CZML+JSON 내보내기 성공, 기존 146+신규 ~10개 테스트 PASS

---

## v0.6.2 — CesiumJS 통합 뷰어 기반 (P2)

**범위**: 프론트엔드 신규 생성, Python 변경 없음
**세션**: 1~2회 (T1+T2 / T3+T4)
**선행**: v0.6.1 완료

| Task | 내용 | 생성 파일 |
|------|------|----------|
| P2-T1 | 프로젝트 구조 + 기본 뷰어 | `cesium-viewer/index.html`, `js/app.js` |
| P2-T2 | CZML 로더 + 시간 컨트롤 | `js/czml-loader.js` |
| P2-T3 | 아키텍처 비교 모드 (토글/Split) | `js/app.js` 확장 |
| P2-T4 | 시나리오 선택 UI | `index.html`, `js/app.js` |

**완료 기준**: localhost에서 뷰어 → CZML 로드 → 위협 궤적 3D + 시간 제어 + 비교 모드

---

## v0.6.3 — 3D 센서 볼륨 & 교전 시각화 (P3)

**범위**: 프론트엔드 JS 모듈, Python 변경 없음
**세션**: **2회** — 세션1: T1(레이더)+T2(요격) / 세션2: T3(폭발)+T4(토폴로지)
**선행**: v0.6.2 완료

| Task | 내용 | 생성 파일 |
|------|------|----------|
| P3-T1 | 3D 구면 부채꼴 레이더 볼륨 | `js/radar-volumes.js` |
| P3-T2 | 요격 미사일 궤적 시각화 | `js/engagement-viz.js` |
| P3-T3 | ParticleSystem 폭발 이펙트 | `js/engagement-viz.js` 확장 |
| P3-T4 | C2 토폴로지 3D 렌더링 | `js/topology-viz.js` |

**완료 기준**: 3D 레이더 볼륨 + 요격 궤적 + 폭발/실패 이펙트 + 토폴로지 연결선

---

## v0.6.4 — 성능 최적화 & Military HUD (P4)

**범위**: 프론트엔드 최적화 + HUD UI
**세션**: 1회
**선행**: v0.6.3 완료

| Task | 내용 | 파일 |
|------|------|------|
| P4-T1 | Primitive API 마이그레이션 | `js/performance.js` |
| P4-T2 | Military HUD 패널 | `js/hud-panel.js`, `css/hud.css` |
| P4-T3 | requestRenderMode 성능 제어 | `js/app.js` |

**완료 기준**: 50+ 위협 60fps, HUD 실시간 갱신, 일시정지 시 CPU 절감

---

## v0.6.5 — 통합 검증 & 문서화 (P5)

**범위**: 테스트, 자동화, 문서
**세션**: 1회
**선행**: v0.6.4 완료

| Task | 내용 | 파일 |
|------|------|------|
| P5-T1 | E2E 통합 테스트 | `tests/test_e2e_cesium.py` |
| P5-T2 | 자동화 스크립트 | `run_cesium.py` |
| P5-T3 | 문서 갱신 | `CHANGELOG.md`, `CLAUDE.md`, `README.md` |

**완료 기준**: `python run_cesium.py --serve` 단일 명령, ~181개 테스트 PASS, SSOT 준수

---

## v0.7 — Monte Carlo 통계 분석 (기존 v0.6 계획 이동)

> 아래 내용은 기존 v0.6 계획을 v0.7로 이동한 것임

### 작업 개요

| # | 작업 | 파일 | 난이도 |
|---|------|------|--------|
| 1 | Monte Carlo 배치 실험 프레임워크 | model.py, notebook3 | **높음** |
| 2 | 통계 분석 모듈 | modules/stats.py (신규) | **높음** |
| 3 | 최종 분석 보고서 | notebook6 (신규) | 중간 |
| 4 | 인터랙티브 시각화 (선택) | modules/dashboard.py | 낮음 |
| 5 | 테스트 추가 | tests/ | 중간 |
| 6 | 문서 업데이트 | CHANGELOG, CLAUDE.md, README | 낮음 |

**실행 순서**: 1 → 2 → 3 → 5 → 6 (작업 4는 선택)
**상세 설계**: 기존 plan.md v0.6 내용과 동일 (Monte Carlo 4,200회, stats.py, 보고서)

---

## v0.5.1 완료 기록 (온톨로지 리팩토링)

> 작업 완료일: 2026-03-23
> 테스트: 146개 전부 PASS (13개 파일)

### 완료된 작업 (v0.5.1)
1. Pydantic 도메인 온톨로지 ✅ — `ontology.py` (SensorType/C2Type/ShooterType/ThreatType + 능력 모델)
2. 엔티티 레지스트리 ✅ — `registry.py` (config→온톨로지 변환, Pk 우선순위, 토폴로지 역조회)
3. Strategy 패턴 ✅ — `strategies.py` (LinearC2Strategy/KillWebStrategy, 11개 if/else 분기 제거)
4. model.py 리팩토링 ✅ — Registry→Strategy→Agent→Topology→Comm 초기화 순서
5. comms.py 개선 ✅ — architecture 문자열 → redundancy_factor 수치 주입
6. CZML 내보내기 ✅ — `exporters.py` (Cesium 3D 시각화 변환)
7. 테스트 확장 ✅ — 86개 → 146개 (신규 60개, 4개 테스트 파일 추가)

### 성능 검증 (v0.5.1 = v0.5 동일)
- 시나리오 1 seed=42 기준선 완전 일치 (순수 구조 리팩토링, 성능 변화 0%)

---

## v0.5 완료 기록

> 작업 완료일: 2026-03-12
> 테스트: 86개 전부 PASS (9개 파일)

### 완료된 작업 (v0.5)
1. COP 품질 차별화 ✅ — 센서 융합 √N 오차, 아군 상태 공유, 교전 계획 공유
2. 적응형 교전 정책 ✅ — 탄약 30%/10% 임계치 기반 자동 전환
3. 통신 네트워크 동적 열화 ✅ — 링크별 차등 재밍, 메시 다중경로 완화
4. 2D 전술 시각화 모듈 ✅ — TacticalVisualizer (렌더/애니메이션/비교/타임라인)
5. 시각화 노트북 ✅ — notebook5 (전술 애니메이션 + 아키텍처 비교)
6. 테스트 확장 ✅ — 57개 → 86개 (COP 11개, 적응형 13개, 시각화 5개)
7. 문서 업데이트 ✅ — CHANGELOG, CLAUDE.md, README 갱신

### 성능 기준선 (v0.5, seed=42)
- Kill Web 전 시나리오 평균 누출률: **20.2%** (vs Linear 32.3%)
- Kill Web S2S: **5~25초** (vs Linear 114~589초)
- Kill Web S3 EW Heavy 누출률: **21.1%** (vs Linear 39.5%)

---

## v0.4 완료 기록

> 작업 완료일: 2026-03-11
> 테스트: 57개 전부 PASS

### 완료된 작업 (v0.4)
1. jamming_level 오버라이드 정리 ✅
2. comms.py 죽은 코드 삭제 ✅
3. config.py 죽은 설정 삭제 ✅
4. 다중 교전 모델링 ✅ (SRBM=3, CM=2)
5. 메트릭 확장 12개 ✅
6. 테스트 확장 57개 ✅
7. 노트북 업데이트 ✅
