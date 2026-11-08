# RE:PLAY 개발 프레임워크 설계

PRD의 게임 규칙을 현재 Pico2D 코드(`main.py`, `game_world.py`, `main_character.py`)에 연결하기 위한 구현 설계다. 이 문서는 모듈 책임과 데이터 흐름을 정의하며, PRD의 `미정` 항목을 확정하지 않는다.

## 1. 설계 목표

- 기록한 입력과 분신 재생을 같은 시뮬레이션 규칙으로 실행해 재현성을 확보한다.
- 플레이어, 분신, 퍼즐 오브젝트가 서로의 내부 상태를 직접 변경하지 않도록 한다.
- 입력·물리·퍼즐·UI를 분리하되, 6주 프로젝트에 맞게 단순한 Python 모듈 구조를 유지한다.
- 스테이지 복구 시 플레이어, 오브젝트, 퍼즐, 슬롯 상태를 명시한 정책에 따라 일관되게 초기화한다.

## 2. 권장 모듈 구조

```text
project/
  main.py                 # Pico2D 초기화, 메인 루프, 종료
  config.py               # 화면, 키, 고정 업데이트 간격, 물리 상수, 레이어
  input_manager.py        # SDL 이벤트와 현재 입력 상태를 게임 명령으로 변환
  game_world.py           # 레이어별 객체 관리, 업데이트, 렌더, 지연 등록/제거
  game_mode.py            # TITLE, PLAYING, STAGE_CLEAR 등 상태 전환
  main_character.py       # 기존 플레이어 이동/애니메이션을 유지하며 명령 기반으로 확장
  tiled_map.py            # Tiled JSON 로딩, 타일 렌더링, 충돌/스폰 정보
  echo_character.py       # ActionFrame을 소비하는 분신
  action_recorder.py      # 슬롯 상태, 기록 데이터, 녹화 및 재생 생성
  physics.py              # 지형/오브젝트 충돌 및 겹침 해소
  game_objects.py         # Ground, Switch, Door, Box, Exit
  puzzle_controller.py    # 센서 이벤트와 퍼즐 조건 연결
  stage_snapshot.py       # 스테이지 상태 캡처 및 복구
  stage.py                # 스테이지 구성 및 초기화
  ui.py                   # 슬롯 UI, 월드 재생 표식, 상호작용 안내
  maps/
    stage_01.tmj          # Tiled 맵
    tileset.tsj            # 외부 JSON 타일셋
    tileset.png            # 타일 이미지
  sprite/
```

처음부터 각 파일을 모두 만들 필요는 없다. 우선 `tiled_map.py`로 샘플 맵을 불러오고, `input_manager.py`, `action_recorder.py`, `echo_character.py`, `physics.py`를 기능 순서에 맞춰 추가한다. 오브젝트·UI·스테이지 코드는 필요 시 분리하며, 기존 파일을 이름만 바꾸는 리팩터링은 피한다.

## 3. 책임과 의존 방향

| 모듈 | 책임 | 직접 소유하지 않는 것 |
|---|---|---|
| `main.py` | Pico2D 생명주기, 프레임 루프, 시간 누적 | 퍼즐 규칙, 슬롯 데이터 |
| `input_manager.py` | 눌림/해제 이벤트, 지속 입력, 단발 입력 관리 | 플레이어 물리 상태 |
| `game_mode.py` | 제목/플레이/완료 상태, 입력 라우팅 | 개별 오브젝트 내부 상태 |
| `game_world.py` | 객체 등록·제거·업데이트·렌더 순회 | 스테이지 규칙 |
| `main_character.py` | 이동 명령 적용, 충돌체, 애니메이션 | SDL 이벤트 직접 수집, 기록 저장 |
| `tiled_map.py` | `.tmj`/`.tsj` 읽기, 타일 렌더링, 충돌 사각형과 스폰 위치 제공 | 퍼즐 상태, 플레이어 입력 |
| `action_recorder.py` | 슬롯 상태 및 행동 데이터 관리 | 렌더링, 캐릭터 충돌 계산 |
| `echo_character.py` | 해당 슬롯의 기록을 순서대로 명령으로 제공 | 키보드 입력 |
| `physics.py` | 충돌 탐색과 이동 보정 | 스테이지 진행 상태 |
| `puzzle_controller.py` | 스위치/문/출구 조건 계산 | 렌더링, 키 입력 |
| `stage_snapshot.py` | 지정 상태의 캡처와 복구 | 임의의 전역 변수 초기화 |
| `ui.py` | 모델 상태를 화면/월드 UI로 표현 | 게임 규칙 변경 |

