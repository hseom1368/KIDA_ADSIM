# v0.5 상세 구현 계획

> 작성일: 2026-03-11
> 기반: v0.4 (57개 테스트 PASS, 다중 교전 모델링 완료, 12개 메트릭)

---

## 작업 개요

| # | 작업 | 파일 | 난이도 | 영향 범위 |
|---|------|------|--------|-----------|
| 1 | COP 품질 차별화 | agents.py, model.py, config.py | **높음** | 킬체인 로직 변경 |
| 2 | 적응형 교전 정책 | model.py, config.py | 중간 | 교전 로직 변경 |
| 3 | 통신 네트워크 동적 열화 | comms.py, model.py, config.py | 중간 | 통신 지연 변경 |
| 4 | 2D 전술 시각화 모듈 | modules/viz.py (신규) | **높음** | 신규 모듈 |
| 5 | 시각화 노트북 | notebook5 (신규) | 중간 | 노트북만 |
| 6 | 테스트 추가/수정 | tests/ | 중간 | 작업 1~3 검증 |
| 7 | 문서 업데이트 | CHANGELOG.md, CLAUDE.md, README.md | 낮음 | 문서만 |

**실행 순서**: 1 → 2 → 3 → 4 → 5 → 6 → 7 (의존성 순)

---

## 작업 1: COP 품질 차별화 (핵심 기능)

### 현재 상태
- 양쪽 아키텍처 모두 `air_picture = {threat_id: track_info}` 형태로 **위협 항적만** 공유
- Kill Web과 Linear C2의 COP 내용이 동일 (차이는 전달 속도뿐)
- `SensorAgent.track()`이 `tracking_position_error_std=0.5km` 가우시안 오차 적용

### 설계: 아키텍처별 COP 내용 차별화

#### Linear C2 COP (제한적 공유)
```
COP_linear = {
    threat_id: {
        "pos": (x, y),           # 위협 위치 (단일 센서 보고, 오차 큼)
        "speed": float,
        "altitude": float,
        "threat_type": str,
        "time": float,
    }
}
```
- **위협 정보만** 포함 — 아군 자산 상태, 교전 계획 정보 없음
- 단일 센서 보고 의존 → 위치 오차 그대로 (`σ = 0.5km`)
- C2 노드가 사수 가용성을 **직접 확인할 수 없음** → 고정 우선순위 할당 유지

#### Kill Web COP (완전 공유)
```
COP_killweb = {
    threat_id: {
        "pos": (x, y),           # 센서 융합 위치 (복수 센서, 오차 감소)
        "speed": float,
        "altitude": float,
        "threat_type": str,
        "time": float,
        # ── v0.5 추가 ──
        "tracking_sensors": [sensor_ids],   # 추적 중인 센서 목록
        "fused_error": float,               # 융합 후 위치 오차 (σ/√N)
    },
    # ── v0.5 추가: 아군 자산 상태 공유 ──
    "friendly_status": {
        shooter_id: {
            "pos": (x, y),
            "ammo_remaining": int,
            "engagement_timer": float,   # 재장전 잔여 시간
            "current_target": threat_id or None,
        }
    },
    # ── v0.5 추가: 대응 계획 공유 ──
    "engagement_plan": {
        threat_id: {
            "assigned_shooters": [shooter_ids],
            "planned_engagement_time": float,
            "priority": int,
        }
    }
}
```

### 구현 상세

#### 1-1. config.py 변경

```python
COP_CONFIG = {
    # 센서 융합 오차 감소 (Kill Web)
    "fusion_error_reduction": True,      # √N 법칙 적용 여부
    "min_fused_error": 0.1,              # 최소 융합 오차 (km)

    # COP 공유 수준
    "linear_cop_level": "threat_only",         # 위협 항적만
    "killweb_cop_level": "full_situational",   # 위협 + 아군 상태 + 대응 계획

    # 아군 상태 공유가 사수 선택에 미치는 효과
    "friendly_status_bonus": 0.15,  # 아군 상태 파악 시 사수 점수 보너스
}
```

#### 1-2. agents.py 변경

**C2NodeAgent 확장**:
```python
class C2NodeAgent:
    def __init__(self, ...):
        self.air_picture = {}        # 기존: 위협 항적
        # v0.5 추가
        self.friendly_status = {}    # 아군 자산 상태
        self.engagement_plan = {}    # 대응 계획

    def update_friendly_status(self, shooter_id, status_dict):
        """Kill Web 전용: 아군 사수 상태 갱신"""
        self.friendly_status[shooter_id] = status_dict

    def update_engagement_plan(self, threat_id, plan_dict):
        """Kill Web 전용: 교전 계획 공유"""
        self.engagement_plan[threat_id] = plan_dict
```

