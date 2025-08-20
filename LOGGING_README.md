# 📝 일정 공동작업자 로깅 시스템 가이드

## 🎯 개요

이 프로젝트는 일정을 새로 추가할 때 공동작업자가 어떻게 추가되고 DB에 저장되는지 상세하게 추적할 수 있는 로깅 시스템을 제공합니다.

## 🔍 로깅 범위

### 1. 백엔드 로깅 (Python)
- **파일**: `app/routers/schedules.py`
- **기능**: 일정 생성 API 호출 시 상세한 처리 과정 로깅
- **로그 레벨**: INFO, WARNING, ERROR
- **출력**: 서버 콘솔

### 2. 프론트엔드 로깅 (JavaScript)
- **파일**: `static/js/main.js`
- **기능**: 사용자 인터페이스에서의 공동작업자 선택 및 처리 과정 로깅
- **로그 레벨**: console.log, console.error, console.warn
- **출력**: 브라우저 개발자 도구 콘솔

## 📊 로깅 카테고리

### 🚀 [SCHEDULE_CREATE]
일정 생성 과정의 전체적인 흐름을 추적합니다.

**백엔드 로그 예시:**
```
🚀 [SCHEDULE_CREATE] Starting schedule creation for user: june9713 (ID: 1)
📋 [SCHEDULE_CREATE] Schedule data received: {...}
👥 [SCHEDULE_CREATE] Collaborators data extracted: [2, 3]
👥 [SCHEDULE_CREATE] Processing 2 collaborators...
💾 [SCHEDULE_CREATE] Schedule committed to database with ID: 15
👥 [SCHEDULE_CREATE] Successfully added 2 collaborators to schedule 15
🎉 [SCHEDULE_CREATE] Schedule creation completed successfully!
```

**프론트엔드 로그 예시:**
```
🚀 [SCHEDULE_CREATE] Starting schedule creation process...
👥 [SCHEDULE_CREATE] Processing collaborators...
👥 [SCHEDULE_CREATE] Final collaborators array: [2, 3]
📤 [SCHEDULE_CREATE] Final schedule data prepared: {...}
🌐 [SCHEDULE_CREATE] Sending POST request to /schedules/...
✅ [SCHEDULE_CREATE] Schedule created successfully!
```

### 🔍 [COLLABORATORS_SEARCH]
공동작업자 검색 과정을 추적합니다.

**로그 예시:**
```
🔍 [COLLABORATORS_SEARCH] setupCollaboratorsSearch 호출 - formType: add
🔍 [COLLABORATORS_SEARCH] 검색 입력: "admin"
⏱️ [COLLABORATORS_SEARCH] 기존 타임아웃 취소
🔍 [COLLABORATORS_SEARCH] 디바운싱 후 updateCollaboratorsDropdown 호출: "admin"
```

### 🔄 [COLLABORATORS_DROPDOWN]
공동작업자 드롭다운 업데이트 과정을 추적합니다.

**로그 예시:**
```
🔄 [COLLABORATORS_DROPDOWN] updateCollaboratorsDropdown 호출 - formType: add, searchTerm: "admin"
🔄 [COLLABORATORS_DROPDOWN] 현재 선택된 값들: [2, 3]
🔍 [COLLABORATORS_DROPDOWN] 필터링된 사용자 수: 1
➕ [COLLABORATORS_DROPDOWN] 옵션 추가: admin (관리자) - ID: 1
```

### 👥 [COLLABORATORS_SELECTION]
공동작업자 선택 처리 과정을 추적합니다.

**로그 예시:**
```
👥 [COLLABORATORS_SELECTION] mousedown 이벤트 - 옵션: 2, 현재 선택됨: false
👥 [COLLABORATORS_SELECTION] 옵션 텍스트: "user2 (사용자2)"
👥 [COLLABORATORS_SELECTION] 옵션 2 (사용자2) 선택 추가
🔄 [COLLABORATORS_SELECTION] 선택 상태 변경 후 updateSelectedCollaborators 호출
```

### 👥 [COLLABORATORS_DISPLAY]
선택된 공동작업자 표시 업데이트를 추적합니다.