의존 방향은 `main → game_mode → recorder/world/controller → game objects`를 기본으로 한다. 플레이어·분신은 공통 명령과 물리 규칙을 사용하되, 분신이 플레이어의 입력 처리나 슬롯을 직접 수정하지 않는다. 문은 스위치 객체의 내부 변수를 직접 읽지 않고 퍼즐 컨트롤러가 계산한 논리 조건을 받는다.

## 4. 게임 루프와 입력 처리

### 루프

렌더 프레임과 시뮬레이션을 분리한다. `FIXED_DT`는 `config.py`에 두고, 초기값은 1/60초를 제안한다.

```text
SDL 이벤트 수집
  → InputManager 상태 갱신
  → 누적 시간에 따라 고정 시뮬레이션 틱 실행
      → 게임 모드가 입력 명령 생성
      → 플레이어/분신에 명령 적용
      → 물리 및 충돌 해결
      → 센서/퍼즐 상태 갱신
      → 녹화 중이면 적용한 명령 기록
      → 대기 중인 월드 객체 추가/제거 반영
  → 화면 초기화
  → GameWorld 렌더
  → update_canvas
```

실제 입력 이벤트는 이벤트가 들어온 순서대로 저장하고, 시뮬레이션 틱에서 적용한다. 한 렌더 프레임에 여러 고정 틱이 실행되더라도 단발 입력(점프/상호작용)이 중복 발화하지 않도록 `pressed`와 `just_pressed`를 구분한다. 누적 시간과 한 프레임 처리 틱 수에는 상한을 둬 프레임 급락 후 과도한 보정이 생기지 않게 한다.

### 명령 데이터

게임 객체는 Pico2D SDL 이벤트 대신 정규화된 명령을 받는다.

```text
PlayerCommand
  move_x: -1 | 0 | 1
  jump_pressed: bool
  interact_pressed: bool
  interact_target_id: str | None
```

입력 매핑은 `input_manager.py` 또는 `config.py` 한 곳에서 관리한다. 플레이어와 기록기가 같은 틱의 `PlayerCommand`를 공유해, 실제 플레이와 저장된 기록의 입력이 어긋나지 않게 한다.

## 5. 행동 기록과 분신 재생

### 기록 모델

```text
ActionFrame
  tick: int
  move_x: int
  jump_pressed: bool
  interact_pressed: bool
  target_id: str | None

Recording
  start_pose: Pose
  frames: list[ActionFrame]

SlotData
  index: int
  unlocked: bool
  state: LOCKED | EMPTY | RECORDING | RECORDED | PLAYING
  recording: Recording | None
  active_echo_id: str | None
```

각 시뮬레이션 틱의 명령을 기록하는 단순한 방식부터 구현한다. `tick`은 녹화 시작을 0으로 둔 정수 틱이며, 이동 입력의 유지와 점프/상호작용의 단발 입력을 모두 보존한다. 기록 길이 제한은 `config.py` 설정으로 두고, 최대 길이 도달 시 동작은 PRD 미정 항목으로 결정한다.

### 상태 전이

```text
LOCKED → EMPTY
EMPTY → RECORDING → RECORDED
RECORDED → RECORDING → RECORDED   # 새 기록으로 교체
RECORDED → PLAYING → RECORDED     # 재생 종료 후 기록 유지
RECORDING → EMPTY                 # 프레임 없는 기록 취소
```

기록 중 같은 슬롯 키 재입력 시 종료할지, 별도 키/자동 종료를 사용할지는 PRD에서 결정한 뒤 입력 라우터에 반영한다. 녹화 시작 시 기존 기록을 즉시 버릴지 새 기록 확정 시 교체할지도 정책으로 명확히 정한다. 분신은 시작 포즈에서 생성되고, 각 틱에 기록된 명령을 공급받는다. 대상 ID가 없거나 더는 유효하지 않은 상호작용은 해당 명령만 건너뛴다.

## 6. 월드와 물리