#### 1-3. model.py 변경

**_sensor_detection() 수정** — 센서 융합 오차 감소:
```python
def _fuse_tracks(self, threat_id, new_track, c2_node):
    """Kill Web: 복수 센서 추적 시 융합 오차 감소 (√N 법칙)"""
    existing = c2_node.air_picture.get(threat_id)
    if existing and "tracking_sensors" in existing:
        sensors = existing["tracking_sensors"]
        if new_track["sensor_id"] not in sensors:
            sensors.append(new_track["sensor_id"])
        n = len(sensors)
        base_error = ENGAGEMENT_POLICY["tracking_position_error_std"]
        fused_error = max(base_error / math.sqrt(n), COP_CONFIG["min_fused_error"])
        existing["fused_error"] = fused_error
        existing["pos"] = new_track["pos"]  # 최신 위치 갱신
    else:
        new_track["tracking_sensors"] = [new_track["sensor_id"]]
        new_track["fused_error"] = ENGAGEMENT_POLICY["tracking_position_error_std"]
        c2_node.air_picture[threat_id] = new_track
```

**_execute_engagements() 수정** — COP 품질이 Pk에 미치는 영향:
```python
# Kill Web: 융합 오차 감소 → Pk 향상
if self.architecture == "killweb":
    track = c2_node.air_picture.get(threat.unique_id, {})
    fused_error = track.get("fused_error", base_error)
    pk_bonus = (base_error - fused_error) / base_error * 0.1  # 최대 +10%

# Kill Web: 아군 상태 파악 → 사수 선택 최적화
if self.architecture == "killweb" and c2_node.friendly_status:
    # 재장전 중인 사수 회피, 탄약 풍부한 사수 우선
    shooter_score += COP_CONFIG["friendly_status_bonus"]
```

### 기대 효과
- Kill Web **Pk 향상** (센서 2개 추적 시 오차 0.5→0.35km, 3개 시 0.29km)
- Kill Web **사수 재할당 최적화** (재장전 중 사수 회피, 탄약 부족 사수 교체)
- Linear C2는 **단일 센서 오차 유지** + 사수 가용성 미확인 → 기존 성능 유지
- **아키텍처 간 차이를 COP 품질 차원에서 추가 정량화**

### 기존 테스트 영향
- `air_picture` 딕셔너리 구조 확장 → 기존 테스트는 `threat_id` 키만 참조하므로 **호환 유지**
- `friendly_status`, `engagement_plan`은 Kill Web 전용 → Linear 테스트 무영향

---

## 작업 2: 적응형 교전 정책

### 문제
v0.4 다중 교전에서 SRBM에 3기 사수 투입 → 탄약 고갈 가속 → 후반부 교전 불가

### 설계

#### config.py 추가
```python
ADAPTIVE_ENGAGEMENT = {
    "ammo_threshold_ratio": 0.3,     # 잔여 탄약 30% 이하 시 정책 전환
    "degraded_max_shooters": 1,      # 절약 모드: 위협당 1기만
    "critical_ammo_ratio": 0.1,      # 10% 이하: 고위협만 교전
    "critical_threat_types": ["SRBM", "CRUISE_MISSILE"],
}
```

#### model.py 변경 — `_execute_engagements()` 수정
```python
def _get_adaptive_max_shooters(self, threat, engaged_shooters):
    """잔여 탄약 기반 교전 규모 결정"""
    available_shooters = [s for s in self.shooters if s.can_engage(threat)]
    avg_ammo_ratio = np.mean([s.ammo_count / s.max_ammo for s in available_shooters])

    if avg_ammo_ratio <= ADAPTIVE_ENGAGEMENT["critical_ammo_ratio"]:
        # 위기 모드: 고위협만 교전
        if threat.threat_type not in ADAPTIVE_ENGAGEMENT["critical_threat_types"]:
            return 0  # 교전 포기
        return 1

    if avg_ammo_ratio <= ADAPTIVE_ENGAGEMENT["ammo_threshold_ratio"]:
        return ADAPTIVE_ENGAGEMENT["degraded_max_shooters"]  # 단일 교전

    # 정상 모드: 기존 다중 교전 정책
    return ENGAGEMENT_POLICY["max_simultaneous_shooters"].get(
        threat.threat_type,
        ENGAGEMENT_POLICY["default_max_simultaneous"]
    )
```

