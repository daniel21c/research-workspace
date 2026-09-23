# 공동 인수인계와 작업별 커밋·푸시

두 앱이 아래 명령을 작업 규칙에 따라 실행하면 `공통_작업_인수인계.md`의 자동 구역에 실제 변경·결정, 검증 근거, 한계, 다음 단계가 갱신됩니다. 종료 명령은 조건을 통과한 작업 파일과 인수인계를 커밋하고, 승인된 `https://github.com/daniel21c/research-workspace.git`의 `codex/research-setup` 브랜치까지 푸시한 뒤 원격 SHA 일치를 확인합니다. 에이전트가 규칙을 따르는 방식이며 앱의 네이티브 완료 이벤트·백그라운드 서비스가 아닙니다. Antigravity DB, 대화 원문, 내부 추론은 수집하지 않습니다. 자동 pull/rebase·강제 푸시는 하지 않습니다.

## 현재 연결

- 정확한 저장소: `D:\Research\00_박사논문_연구체계`
- 원격: private `daniel21c/research-workspace`; 기존 `daniel21c/Research`와 별개
- 승인된 자동 커밋·푸시 브랜치: `codex/research-setup` 하나. 다른 `codex/*`에서 생긴 커밋은 자동 푸시할 수 없습니다.
- 여섯 연구 폴더의 기존 코드·문서가 대상이며 공동 원자료·시설자료·분석 결과는 외부 경로에 보존합니다. clone만으로 분석을 재현할 수 없습니다.
- Python: `C:\Users\cyion\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe` (표준 라이브러리만 사용)
- 기존 원장은 활성 상태이며 정책의 `push.enabled`가 푸시 확장 승인을 기록합니다. 새 설치는 `enable` 전 비활성입니다. 실제 상태는 `status`가 기준입니다.

## 매 작업의 필수 순서

먼저 공통 인수인계와 관련 GUIDELINE을 읽고 최신 요청의 허용 경로를 정합니다. 작업 ID는 개인정보 없는 새 UUID나 짧은 고유 ID를 사용합니다. 부모/자식 에이전트가 같은 작업을 이중 등록하지 않도록 **파일을 수정하는 단일 담당자만** 이 순서를 실행합니다. 다른 앱이 작업 중이면 시작 기록은 가능하지만 겹친 두 작업의 자동 커밋은 모두 보류됩니다.

```powershell
$syncPython = 'C:\Users\cyion\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$syncScript = 'D:\Research\00_박사논문_연구체계\tools\research_sync.py'
$syncTask = [guid]::NewGuid().ToString()
& $syncPython $syncScript begin --app codex --task $syncTask
# Antigravity는 --app antigravity. 아래 경로는 실제 작업 허용 경로로 교체.
& $syncPython $syncScript claim --task $syncTask 'README.md'
# 이 시점부터 선언한 파일만 편집하고 해당 변경에 필요한 검증 실행.
& $syncPython $syncScript note --task $syncTask --summary '실제로 바꾼 내용과 사용자 결정' --evidence '실행한 확인과 결과' --remaining '하지 않은 확인과 미해결 사항' --next-step '다음 한 단계'
& $syncPython $syncScript verify --task $syncTask --result passed
& $syncPython $syncScript finish --task $syncTask --dry-run
& $syncPython $syncScript finish --task $syncTask
& $syncPython $syncScript status
```

`verify`는 검증을 실행하는 명령이 아니라 **이미 수행한 검증 결과의 선언**입니다. 의미 있는 테스트가 필요 없는 작은 문서 변경은 근거를 note에 적고 `not_required`를 사용합니다. 실패는 `failed`, 확인하지 않았으면 `not_run`입니다. 선언 뒤 파일이 다시 바뀌면 종료가 보류되므로 재검증 후 기록합니다. `completed`는 이 작업 실행의 종료이며 연구 타당성·논문 완성 인증이 아닙니다.

읽기 전용 작업은 `claim` 없이 `begin → note → verify → finish`하여 인수인계만 커밋·푸시할 수 있습니다. 문서의 관리 구역을 손으로 수정하지 마세요. 수동 연구 결정 본문이 필요한 작업은 기존 수동 인수인계 절차를 따르고 자동 커밋 보류를 허용합니다. `note`는 한 필드 600자, 연락처·알려진 비밀 패턴을 거부합니다. 민감한 내용을 넣지 않을 책임은 작성자에게 있으며 탐지가 완전한 DLP는 아닙니다.

중단·취소·결과 불명 작업은 아래처럼 명시적으로 닫습니다. 자동으로 완료로 바꾸거나 더 최근 작업에 편입하지 않습니다.

```powershell
& $syncPython $syncScript finish --task $syncTask --outcome interrupted
```

## 경계와 보류 조건

