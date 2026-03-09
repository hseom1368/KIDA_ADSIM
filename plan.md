# 위협 비행 프로파일 현실화 계획

## 현재 문제점

현재 모든 위협은 **고정 고도 + 등속 직선 이동**으로 모델링되어 있음:
- `altitude`는 초기화 시 설정된 후 비행 중 **전혀 변하지 않음**
- `speed`도 전 비행 구간 동안 **일정**
- `maneuvering`은 단순 boolean → Pk에 0.85 상수 패널티만 적용
- 거리 계산은 **2D 수평거리**만 사용 (고도 미반영)

결과적으로 SRBM(50km 고도)이 PAC-3(최대 30km) 교전고도를 종말단계에서도
초과하여 요격 자체가 불가능한 구조적 결함이 존재.

---

## 변경 범위

### 파일별 변경 사항

| 파일 | 변경 내용 |
|------|----------|
| `modules/config.py` | 위협별 비행 프로파일 파라미터 추가 |
| `modules/agents.py` | ThreatAgent 비행 프로파일 엔진 구현, 3D 거리 계산 반영 |

---

## 단계별 계획

### 1단계: config.py — 위협별 비행 프로파일 파라미터 정의

`THREAT_PARAMS`의 각 위협에 `flight_profile` 딕셔너리를 추가한다.

#### 1-1. SRBM (KN-23형) — 탄도 미사일 3단계 비행

```python
"SRBM": {
    ...
    "flight_profile": {
        "type": "ballistic",
        "phases": [
            {   # 부스트 단계: 발사 후 급상승·가속
                "name": "boost",
                "duration_ratio": 0.15,      # 전체 비행시간의 15%
                "altitude_start": 0.0,       # km (지상 발사)
                "altitude_end": 50.0,        # km (정점)
                "speed_start": 0.5,          # km/s (발사 직후)
                "speed_end": 2.5,            # km/s (연소 종료)
                "maneuvering": False,
            },
            {   # 중간 단계: 탄도 비행 (포물선 정점)
                "name": "midcourse",
                "duration_ratio": 0.50,      # 전체 비행시간의 50%
                "altitude_start": 50.0,
                "altitude_end": 30.0,        # 하강 시작
                "speed_start": 2.5,
                "speed_end": 2.0,
                "maneuvering": False,
            },
            {   # 종말 단계: 급강하 + 풀업 기동
                "name": "terminal",
                "duration_ratio": 0.35,      # 전체 비행시간의 35%
                "altitude_start": 30.0,
                "altitude_end": 0.0,         # 지면 수준 (목표 충돌)
                "speed_start": 2.0,
                "speed_end": 3.0,            # 중력 가속
                "maneuvering": True,         # KN-23 풀업 기동
            },
        ],
    },
}
```

**근거:**
- KN-23형은 정점 약 50km, 사거리 ~200km의 단거리 탄도미사일
- 종말단계에서 풀업(pull-up) 기동으로 요격 회피 시도
- 부스트 종료 후 중간비행 구간에서 하강 시작, 종말단계에서 급강하
- 종말단계에서 고도 30→0km 구간이 PAC-3 교전 가능 영역(≤30km)

#### 1-2. 순항미사일 (금성-3형) — 해면밀착 순항 + 종말 팝업

```python
"CRUISE_MISSILE": {
    ...
    "flight_profile": {
        "type": "cruise",
        "phases": [
            {   # 부스트/상승 단계
                "name": "boost",
                "duration_ratio": 0.05,
                "altitude_start": 0.0,
                "altitude_end": 0.5,         # km (500m로 상승)
                "speed_start": 0.10,
                "speed_end": 0.27,
                "maneuvering": False,
            },
            {   # 순항 단계: 해면밀착
                "name": "cruise",
                "duration_ratio": 0.85,
                "altitude_start": 0.03,      # km (30m 해면밀착)
                "altitude_end": 0.03,
                "speed_start": 0.27,
                "speed_end": 0.27,
                "maneuvering": False,
            },
            {   # 종말 단계: 팝업 후 다이브 또는 저고도 유지
                "name": "terminal",
                "duration_ratio": 0.10,
                "altitude_start": 0.03,
                "altitude_end": 0.0,         # 목표 충돌
                "speed_start": 0.27,
                "speed_end": 0.30,           # 약간 가속
                "maneuvering": True,         # 종말 회피기동
            },
        ],
    },
}
```

**근거:**
- 금성-3형은 해면밀착(sea-skimming) 대함 순항미사일
- 발사 직후 부스터로 상승 → 순항 엔진 점화 후 30m 고도 유지
- 종말단계에서 기동 가능 (회피 기동 또는 팝업-다이브)

#### 1-3. 고정익 항공기 — 고고도 침투 → 저고도 회피