### 기대 효과
- 탄약 30% 이하 → 자동 단일 교전 전환 → 교전 지속성 확보
- 탄약 10% 이하 → 고위협(SRBM/CM)만 선별 교전 → 최후 방어
- S4 순차교전(60분 지속) 시나리오에서 특히 효과적

---

## 작업 3: 통신 네트워크 동적 열화

### 현재 상태
- `jamming_level`이 전역 스칼라 → 모든 링크에 동일 영향
- 실제로는 재밍 위치/방향에 따라 링크별 차등 열화

### 설계

#### config.py 추가
```python
COMM_DEGRADATION = {
    "base_latency_factor": 1.0,       # 기본 지연 배수
    "jamming_latency_multiplier": 3.0, # 재밍 시 최대 지연 배수
    "link_failure_threshold": 0.8,     # 재밍 0.8 이상 시 링크 두절
    "killweb_redundancy_factor": 0.5,  # Kill Web 메시 경로 다중화로 열화 완화
}
```

#### comms.py 변경
```python
class CommChannel:
    def get_link_latency(self, src_id, dst_id, jamming_level):
        """링크별 차등 지연 계산"""
        base = self.base_latency
        # 링크 거리 기반 재밍 영향 차등
        link_distance = self._get_link_distance(src_id, dst_id)
        jamming_effect = jamming_level * (link_distance / self.max_link_distance)

        if jamming_effect >= COMM_DEGRADATION["link_failure_threshold"]:
            return float('inf')  # 링크 두절

        latency_multiplier = 1.0 + jamming_effect * COMM_DEGRADATION["jamming_latency_multiplier"]

        # Kill Web: 메시 구조 다중 경로로 열화 완화
        if self.architecture == "killweb":
            latency_multiplier *= COMM_DEGRADATION["killweb_redundancy_factor"]

        return base * latency_multiplier
```

### 기대 효과
- S3 EW 시나리오에서 **아키텍처 간 차이 확대** — Kill Web 메시 다중 경로의 통신 회복력 정량화
- 링크 두절 시 Kill Web은 우회 경로, Linear C2는 킬체인 단절 → 누출률 차이 증가 예상

---

## 작업 4: 2D 전술 시각화 모듈 (신규)

### 목표
이미지 참조와 같은 수준의 2D 전투공간 시각화:
- 에이전트(센서/C2/사수/위협) 배치 및 이동 궤적
- 센서 탐지 범위, 사수 교전 범위 시각화
- 교전 이벤트(발사, 명중, 누출) 실시간 표시
- 킬체인 연결선(탐지→C2→사수) 표시
- 시뮬레이션 시간축 리플레이

### 기술 선택

| 옵션 | 장점 | 단점 |
|------|------|------|
| **matplotlib.animation** (선택) | 기존 의존성 활용, 노트북 호환 | 인터랙티브 제한 |
| plotly + dash | 웹 인터랙티브 | 의존성 추가, 노트북 무거움 |
| pygame | 실시간 렌더링 | 노트북 비호환 |

### 구현: `modules/viz.py` (신규)

#### 핵심 클래스 설계

```python
class TacticalVisualizer:
    """2D 전술 시각화 엔진 (matplotlib.animation 기반)"""

    def __init__(self, sim_result, figsize=(14, 10)):
        """
        sim_result: AirDefenseModel.run_full() 반환값
        필요 데이터: agent 위치, 이벤트 로그, 시간축 상태
        """
        self.events = sim_result["events"]       # 킬체인 이벤트 로그
        self.snapshots = sim_result["snapshots"]  # 매 스텝 에이전트 상태
        self.config = sim_result["config"]

    def render_frame(self, time_step):
        """특정 시간 스텝의 전술 상황도 렌더링"""
        # 배경: 200×200km 작전 영역 (그리드)
        # 센서: 파란 삼각형 + 탐지 범위 부채꼴/원
        # C2: 주황 사각형
        # 사수: 빨간 다이아몬드 + 교전 범위 원
        # 위협: 하늘색 화살표 + 이동 궤적선
        # 방어 목표: 녹색 별
        # 교전 이벤트: 빨간 폭발 마커 (명중) / 회색 X (실패)
        # 킬체인 연결선: 점선 (탐지→C2→사수)

    def animate(self, interval_ms=200, save_path=None):
        """전체 시뮬레이션 리플레이 애니메이션"""
        anim = FuncAnimation(self.fig, self._update_frame,
                             frames=len(self.snapshots),
                             interval=interval_ms)
        if save_path:
            anim.save(save_path, writer='pillow', fps=5)
        return anim

    def snapshot_comparison(self, time_step, architectures=['linear', 'killweb']):
        """동일 시점 두 아키텍처 나란히 비교 스냅샷"""

    def event_timeline(self):
        """이벤트 타임라인 바 차트 (탐지/추적/교전/격추/누출)"""
```