- `policy.json`은 **정확한 기존 파일 목록**입니다. `claim`은 그중 이번 작업 경로만, 편집 전에 선언합니다. 새 파일은 별도 검토로 `approved_new_paths`와 `.gitignore`에 정확한 경로를 추가한 다음 새 작업 시작 때 존재하지 않아야 합니다. 기존 미추적 파일은 자동 채택하지 않습니다.
- 데이터·출력·원천자료·비밀 경로, 바이너리, 대형 파일, 심볼릭 링크·Windows junction, 경로 이탈을 거부합니다. 자동화 코드·정책·AGENTS/GEMINI·Git 설정은 자동 커밋 대상이 아니며 별도 검토 후 수동 커밋합니다.
- 시작 때 기존 추적 파일 변경, 작업 중 겹침, HEAD/브랜치 이동, 미선언 파일 변경, 완료 불명, 검증 누락, 선언한 파일의 사용자 스테이징, 수동 인수인계 변경은 자동 커밋을 보류합니다. 작업 시작의 내용 해시와 명시적 경로 선언에 의존하며 다른 앱/사용자가 같은 파일을 몰래 편집한 것을 완벽히 식별하지는 못합니다. 단일 담당 원칙을 지켜야 합니다.
- 별도 인덱스로 커밋을 만들고 실제 Git `index.lock`을 잡습니다. 선택 경로에 사용자 스테이징이 있으면 보류하고, 커밋 후 선택 경로의 인덱스만 새 HEAD와 맞춥니다. 다른 스테이징은 채택하거나 초기화하지 않습니다. `git add .`, stash, reset, checkout, fetch, pull, rebase를 실행하지 않습니다. 푸시는 아래 정확한 목적지와 이번 작업 SHA만 전송합니다.
- Git hooks·외부 clean filter·서명 프로그램은 실행하지 않습니다. `.gitattributes`에서 해당 문서/코드가 `text eol=lf`이고 filter/encoding 변환이 없는지 확인한 뒤 LF로 저장합니다. 작업 파일의 실제 줄바꿈은 변경하지 않습니다.
- 커밋 준비 단계와 실제 커밋 사이에 인수인계를 기록하므로 자동 구역의 `eligible`은 준비 판정입니다. 실제 로컬·원격 SHA, `push_status=verified`, 보류/실패 사유는 `status`와 Git에서 확인합니다. 성공한 푸시 자체의 SHA를 같은 커밋에 넣으려는 재귀 커밋은 하지 않습니다. 다음 작업 기록 때 최신 상태로 갱신됩니다.

## 승인된 푸시와 실패 재시도

사용자는 2026-09-23 “깃은 푸시까지 되어야해. 커밋만이 아님”이라고 명시적으로 승인했습니다. 프로그램과 정책에 같은 정확한 루트·URL·브랜치를 고정합니다. `origin` 하나와 단일 URL만 허용하고 `pushurl`, URL rewrite, mirror·추가 push refspec을 거부합니다. 다른 원격이나 브랜치로 권한을 확대하지 않습니다.

전송 직전 원격 HEAD가 이번 작업 시작 HEAD와 같아야 합니다. 전송은 `작업커밋SHA:refs/heads/codex/research-setup` 하나의 비강제 refspec이며, 실제 커밋의 단일 부모·허용 경로·내용을 다시 검사합니다. 기존 미전송 조상 커밋을 묶어서 올리지 않습니다. 푸시 뒤 `ls-remote`의 원격 SHA가 이 작업 커밋과 같을 때만 `push_status=verified`를 기록합니다.

실패하거나 전송 후 확인이 끊기면 로컬 커밋을 그대로 보존하고 `push_failed` 및 원인을 인수인계 자동 구역과 원장에 기록합니다. 이 기록만으로 추가 커밋·푸시를 반복하지 않으므로 자동 구역만 로컬 변경으로 남을 수 있습니다. 다음 정상 작업이 이를 포함합니다. 미해결 푸시가 있으면 새 `begin`을 보류하고 먼저 아래 재시도를 수행합니다.

```powershell
& $syncPython $syncScript retry-push --task $syncTask
& $syncPython $syncScript status
```

재시도는 새 커밋을 만들지 않습니다. 원격이 이미 해당 SHA이면 전송하지 않고 검증만 합니다. 로컬 HEAD·브랜치·조상 또는 목적지가 바뀌었으면 거부하며 pull/rebase/force로 해결하지 않습니다. 이미 `verified`인 이전 작업을 뒤늦게 재시도해 HEAD가 달라졌다면 `retry_refused`가 나오고 과거 성공 기록은 유지합니다. 인증이나 네트워크가 필요한 경우 실패 원인을 확인한 뒤 같은 작업 ID로 재시도합니다. 코드는 자격 증명·원문 stderr를 인수인계에 저장하지 않습니다.

## 상태·중지·재개·복구

```powershell
& $syncPython $syncScript status
& $syncPython $syncScript pause   # 이후 자동 커밋·푸시 보류; 인수인계 명령은 계속 가능
& $syncPython $syncScript disable # pause와 동일
& $syncPython $syncScript enable  # 정확한 Git 루트·기존 HEAD·codex/* 확인 후 활성화
```

상태·원장·잠금·임시 인덱스는 Git 제외 경로 `.research-sync/state/`에 있습니다. OS 잠금은 프로세스 종료 시 해제됩니다. `status`에 `commit_journal`이 남았으면 추가 자동 실행을 중지합니다. Git ref 변경과 인덱스 교체 사이의 중단일 수 있으므로 **잠금 파일을 무조건 지우지 말고** 해당 journal의 old/new SHA, 현재 HEAD, 작업 트리, `.git/index`/`index.lock`을 읽기 전용으로 비교한 뒤 담당자가 복구합니다. 자동 재시도·자동 덮어쓰기는 하지 않습니다. 완료된 작업 ID는 중복 실행해도 다시 커밋하지 않습니다.

실제 `.git`은 설치 담당자가 관리합니다. 이 프로그램은 브랜치를 만들거나 원격·스케줄러·서비스·앱 hook 신뢰를 설정하지 않습니다. 네이티브 Codex hooks를 향후 추가하려면 별도 어댑터 검증과 `/hooks` 검토가 필요하며 현재 설치의 필수 조건이 아닙니다.

## 검증

```powershell
& $syncPython 'D:\Research\00_박사논문_연구체계\tools\test_research_sync.py'
```

테스트는 시스템 임시 폴더의 합성 저장소와 로컬 bare 원격만 사용하며 실제 인터넷으로 전송하지 않습니다. 실제 연구 알고리즘·원자료를 실행하거나 변경하지 않습니다. 초기 저장소의 과거 공백 경고는 새 코드의 실패나 연구 검증으로 해석하지 않습니다.