```python
"AIRCRAFT": {
    ...
    "flight_profile": {
        "type": "aircraft",
        "phases": [
            {   # 순항 접근
                "name": "ingress_high",
                "duration_ratio": 0.60,
                "altitude_start": 10.0,
                "altitude_end": 10.0,
                "speed_start": 0.34,
                "speed_end": 0.34,
                "maneuvering": False,
            },
            {   # 방공망 접근 시 저고도 침투
                "name": "ingress_low",
                "duration_ratio": 0.30,
                "altitude_start": 10.0,
                "altitude_end": 1.0,         # 1km으로 강하
                "speed_start": 0.34,
                "speed_end": 0.30,           # 저고도 감속
                "maneuvering": True,         # 회피기동
            },
            {   # 공격 진입
                "name": "attack_run",
                "duration_ratio": 0.10,
                "altitude_start": 1.0,
                "altitude_end": 0.5,
                "speed_start": 0.30,
                "speed_end": 0.34,
                "maneuvering": True,
            },
        ],
    },
}
```

**근거:**
- 고정익 전투기는 방공망 외곽에서 고고도 순항 후 침투 시 저고도 강하
- 저고도 침투로 레이더 탐지 거리 감소 효과
- 공격 진입 시 회피기동

#### 1-4. UAS 군집 — 저고도 은밀 접근

```python
"UAS": {
    ...
    "flight_profile": {
        "type": "uas",
        "phases": [
            {   # 접근 단계
                "name": "approach",
                "duration_ratio": 0.80,
                "altitude_start": 0.3,
                "altitude_end": 0.3,
                "speed_start": 0.05,
                "speed_end": 0.05,
                "maneuvering": False,
            },
            {   # 종말 강하 (목표 근접 시 고도 낮춤)
                "name": "terminal",
                "duration_ratio": 0.20,
                "altitude_start": 0.3,
                "altitude_end": 0.05,        # 50m로 강하
                "speed_start": 0.05,
                "speed_end": 0.07,           # 최종 돌입 가속
                "maneuvering": True,
            },
        ],
    },
}
```

**근거:**
- 소형 UAS는 대부분 구간에서 저고도 등속 비행
- 목표 근접 시 더 낮은 고도로 강하하여 탐지/요격 회피
- 종말단계에서 돌입 가속 + 회피기동

---

### 2단계: agents.py — ThreatAgent 비행 프로파일 엔진

#### 2-1. `__init__` 수정: 비행 프로파일 초기화

- `flight_profile` 파라미터를 저장
- 전체 비행시간(`total_flight_time`)을 발사 위치~목표 거리와 평균 속도로 사전 계산
- 각 단계의 시작/종료 시각을 사전 계산하여 `phase_timeline` 리스트로 저장
- `self.elapsed_flight_time = 0.0` 추가 (비행 경과 시간 추적)

#### 2-2. `_compute_phase_state(elapsed)` 신규 메서드

경과 시간에 따라 현재 비행 단계를 결정하고, 해당 단계 내 진행률(0~1)에 따라
고도·속도·기동여부를 선형 보간으로 산출:

```python
def _compute_phase_state(self, elapsed):
    """경과 시간 기반 현재 비행 단계의 고도·속도·기동여부 계산"""
    for phase in self.phase_timeline:
        if elapsed <= phase['end_time']:
            # 단계 내 진행률 (0.0 ~ 1.0)
            progress = (elapsed - phase['start_time']) / phase['duration']
            progress = max(0.0, min(1.0, progress))

            alt = phase['altitude_start'] + (phase['altitude_end'] - phase['altitude_start']) * progress
            spd = phase['speed_start'] + (phase['speed_end'] - phase['speed_start']) * progress
            maneuvering = phase['maneuvering']

            return alt, spd, maneuvering

    # 마지막 단계 이후
    last = self.phase_timeline[-1]
    return last['altitude_end'], last['speed_end'], last['maneuvering']
```

#### 2-3. `move(dt)` 수정: 동적 속도·고도 적용

```python
def move(self, dt):
    if not self.is_alive:
        return

    self.elapsed_flight_time += dt

    # 비행 프로파일에서 현재 상태 계산
    self.altitude, self.speed, self.maneuvering = \
        self._compute_phase_state(self.elapsed_flight_time)

    # 기존 2D 이동 로직 (self.speed는 이제 동적)
    dx = self.target_pos[0] - self.pos[0]
    dy = self.target_pos[1] - self.pos[1]
    dist_to_target = math.sqrt(dx**2 + dy**2)

    if dist_to_target < 1.0:
        return

    move_dist = self.speed * dt
    if move_dist >= dist_to_target:
        self.pos = self.target_pos
    else:
        ratio = move_dist / dist_to_target
        self.pos = (self.pos[0] + dx * ratio, self.pos[1] + dy * ratio)
```