- `GameWorld`는 `BACKGROUND`, `TERRAIN`, `INTERACTABLE`, `ACTOR`, `WORLD_UI`, `SCREEN_UI` 레이어를 가진다.
- 월드 객체 변경은 순회 중 직접 리스트를 수정하지 않고 추가/제거 큐를 사용한다. 틱 처리가 끝난 뒤 큐를 반영한다.
- `update(dt, command)` 또는 그에 준하는 명시적 메서드로 시간과 입력을 전달한다. 객체 내부에서 별도로 `perf_counter()`를 호출해 게임 시간을 계산하지 않는다.
- 플레이어와 분신은 충돌 박스와 스프라이트 영역을 분리한다. `physics.py`가 이동 후 지형과 동적 오브젝트 충돌을 해결한다.
- 첫 구현은 축별 이동과 겹침 해소로 시작한다. 빠른 움직임에서 관통이 확인된 경우에만 고정 스텝 보완이나 세분 검사를 추가한다.
- 센서는 충돌체의 `actor_type`(예: player, echo, box)을 이용해 접촉 대상을 판별한다. 퍼즐 컨트롤러는 접촉 목록과 스테이지 연결 정보를 바탕으로 문 상태를 갱신한다.

## 7. Tiled 맵 제작과 실행 연결

### 프로젝트의 맵 규약

- 맵 편집 도구는 Tiled Editor다. 실행 중에는 외부 Tiled 런타임이나 추가 Python 패키지를 쓰지 않고, `tiled_map.py`가 Tiled JSON을 읽는다.
- 현재 프로젝트는 유한 크기의 `orthogonal` 맵과 이미지 타일셋을 사용한다. 맵은 `.tmj`, 외부 타일셋은 `.tsj`, 이미지는 `.png`를 `maps/` 아래에 둔다. 맵·타일셋·이미지 경로는 서로의 위치를 기준으로 해석된다.
- 맵 타일 크기와 타일셋 타일 크기는 같아야 한다. Tiled의 `infinite map`은 끄고, 타일 레이어는 압축하지 않은 JSON 배열 또는 CSV로 저장한다.
- 레이어 이름과 용도:

| 레이어 이름 | Tiled 레이어 종류 | 용도 |
|---|---|---|
| `Background` | Tile Layer | 배경 타일 |
| `Terrain` | Tile Layer | 플랫폼/지형 이미지 |
| `Collision` | Object Layer | 충돌하는 사각형 오브젝트 |
| `Markers` | Object Layer | `PlayerSpawn` 포인트 등 위치 마커 |

- 플레이어 시작 지점은 `Markers` 레이어의 오브젝트 이름을 정확히 `PlayerSpawn`으로 지정한다. 맵당 하나만 허용한다. 누락 시 실행 코드는 기본 시작 좌표를 사용한다.
- 지형 그림과 충돌은 별도 데이터다. 플랫폼을 그린 뒤 `Collision` 레이어에 회전하지 않은 사각형을 추가해야 캐릭터가 충돌한다. 오브젝트 좌표를 좌상단·Y-아래 방향의 맵 픽셀 좌표로 작성하면 로더가 Pico2D 좌표로 변환한다.

### 지원 범위와 제작 절차

현재 로더는 직교·유한 맵, 이미지 아틀라스, 타일 레이어와 충돌 사각형을 지원한다. 무한 맵, Base64/압축 데이터, 그룹 레이어, 타일 오브젝트 충돌, 대각선/육각 타일 변환은 지원하지 않으며, 오류를 표시한다. 편집 중인 맵은 Tiled에서 JSON으로 저장한다.

1. Tiled에서 프로젝트의 `maps/stage_01.tmj`를 열거나 새로 만든다.
2. 맵 방향을 `Orthogonal`, 맵 크기를 finite로 설정하고, 프로젝트에서 사용하는 타일 크기를 지정한다.
3. 타일셋을 `.tsj`로 저장하고 타일 이미지 경로가 맵 파일과 올바르게 연결되는지 확인한다.
4. `Background`, `Terrain`, `Collision`, `Markers` 레이어를 만든다. 충돌 레이어에는 사각형 오브젝트, 마커 레이어에는 이름이 `PlayerSpawn`인 포인트를 둔다.
5. `.tmj`를 저장한 뒤 프로젝트를 실행한다. 시작 단계에서는 `main.py`가 `maps/stage_01.tmj`를 로드하며, 맵 이미지와 충돌 정보가 함께 적용된다.

`maps/stage_01.tmj`, `maps/tileset.tsj`, `maps/tileset.png`는 바로 실행하고 편집할 수 있는 시작 맵이다. Tiled는 별도 설치가 필요한 편집 도구지만, 맵 재생에는 추가 Python 의존성이 없다.

## 8. 스테이지 상태 저장과 복구

`StageSnapshot`은 스테이지 시작 또는 명시된 체크포인트에서 생성한다.

