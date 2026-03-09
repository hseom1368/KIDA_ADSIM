# KIDA_ADSIM — Claude Code 프로젝트 컨텍스트

## 프로젝트 개요
한국군 방공체계 C2 아키텍처(선형 C2 vs Kill Web) 비교 M&S.
Mesa(ABM) + SimPy(DES) + NetworkX 기반 에이전트 시뮬레이션.

## 디렉터리 구조
```
modules/
  config.py    — 모든 파라미터 (센서, C2, 사수, 위협, 시나리오, 통신)
  agents.py    — Mesa 에이전트 4종 (Sensor, C2Node, Shooter, Threat)
  model.py     — 통합 시뮬레이션 엔진 (AirDefenseModel)
  network.py   — NetworkX 토폴로지 빌더 (선형/킬웹)
  comms.py     — SimPy 통신 채널 + 킬체인 프로세스
  metrics.py   — 10개 성능 지표 수집기
  threats.py   — 위협 생성기 (5개 시나리오)
notebook1~4    — Jupyter 노트북 (모델정의, 시나리오, 배치실험, 분석)
```

## 기술 스택
- Python 3.10+, SimPy 4.1, Mesa 3.0, NetworkX 3.0
- numpy, pandas, scipy, matplotlib, seaborn

## 코딩 규칙
- 주석·변수명: 한국어 주석 허용, 변수·함수명은 영문 snake_case
- config.py에 모든 상수 집중 관리 — 매직 넘버 금지
- 에이전트 간 통신은 반드시 SimPy yield를 통한 지연 모델링
- 거리 계산: 고도 반영 시 _slant_range() 사용 (구현 예정)
- 테스트: 변경 후 반드시 `python -m pytest tests/` 및 시나리오 1 스모크 테스트 실행

## 핵심 아키텍처 비교
| 항목 | 선형 C2 | Kill Web |
|------|---------|----------|
| S2S 시간 | ~309s | ~5s (63배 빠름) |
| 토폴로지 | 계층 체인 (MCRC SPOF) | 완전 메시 (분산) |
| 사수 선택 | 유형 우선 고정 | 최적 점수 기반 |

## 현재 버전: v0.2-dev
**상태**: 위협 비행 프로파일 현실화 작업 진행 중

## 현재 진행 중인 작업
### 위협 비행 프로파일 현실화 (plan.md 참조)
- **문제**: 위협의 고도·속도가 전 비행 구간 고정 → SRBM(50km)이 PAC-3(30km) 교전고도 초과
- **계획**: 4종 위협 모두에 단계별 비행 프로파일(부스트/순항/종말) 도입
- **파일**: config.py(파라미터), agents.py(ThreatAgent 엔진)
- **상세**: `/home/user/KIDA_ADSIM/plan.md` 참조

### 다음 세션에서 할 일
1. plan.md의 8단계 구현 계획에 따라 코드 수정 착수
   - 1단계: config.py에 flight_profile 파라미터 추가
   - 2단계: agents.py ThreatAgent에 비행 프로파일 엔진 구현
   - 3단계: 3D 경사거리(slant range) 반영
2. 변경 후 시나리오 1 실행하여 SRBM 교전 가능 여부 검증
3. Kill Web vs 선형 C2 성능 재비교

## 자주 쓰는 명령어
```bash
# 스모크 테스트 (시나리오 1, 두 아키텍처)
python -c "
from modules.model import AirDefenseModel
for arch in ['linear', 'killweb']:
    m = AirDefenseModel(architecture=arch, scenario='scenario_1_saturation', seed=42)
    r = m.run_full()
    print(f'{arch}: leaker={r[\"metrics\"][\"leaker_rate\"]:.1%}, '
          f's2s={r[\"metrics\"][\"avg_s2s_time\"]:.1f}s, '
          f'success={r[\"metrics\"][\"engagement_success_rate\"]:.1%}')
"

# 전체 테스트
python -m pytest tests/ -v
```

## 이력 관리 파일
- `README.md` — 프로젝트 목표, 개념, 아키텍처 청사진
- `CHANGELOG.md` — 버전별 업데이트 이력 + 발견된 문제 + 개선 계획
- `plan.md` — 현재 진행 중인 개선 작업의 상세 기술 계획
- `dev_blueprint.md` — 초기 개발 청사진 (참조용, 동결)