핵심 변경: `self.speed`와 `self.altitude`가 매 스텝 갱신되므로
기존 `can_engage()`, `compute_pk()`, `detect()` 코드가 **수정 없이**
동적 고도/속도/기동 상태를 자동 반영함.

#### 2-4. `__init__`에서 `phase_timeline` 계산 로직

```python
# 발사지-목표 거리와 가중평균 속도로 전체 비행시간 추정
total_dist = math.dist(pos, target_pos)
phases = params["flight_profile"]["phases"]
avg_speed = sum(
    p['duration_ratio'] * (p['speed_start'] + p['speed_end']) / 2
    for p in phases
)
self.total_flight_time = total_dist / avg_speed

# 각 단계 절대 시각 계산
t = 0.0
self.phase_timeline = []
for p in phases:
    duration = p['duration_ratio'] * self.total_flight_time
    self.phase_timeline.append({
        'name': p['name'],
        'start_time': t,
        'end_time': t + duration,
        'duration': max(duration, 0.001),  # 0 방지
        'altitude_start': p['altitude_start'],
        'altitude_end': p['altitude_end'],
        'speed_start': p['speed_start'],
        'speed_end': p['speed_end'],
        'maneuvering': p['maneuvering'],
    })
    t += duration
```

#### 2-5. 하위 호환성: flight_profile이 없는 경우

기존 설정과의 하위 호환을 위해, `flight_profile`이 THREAT_PARAMS에 없으면
기존과 동일한 고정 고도/속도 동작을 유지:

```python
if "flight_profile" in params:
    # 비행 프로파일 초기화 (2-4 로직)
    ...
else:
    # 레거시: 고정 고도/속도
    self.phase_timeline = None
    self.total_flight_time = None
    self.elapsed_flight_time = 0.0
```

`move()` 내에서도 `self.phase_timeline is None`이면 기존 로직 유지.

---

### 3단계: 3D 경사거리(Slant Range) 반영

현재 탐지·교전 거리는 2D 수평거리(`math.dist(pos1, pos2)`)만 사용하나,
고도가 동적으로 변하므로 **3D 경사거리** 계산이 필요.

#### 3-1. agents.py에 유틸리티 함수 추가

```python
def _slant_range(pos1, alt1, pos2, alt2):
    """3D 경사거리 = sqrt(수평거리² + 고도차²)"""
    horiz = math.dist(pos1, pos2)
    return math.sqrt(horiz**2 + (alt1 - alt2)**2)
```

#### 3-2. 적용 대상

| 메서드 | 현재 | 변경 |
|--------|------|------|
| `SensorAgent.detect()` | `math.dist(self.pos, threat.pos)` | `_slant_range(self.pos, 0, threat.pos, threat.altitude)` |
| `ShooterAgent.can_engage()` | `math.dist(self.pos, threat.pos)` | `_slant_range(self.pos, 0, threat.pos, threat.altitude)` |
| `ShooterAgent.compute_pk()` | `math.dist(self.pos, threat.pos)` | `_slant_range(self.pos, 0, threat.pos, threat.altitude)` |

센서·사수의 고도는 지상(0km)으로 가정.

---

## 예상 효과

### SRBM 교전 가능 구간 생성
- 종말단계(비행시간 65~100%)에서 고도 30→0km로 하강
- PAC-3 최대 교전 고도 30km 이내 진입 → **교전 가능 시간 창(window)** 생성
- Kill Web: 빠른 S2S로 종말단계 진입 즉시 교전 → 선형 C2 대비 **명확한 이점**

### 순항미사일 종말기동
- 종말단계 `maneuvering=True` → Pk 0.85배 패널티 적용
- 현재는 전 구간 `maneuvering=False`였으므로 교전 난이도 현실적으로 상승

### 항공기 저고도 침투
- 방공권 접근 시 10km→1km 강하 → 레이더 탐지거리 감소 (3D 경사거리 반영)
- 저고도 기동으로 교전 회피 시도

### UAS 종말 강하
- 목표 근접 시 0.3km→0.05km 강하 → 비호 등 단거리 체계의 교전 난이도 상승

---

## 구현 순서 요약

| 순서 | 작업 | 파일 |
|------|------|------|
| 1 | THREAT_PARAMS에 flight_profile 파라미터 추가 | config.py |
| 2 | ThreatAgent.__init__에 비행 프로파일 초기화 + phase_timeline 계산 | agents.py |
| 3 | _compute_phase_state() 메서드 구현 | agents.py |
| 4 | move() 메서드에 동적 고도/속도/기동 반영 | agents.py |
| 5 | _slant_range() 유틸리티 함수 추가 | agents.py |
| 6 | SensorAgent.detect()에 3D 경사거리 적용 | agents.py |
| 7 | ShooterAgent.can_engage(), compute_pk()에 3D 경사거리 적용 | agents.py |
| 8 | 기존 테스트 실행 및 결과 검증 | tests/ |