**로그 예시:**
```
👥 [COLLABORATORS_DISPLAY] updateSelectedCollaborators 호출 - formType: add
👥 [COLLABORATORS_DISPLAY] 선택된 옵션들: 2 (사용자2), 3 (사용자3)
👥 [COLLABORATORS_DISPLAY] 최종 선택된 사용자들: 사용자2 (사용자2) - ID: 2, 사용자3 (사용자3) - ID: 3
✅ [COLLABORATORS_DISPLAY] 선택된 사용자 HTML 업데이트 완료 - 2명
```

### 👥 [USERS_LOAD]
사용자 목록 로드 과정을 추적합니다.

**로그 예시:**
```
👥 [USERS_LOAD] loadUsers 함수 호출 시작
🌐 [USERS_LOAD] /users/ API 호출 중...
✅ [USERS_LOAD] 사용자 5명 로드 완료
👥 [USERS_LOAD] 로드된 사용자들: june9713 (박정준) - ID: 1, admin (관리자) - ID: 2, ...
```

### 🔍 [USERS_SEARCH]
사용자 검색 및 필터링 과정을 추적합니다.

**로그 예시:**
```
🔍 [USERS_SEARCH] searchUsers 호출 - searchTerm: "admin"
🔍 [USERS_SEARCH] 현재 사용자 ID: 1
🔍 [USERS_SEARCH] 필터링 전 사용자 수: 5
🔍 [USERS_SEARCH] admin/viewer/자기자신 제외 후 사용자 수: 3
🔍 [USERS_SEARCH] 검색어 "admin"에 대한 결과: 1명
```

## 🛠️ 사용법

### 1. 백엔드 로그 확인
```bash
# 서버 실행 시 콘솔에서 실시간으로 로그 확인
python main.py

# 또는 별도 터미널에서 로그 파일 모니터링
tail -f logs/app.log
```

### 2. 프론트엔드 로그 확인
1. 브라우저에서 F12 키를 눌러 개발자 도구 열기
2. Console 탭 선택
3. 일정 추가 폼에서 공동작업자 선택 시 실시간 로그 확인

### 3. 로그 레벨별 필터링
브라우저 콘솔에서 특정 로그만 보려면:
```javascript
// 특정 카테고리만 보기
console.log = function(...args) {
    if (args[0] && args[0].includes('[SCHEDULE_CREATE]')) {
        console.originalLog.apply(console, args);
    }
};

// 원래 로그 함수 복원
console.originalLog = console.log;
```

## 🔧 로깅 설정 커스터마이징

### 백엔드 로그 레벨 변경
`app/routers/schedules.py`에서:
```python
logger.setLevel(logging.DEBUG)  # DEBUG, INFO, WARNING, ERROR
```

### 프론트엔드 로그 비활성화
`static/js/main.js`에서:
```javascript
// 모든 로그 비활성화
console.log = () => {};
console.error = () => {};
console.warn = () => {};
```

## 📋 로그 분석 팁

### 1. 공동작업자 추가 실패 디버깅
- `[SCHEDULE_CREATE]` 로그에서 실패 지점 확인
- `[COLLABORATORS_SEARCH]` 로그에서 사용자 검색 문제 확인
- `[USERS_LOAD]` 로그에서 사용자 목록 로드 문제 확인

### 2. 성능 분석
- API 호출 시간 측정
- 사용자 검색 응답 시간 확인
- 드롭다운 업데이트 지연 시간 분석

### 3. 사용자 경험 개선
- 사용자가 자주 검색하는 키워드 파악
- 공동작업자 선택 패턴 분석
- 오류 발생 빈도 및 원인 분석

## 🚨 주의사항

1. **프로덕션 환경**: 상세한 로깅은 성능에 영향을 줄 수 있으므로 필요한 경우 로그 레벨을 조정하세요.
2. **개인정보**: 로그에 민감한 정보가 포함되지 않도록 주의하세요.
3. **로그 크기**: 로그 파일이 너무 커지지 않도록 적절한 로테이션 정책을 설정하세요.

## 📞 지원

로깅 시스템에 문제가 있거나 개선 사항이 있다면 개발팀에 문의하세요.