#### model.py 변경 — 스냅샷 데이터 수집

시각화를 위해 `run_full()`에서 매 스텝 에이전트 상태를 기록해야 함:

```python
# model.py — _step() 끝에 추가
def _record_snapshot(self):
    """현재 시점 에이전트 상태 스냅샷 기록"""
    snapshot = {
        "time": self.sim_time,
        "threats": [
            {"id": t.unique_id, "pos": t.pos, "altitude": t.altitude,
             "speed": t.speed, "alive": t.alive, "type": t.threat_type}
            for t in self.threats
        ],
        "sensors": [
            {"id": s.agent_id, "pos": s.pos, "tracking": list(s.tracking.keys())}
            for s in self.sensors
        ],
        "shooters": [
            {"id": s.agent_id, "pos": s.pos, "ammo": s.ammo_count,
             "engaged": s.engagement_timer > 0}
            for s in self.shooters
        ],
        "c2_nodes": [
            {"id": c.agent_id, "pos": c.pos, "tracks": len(c.air_picture)}
            for c in self.c2_nodes
        ],
    }
    self.snapshots.append(snapshot)
```

### 시각화 요소 상세

| 요소 | 심볼 | 색상 | 동적 표현 |
|------|------|------|-----------|
| 센서 | ▲ 삼각형 | 파란색 | 탐지 범위 원 (점선), 추적 중인 위협과 연결선 |
| C2 노드 | ■ 사각형 | 주황색 | 처리 중 위협 수 텍스트 라벨 |
| 사수 | ◆ 다이아몬드 | 빨간색 | 교전 범위 원, 탄약 잔량 바, 교전 시 발사선 |
| 위협 (활성) | → 화살표 | 하늘색 | 이동 궤적선, 고도 텍스트 |
| 위협 (격추) | ✕ | 회색 | 격추 위치에 마커 |
| 위협 (누출) | ✕ | 빨간색 | 누출 위치에 마커 |
| 방어 목표 | ★ 별 | 녹색 | 고정 |
| 킬체인 | --- 점선 | 노란색 | 탐지→C2→사수 경로 (교전 시 표시) |
| 교전 이벤트 | 💥 원 | 빨간/회색 | 명중/실패 구분 |

### 의존성
- 추가 라이브러리 없음 (matplotlib.animation은 matplotlib에 포함)
- GIF 저장 시 `pillow` 필요 (requirements.txt에 추가)

---

## 작업 5: 시각화 노트북 (notebook5)

### `notebook5_tactical_viz.ipynb`

#### 셀 구성
1. **임포트 및 시뮬레이션 실행** — S1 시나리오, 양쪽 아키텍처
2. **정적 스냅샷 비교** — 주요 시점(t=0, t=100, t=300, t=600) 4패널
3. **병렬 비교** — 동일 시점 Linear vs Kill Web 나란히 (2열)
4. **전체 애니메이션** — 리플레이 (GIF 저장)
5. **이벤트 타임라인** — 탐지/교전/격추/누출 시계열
6. **COP 시각화** — 각 C2 노드의 air_picture 범위 비교 (Linear: 부분 / Kill Web: 전체)
7. **전 시나리오 요약 스냅샷** — S1~S5 최종 상태 비교 그리드

---

## 작업 6: 테스트 추가/수정

### 신규 테스트

#### `tests/test_cop_differentiation.py` (8~10개)
```python
class TestCOPConfig:
    def test_cop_config_exists(self):
    def test_linear_cop_level(self):
    def test_killweb_cop_level(self):

class TestSensorFusion:
    def test_fusion_error_reduction(self):
        """복수 센서 추적 시 오차 감소 확인 (√N)"""
    def test_single_sensor_no_fusion(self):
        """단일 센서 추적 시 융합 미적용"""
    def test_min_fused_error(self):
        """최소 오차 하한선 확인"""

class TestCOPContent:
    def test_killweb_has_friendly_status(self):
        """Kill Web COP에 아군 상태 포함"""
    def test_linear_no_friendly_status(self):
        """Linear COP에 아군 상태 미포함"""
    def test_killweb_has_engagement_plan(self):
        """Kill Web COP에 대응 계획 포함"""
```