```text
StageSnapshot
  player_state
  resettable_object_states: dict[object_id, state]
  puzzle_state
  slot_state: policy-defined
```

복구 순서는 다음과 같이 고정한다.

1. 입력 및 시뮬레이션을 잠근다.
2. 활성 분신과 임시 효과를 제거한다.
3. 저장 대상 오브젝트와 퍼즐 상태를 복원한다.
4. 플레이어 위치·방향·이동 상태를 복원한다.
5. 슬롯 기록/해금 정책을 적용한다.
6. 충돌 센서와 퍼즐 조건을 다시 계산한다.
7. 입력을 재개한다.

복구 대상과 기록/해금 유지 정책은 코드 곳곳의 조건문으로 흩뜨리지 않고 `ResetPolicy` 또는 동등한 설정 한 곳에 둔다. PRD의 C/Z 조작은 저장 시점·대상·실패 복구와의 관계가 확정된 뒤 연결한다.

## 9. UI 상태 연결

- UI는 슬롯 데이터와 게임 상태를 읽기만 하고, 키 입력 처리나 슬롯 전이를 직접 수행하지 않는다.
- 하단 슬롯 UI는 화면 좌표를 사용하고, 분신 재생 표식은 월드 좌표를 사용한다.
- 재생 표식은 기록의 시작 포즈에 배치한다. 기록이 없는 슬롯의 표식 위치는 PRD에서 결정하기 전까지 UI 정책으로 하드코딩하지 않는다.
- 상호작용 가능한 오브젝트 강조는 상호작용 대상 선택 결과를 받아 표시한다. 대상 선택 우선순위는 `input_manager`가 아니라 상호작용 판정 책임 모듈 한 곳에서 결정한다.

## 10. 현재 코드에서의 이행 순서

1. **시간 흐름 통일**: `game_world.update()`가 `dt`를 전달하도록 바꾸고, `main_character.py`의 내부 시각 계산을 제거한다. 이동 동작은 유지한다.
2. **명령 기반 입력**: `InputManager`를 추가해 기존 A/D·방향키 및 Space 입력을 `PlayerCommand`로 변환한다. E 상호작용은 대상 선택 규칙이 정해진 뒤 연결한다.
3. **월드 안전성**: 객체 업데이트 중 추가/제거가 필요한 경우를 위해 지연 변경 큐를 도입한다.
4. **단일 슬롯 수직 슬라이스**: I로 기록, J로 재생, 분신 제거, 하단 슬롯 상태 표시까지 한 퍼즐 공간에서 완성한다. 우선 이동/점프를 대상으로 하고 상호작용 기록은 다음 단계에서 붙인다.
5. **퍼즐과 복구**: 스위치·문 한 조합과 스냅샷 복구를 구현하고 반복 복구를 검증한다.
6. **확장과 폴리싱**: 두 번째/세 번째 슬롯, 스테이지 진행, 튜토리얼과 피드백을 추가한다.

## 11. 초기 검증 기준

- 동일한 초기 상태와 동일한 `ActionFrame` 목록을 반복 재생했을 때 명령 순서와 최종 상태가 일치한다.
- 슬롯별 I/O/P 기록과 J/K/L 재생 매핑이 서로 뒤바뀌지 않는다.
- 기록 완료, 재생, 종료, 재생 재시작 시 UI가 `SlotData` 상태와 일치한다.
- 분신 제거가 월드 순회 중 목록 오류를 일으키지 않는다.
- 복구를 연속 두 번 실행해도 오브젝트 중복 생성이나 퍼즐 이벤트 중복이 발생하지 않는다.
- 렌더 프레임률 변화에도 시뮬레이션 틱과 기록 타이밍이 유지된다.

## 12. 구현 전 결정이 필요한 게임 규칙

아래 정책은 프레임워크에서 교체 가능하게 두고, 구현 전에 PRD와 함께 확정한다.

1. I/O/P 녹화 종료 방식과 최대 길이 도달 시 동작.
2. 녹화 시작 시 기존 슬롯 데이터를 즉시 교체할지 여부.
3. 분신 시작 위치·방향과 재생 중 충돌이 기록과 달라졌을 때의 처리.
4. 슬롯 간 동시 재생과 같은 슬롯 재입력 규칙.
5. 스위치/문/상자 상호작용 권한과 상호작용 대상 선택 방식.
6. 실패 판정, 스냅샷 기준 시점, 복구 후 기록·해금 유지 정책.
7. C/Z 키의 저장·복구 의미와 저장 슬롯의 범위.