#### `tests/test_adaptive_engagement.py` (6~8개)
```python
class TestAdaptivePolicy:
    def test_normal_mode_multi_engagement(self):
    def test_degraded_mode_single_engagement(self):
    def test_critical_mode_high_threat_only(self):
    def test_ammo_threshold_transition(self):

class TestCommDegradation:
    def test_link_latency_increases_with_jamming(self):
    def test_link_failure_at_high_jamming(self):
    def test_killweb_redundancy_factor(self):
```

#### `tests/test_viz.py` (4~5개)
```python
class TestTacticalVisualizer:
    def test_snapshot_data_recorded(self):
    def test_render_frame_no_error(self):
    def test_animate_returns_animation(self):
    def test_snapshot_comparison_two_arch(self):
```

### 테스트 목표: 기존 57개 + 신규 ~22개 = **~79개**

---

## 작업 7: 문서 업데이트

### CHANGELOG.md
- v0.5 섹션 추가 (변경사항, 성능 비교표, 발견된 문제, 개선 계획)

### CLAUDE.md
- "현재 버전" → v0.5 업데이트
- "디렉터리 구조"에 `viz.py` 추가
- "핵심 아키텍처 비교" 표에 COP 차별화 항목 추가
- "알려진 문제" 갱신

### README.md
- 로드맵 v0.5 완료 반영
- 프로젝트 구조에 `viz.py`, `notebook5` 추가
- 성능 지표 테이블 갱신 (COP 관련 메트릭 추가 시)

---

## 리스크 및 완화 전략

| 리스크 | 영향 | 완화 |
|--------|------|------|
| COP 확장으로 시뮬레이션 속도 저하 | Monte Carlo 배치 시간 증가 | `friendly_status` 업데이트 주기 조절 (매 스텝→5스텝) |
| 스냅샷 메모리 사용량 증가 | 300회 배치 시 OOM | 스냅샷을 시각화 모드에서만 수집 (`record_snapshots=True`) |
| 센서 융합이 Kill Web 성능을 과도하게 향상 | 비현실적 결과 | √N 감소율 상한 설정 (`min_fused_error=0.1km`) |
| matplotlib 애니메이션 렌더링 시간 | 대규모 시나리오에서 느림 | 프레임 간격 조절, 요약 스냅샷 모드 제공 |
| 적응형 교전이 기존 메트릭에 미치는 영향 | 회귀 비교 어려움 | `adaptive_engagement=True/False` 토글 제공 |

---

## 검증 체크리스트

- [ ] 작업 1 후: `python -m pytest tests/ -v` → 기존 57개 PASS
- [ ] 작업 1 후: Kill Web 센서 융합 시 위치 오차 감소 확인
- [ ] 작업 1 후: Linear COP에 `friendly_status` 없음 확인
- [ ] 작업 2 후: 탄약 30% 이하 → 단일 교전 전환 확인
- [ ] 작업 2 후: S4 순차교전 시나리오에서 교전 지속성 향상 확인
- [ ] 작업 3 후: S3 EW Heavy에서 링크 두절 발생 확인
- [ ] 작업 4 후: 스냅샷 데이터 정상 수집 확인
- [ ] 작업 4 후: `TacticalVisualizer.render_frame()` 에러 없이 렌더링
- [ ] 작업 5 후: 전체 애니메이션 GIF 저장 확인
- [ ] 작업 6 후: `python -m pytest tests/ -v` → ~79개 PASS
- [ ] 최종: 스모크 테스트 (S1, 두 아키텍처) 성능 비교

---

## 다음: v0.6 계획 (예고)

| 작업 | 설명 |
|------|------|
| Monte Carlo 300회 배치 실험 | 전 시나리오 × 2 아키텍처 × 300 시드, 수렴 분석 |
| 인터랙티브 시각화 (선택) | plotly/dash 기반 웹 대시보드 (줌/팬/필터) |
| 최종 분석 보고서 | 통계 검정, 효과 크기, 정책 제언 포함 종합 보고 |

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
