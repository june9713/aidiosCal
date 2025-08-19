
달력 화면과 주간 일정 표시 HTML을 생성하는 방법을 알아보기 위해 먼저 현재 프로젝트 구조를 파악하겠습니다.

Ran tool
`_helper` 디렉토리가 있으니 먼저 거기서 `getAllfiles.py`를 실행하여 전체 파일 구조를 파악하겠습니다.

Ran tool

Ran tool

Ran tool
기존 파일들을 확인하여 현재 프로젝트 상태를 파악해보겠습니다.

Read file: static/index.html

Ran tool

Ran tool

Read file: static/js/main.js
달력 관련 기능을 찾기 위해 CSS 파일과 추가 JS 파일을 확인해보겠습니다.

Ran tool

Ran tool

Ran tool
현재 프로젝트에는 달력 UI가 없고 일정 관리 시스템만 있는 것으로 보입니다. 계획을 세우고 달력 화면과 주간 달력을 생성해보겠습니다.

Ran tool

Read file: _plan/plan0007.txt
이제 달력 기능 추가에 대한 새로운 계획을 수립하겠습니다.

Read file: _plan/plan0000.txt
이제 달력 화면과 주간 달력 기능을 추가하는 새로운 계획을 작성하겠습니다.

달력 화면을 생성하기 위해서는 다음과 같은 방법들이 있습니다:

## 달력 화면 구현 방법

### 1. 월간 달력 화면 (Calendar Grid View)
- 7x6 그리드 형태의 전통적인 달력 UI
- 날짜별 일정 표시
- 월/년 네비게이션

### 2. 주간 달력 화면 (Weekly Calendar View)  
- 1주일 단위로 일정을 표시
- 시간대별 일정 배치
- 좌우 스크롤로 주 이동

### 3. 구현 방향
현재 프로젝트 구조를 보면 일정 관리 시스템이 이미 구축되어 있고, 다음과 같이 추가하는 것이 좋겠습니다:

1. **새로운 HTML 파일 생성**:
   - `calendar-monthly.html` - 월간 달력 화면
   - `calendar-weekly.html` - 주간 달력 화면

2. **CSS 스타일 추가**: `style.css`에 달력 관련 스타일 추가

3. **JavaScript 기능 추가**: `calendar.js` 파일 생성

4. **기존 시스템과의 통합**: 현재 일정 데이터 API와 연동

구체적으로 생성해보겠습니다:

### 월간 달력 HTML 생성

```html:static/calendar-monthly.html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>월간 달력 - 일정 관리 시스템</title>
    <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <div class="calendar-container">
        <header class="calendar-header">
            <div class="calendar-nav">
                <button id="prev-month" class="nav-btn">
                    <i class="fas fa-chevron-left"></i>
                </button>
                <h1 id="current-month-year"></h1>
                <button id="next-month" class="nav-btn">
                    <i class="fas fa-chevron-right"></i>
                </button>
            </div>
            <div class="calendar-controls">
                <button id="today-btn" class="control-btn">오늘</button>
                <button id="week-view-btn" class="control-btn">주간보기</button>
                <button id="list-view-btn" class="control-btn">목록보기</button>
            </div>
        </header>

        <div class="calendar-grid">
            <div class="calendar-weekdays">
                <div class="weekday">일</div>
                <div class="weekday">월</div>
                <div class="weekday">화</div>
                <div class="weekday">수</div>
                <div class="weekday">목</div>
                <div class="weekday">금</div>
                <div class="weekday">토</div>
            </div>
            <div id="calendar-days" class="calendar-days"></div>
        </div>
    </div>

    <!-- 일정 상세 모달 -->
    <div id="schedule-detail-modal" class="modal" style="display: none;">
        <div class="modal-content">
            <div class="modal-header">
                <h3>일정 상세</h3>
                <span class="close">&times;</span>
            </div>
            <div id="schedule-detail-content"></div>
        </div>
    </div>

    <script src="/static/js/calendar.js"></script>
</body>
</html>
```

### 주간 달력 HTML 생성

```html:static/calendar-weekly.html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>주간 달력 - 일정 관리 시스템</title>
    <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <div class="weekly-calendar-container">
        <header class="weekly-header">
            <div class="weekly-nav">
                <button id="prev-week" class="nav-btn">
                    <i class="fas fa-chevron-left"></i>
                </button>
                <h1 id="current-week-range"></h1>
                <button id="next-week" class="nav-btn">
                    <i class="fas fa-chevron-right"></i>
                </button>
            </div>
            <div class="weekly-controls">
                <button id="today-btn" class="control-btn">이번 주</button>
                <button id="month-view-btn" class="control-btn">월간보기</button>
                <button id="list-view-btn" class="control-btn">목록보기</button>
            </div>
        </header>

        <div class="weekly-grid">
            <div class="time-column">
                <div class="time-header"></div>
                <div class="time-slots"></div>
            </div>
            <div class="days-container">
                <div class="days-header"></div>
                <div class="days-grid"></div>
            </div>
        </div>
    </div>

    <!-- 일정 상세 모달 -->
    <div id="schedule-detail-modal" class="modal" style="display: none;">
        <div class="modal-content">
            <div class="modal-header">
                <h3>일정 상세</h3>
                <span class="close">&times;</span>
            </div>
            <div id="schedule-detail-content"></div>
        </div>
    </div>

    <script src="/static/js/calendar.js"></script>
</body>
</html>
```

### CSS 스타일 추가

`style.css` 파일에 다음 스타일을 추가해야 합니다:

```css:static/css/style.css
/* ... 기존 코드 ... */

/* ===== 달력 관련 스타일 ===== */

/* 월간 달력 스타일 */
.calendar-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.calendar-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 2px solid #e1e5e9;
}

.calendar-nav {
    display: flex;
    align-items: center;
    gap: 20px;
}

.calendar-nav h1 {
    margin: 0;
    font-size: 1.8rem;
    color: #2c3e50;
    min-width: 200px;
    text-align: center;
}

.nav-btn {
    background: #3498db;
    color: white;
    border: none;
    padding: 10px 15px;
    border-radius: 50%;
    cursor: pointer;
    transition: background-color 0.3s;
    width: 45px;
    height: 45px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.nav-btn:hover {
    background: #2980b9;
}

.calendar-controls {
    display: flex;
    gap: 10px;
}

.control-btn {
    background: #95a5a6;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 5px;
    cursor: pointer;
    transition: background-color 0.3s;
}

.control-btn:hover {
    background: #7f8c8d;
}

.calendar-grid {
    border: 1px solid #ddd;
    border-radius: 8px;
    overflow: hidden;
}

.calendar-weekdays {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    background: #34495e;
}

.weekday {
    padding: 15px;
    text-align: center;
    color: white;
    font-weight: bold;
    border-right: 1px solid #2c3e50;
}

.weekday:last-child {
    border-right: none;
}

.calendar-days {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 1px;
    background: #ddd;
}

.calendar-day {
    background: white;
    min-height: 120px;
    padding: 8px;
    position: relative;
    cursor: pointer;
    transition: background-color 0.2s;
}

.calendar-day:hover {
    background: #f8f9fa;
}

.calendar-day.other-month {
    background: #f5f5f5;
    color: #999;
}

.calendar-day.today {
    background: #e3f2fd;
    border: 2px solid #2196f3;
}

.day-number {
    font-weight: bold;
    margin-bottom: 5px;
}

.day-schedules {
    font-size: 0.8rem;
}

.schedule-item {
    background: #3498db;
    color: white;
    padding: 2px 4px;
    margin: 1px 0;
    border-radius: 3px;
    cursor: pointer;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.schedule-item.completed {
    background: #95a5a6;
    text-decoration: line-through;
}

.schedule-item.high-priority {
    background: #e74c3c;
}

.schedule-item.medium-priority {
    background: #f39c12;
}

/* 주간 달력 스타일 */
.weekly-calendar-container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.weekly-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 2px solid #e1e5e9;
}

.weekly-nav {
    display: flex;
    align-items: center;
    gap: 20px;
}

.weekly-nav h1 {
    margin: 0;
    font-size: 1.8rem;
    color: #2c3e50;
    min-width: 300px;
    text-align: center;
}

.weekly-controls {
    display: flex;
    gap: 10px;
}

.weekly-grid {
    display: flex;
    border: 1px solid #ddd;
    border-radius: 8px;
    overflow: hidden;
}

.time-column {
    width: 80px;
    background: #f8f9fa;
    border-right: 1px solid #ddd;
}

.time-header {
    height: 60px;
    border-bottom: 1px solid #ddd;
}

.time-slots {
    display: flex;
    flex-direction: column;
}

.time-slot {
    height: 60px;
    padding: 5px;
    border-bottom: 1px solid #eee;
    font-size: 0.8rem;
    text-align: right;
    color: #666;
}

.days-container {
    flex: 1;
}

.days-header {
    height: 60px;
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    background: #34495e;
}

.day-header {
    padding: 15px;
    text-align: center;
    color: white;
    font-weight: bold;
    border-right: 1px solid #2c3e50;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.day-header:last-child {
    border-right: none;
}

.day-date {
    font-size: 1.2rem;
}

.day-name {
    font-size: 0.9rem;
    opacity: 0.8;
}

.days-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    position: relative;
}

.day-column {
    border-right: 1px solid #eee;
    position: relative;
}

.day-column:last-child {
    border-right: none;
}

.hour-slot {
    height: 60px;
    border-bottom: 1px solid #eee;
    position: relative;
    padding: 2px;
}

.weekly-schedule-item {
    position: absolute;
    background: #3498db;
    color: white;
    padding: 2px 4px;
    border-radius: 3px;
    font-size: 0.8rem;
    cursor: pointer;
    z-index: 10;
    min-height: 20px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}

.weekly-schedule-item.completed {
    background: #95a5a6;
    text-decoration: line-through;
}

.weekly-schedule-item.high-priority {
    background: #e74c3c;
}

.weekly-schedule-item.medium-priority {
    background: #f39c12;
}

/* 반응형 디자인 */
@media (max-width: 768px) {
    .calendar-header, .weekly-header {
        flex-direction: column;
        gap: 15px;
    }
    
    .calendar-nav h1, .weekly-nav h1 {
        font-size: 1.4rem;
        min-width: auto;
    }
    
    .calendar-day {
        min-height: 80px;
    }
    
    .weekly-grid {
        overflow-x: auto;
    }
    
    .time-column {
        width: 60px;
    }
    
    .days-container {
        min-width: 600px;
    }
}
```

### JavaScript 달력 기능 구현

```javascript:static/js/calendar.js
// 달력 관련 전역 변수
let currentDate = new Date();
let currentView = 'month'; // 'month' 또는 'week'
let schedules = [];

// 달력 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeCalendar();
    loadSchedules();
    setupEventListeners();
});

// 달력 초기화
function initializeCalendar() {
    if (document.querySelector('.calendar-container')) {
        currentView = 'month';
        renderMonthCalendar();
    } else if (document.querySelector('.weekly-calendar-container')) {
        currentView = 'week';
        renderWeeklyCalendar();
    }
}

// 이벤트 리스너 설정
function setupEventListeners() {
    // 월간 달력 이벤트
    const prevMonth = document.getElementById('prev-month');
    const nextMonth = document.getElementById('next-month');
    const todayBtn = document.getElementById('today-btn');
    
    if (prevMonth) prevMonth.addEventListener('click', goToPreviousMonth);
    if (nextMonth) nextMonth.addEventListener('click', goToNextMonth);
    if (todayBtn) todayBtn.addEventListener('click', goToToday);
    
    // 주간 달력 이벤트
    const prevWeek = document.getElementById('prev-week');
    const nextWeek = document.getElementById('next-week');
    
    if (prevWeek) prevWeek.addEventListener('click', goToPreviousWeek);
    if (nextWeek) nextWeek.addEventListener('click', goToNextWeek);
    
    // 보기 전환 버튼들
    const weekViewBtn = document.getElementById('week-view-btn');
    const monthViewBtn = document.getElementById('month-view-btn');
    const listViewBtn = document.getElementById('list-view-btn');
    
    if (weekViewBtn) weekViewBtn.addEventListener('click', () => switchView('week'));
    if (monthViewBtn) monthViewBtn.addEventListener('click', () => switchView('month'));
    if (listViewBtn) listViewBtn.addEventListener('click', () => switchView('list'));
}

// 일정 데이터 로드
async function loadSchedules() {
    try {
        const token = localStorage.getItem('token');
        if (!token) {
            console.error('토큰이 없습니다.');
            return;
        }
        
        const response = await fetch('/schedules/', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            schedules = data.schedules || data || [];
            renderCurrentView();
        } else {
            console.error('일정 로드 실패:', response.status);
        }
    } catch (error) {
        console.error('일정 로드 중 오류:', error);
    }
}

// 현재 뷰 렌더링
function renderCurrentView() {
    if (currentView === 'month') {
        renderMonthCalendar();
    } else if (currentView === 'week') {
        renderWeeklyCalendar();
    }
}

// 월간 달력 렌더링
function renderMonthCalendar() {
    const monthYearElement = document.getElementById('current-month-year');
    const calendarDays = document.getElementById('calendar-days');
    
    if (!monthYearElement || !calendarDays) return;
    
    // 월/년 표시
    const monthNames = ['1월', '2월', '3월', '4월', '5월', '6월', 
                       '7월', '8월', '9월', '10월', '11월', '12월'];
    monthYearElement.textContent = `${currentDate.getFullYear()}년 ${monthNames[currentDate.getMonth()]}`;
    
    // 달력 날짜 생성
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay());
    
    const today = new Date();
    calendarDays.innerHTML = '';
    
    for (let i = 0; i < 42; i++) {
        const cellDate = new Date(startDate);
        cellDate.setDate(startDate.getDate() + i);
        
        const dayElement = document.createElement('div');
        dayElement.className = 'calendar-day';
        
        // 날짜 클래스 설정
        if (cellDate.getMonth() !== month) {
            dayElement.classList.add('other-month');
        }
        if (cellDate.toDateString() === today.toDateString()) {
            dayElement.classList.add('today');
        }
        
        // 날짜 번호
        const dayNumber = document.createElement('div');
        dayNumber.className = 'day-number';
        dayNumber.textContent = cellDate.getDate();
        dayElement.appendChild(dayNumber);
        
        // 해당 날짜의 일정들
        const daySchedules = getSchedulesForDate(cellDate);
        const schedulesContainer = document.createElement('div');
        schedulesContainer.className = 'day-schedules';
        
        daySchedules.slice(0, 3).forEach(schedule => {
            const scheduleElement = document.createElement('div');
            scheduleElement.className = 'schedule-item';
            scheduleElement.textContent = schedule.title;
            
            if (schedule.completed) {
                scheduleElement.classList.add('completed');
            }
            if (schedule.priority === 'high') {
                scheduleElement.classList.add('high-priority');
            } else if (schedule.priority === 'medium') {
                scheduleElement.classList.add('medium-priority');
            }
            
            scheduleElement.addEventListener('click', (e) => {
                e.stopPropagation();
                showScheduleDetail(schedule);
            });
            
            schedulesContainer.appendChild(scheduleElement);
        });
        
        if (daySchedules.length > 3) {
            const moreElement = document.createElement('div');
            moreElement.className = 'schedule-item';
            moreElement.textContent = `+${daySchedules.length - 3}개 더`;
            moreElement.style.background = '#95a5a6';
            schedulesContainer.appendChild(moreElement);
        }
        
        dayElement.appendChild(schedulesContainer);
        calendarDays.appendChild(dayElement);
    }
}

// 주간 달력 렌더링
function renderWeeklyCalendar() {
    const weekRangeElement = document.getElementById('current-week-range');
    const daysHeader = document.querySelector('.days-header');
    const daysGrid = document.querySelector('.days-grid');
    const timeSlots = document.querySelector('.time-slots');
    
    if (!weekRangeElement || !daysHeader || !daysGrid || !timeSlots) return;
    
    // 주간 범위 계산
    const startOfWeek = new Date(currentDate);
    startOfWeek.setDate(currentDate.getDate() - currentDate.getDay());
    const endOfWeek = new Date(startOfWeek);
    endOfWeek.setDate(startOfWeek.getDate() + 6);
    
    weekRangeElement.textContent = 
        `${formatDate(startOfWeek)} - ${formatDate(endOfWeek)}`;
    
    // 시간 슬롯 생성
    timeSlots.innerHTML = '';
    for (let hour = 0; hour < 24; hour++) {
        const timeSlot = document.createElement('div');
        timeSlot.className = 'time-slot';
        timeSlot.textContent = hour < 10 ? `0${hour}:00` : `${hour}:00`;
        timeSlots.appendChild(timeSlot);
    }
    
    // 요일 헤더 생성
    daysHeader.innerHTML = '';
    const dayNames = ['일', '월', '화', '수', '목', '금', '토'];
    for (let i = 0; i < 7; i++) {
        const dayDate = new Date(startOfWeek);
        dayDate.setDate(startOfWeek.getDate() + i);
        
        const dayHeader = document.createElement('div');
        dayHeader.className = 'day-header';
        
        const dayName = document.createElement('div');
        dayName.className = 'day-name';
        dayName.textContent = dayNames[i];
        
        const dayDateElement = document.createElement('div');
        dayDateElement.className = 'day-date';
        dayDateElement.textContent = dayDate.getDate();
        
        dayHeader.appendChild(dayName);
        dayHeader.appendChild(dayDateElement);
        daysHeader.appendChild(dayHeader);
    }
    
    // 날짜별 컬럼 생성
    daysGrid.innerHTML = '';
    for (let i = 0; i < 7; i++) {
        const dayColumn = document.createElement('div');
        dayColumn.className = 'day-column';
        
        // 24시간 슬롯 생성
        for (let hour = 0; hour < 24; hour++) {
            const hourSlot = document.createElement('div');
            hourSlot.className = 'hour-slot';
            dayColumn.appendChild(hourSlot);
        }
        
        // 해당 날짜의 일정들 배치
        const dayDate = new Date(startOfWeek);
        dayDate.setDate(startOfWeek.getDate() + i);
        const daySchedules = getSchedulesForDate(dayDate);
        
        daySchedules.forEach(schedule => {
            const scheduleElement = createWeeklyScheduleElement(schedule);
            if (scheduleElement) {
                dayColumn.appendChild(scheduleElement);
            }
        });
        
        daysGrid.appendChild(dayColumn);
    }
}

// 주간 달력용 일정 요소 생성
function createWeeklyScheduleElement(schedule) {
    const scheduleElement = document.createElement('div');
    scheduleElement.className = 'weekly-schedule-item';
    scheduleElement.textContent = schedule.title;
    
    if (schedule.completed) {
        scheduleElement.classList.add('completed');
    }
    if (schedule.priority === 'high') {
        scheduleElement.classList.add('high-priority');
    } else if (schedule.priority === 'medium') {
        scheduleElement.classList.add('medium-priority');
    }
    
    // 시간에 따른 위치 계산
    let startTime, endTime;
    if (schedule.due_time) {
        const dueTime = new Date(schedule.due_time);
        startTime = dueTime.getHours() + (dueTime.getMinutes() / 60);
        endTime = startTime + 1; // 기본 1시간
    } else if (schedule.date) {
        const date = new Date(schedule.date);
        startTime = date.getHours() + (date.getMinutes() / 60);
        endTime = startTime + 1;
    } else {
        startTime = 9; // 기본 오전 9시
        endTime = 10;
    }
    
    scheduleElement.style.top = `${startTime * 60}px`;
    scheduleElement.style.height = `${(endTime - startTime) * 60 - 2}px`;
    scheduleElement.style.left = '2px';
    scheduleElement.style.right = '2px';
    
    scheduleElement.addEventListener('click', () => {
        showScheduleDetail(schedule);
    });
    
    return scheduleElement;
}

// 특정 날짜의 일정 가져오기
function getSchedulesForDate(date) {
    const dateStr = date.toISOString().split('T')[0];
    return schedules.filter(schedule => {
        const scheduleDate = schedule.due_time || schedule.date;
        if (!scheduleDate) return false;
        return scheduleDate.split('T')[0] === dateStr;
    });
}

// 일정 상세 표시
function showScheduleDetail(schedule) {
    // 기존 main.js의 handleScheduleClick 함수 활용
    if (typeof handleScheduleClick === 'function') {
        handleScheduleClick(schedule);
    } else {
        alert(`제목: ${schedule.title}\n설명: ${schedule.description || '없음'}`);
    }
}

// 날짜 포맷팅
function formatDate(date) {
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    return `${year}.${month}.${day}`;
}

// 네비게이션 함수들
function goToPreviousMonth() {
    currentDate.setMonth(currentDate.getMonth() - 1);
    renderMonthCalendar();
}

function goToNextMonth() {
    currentDate.setMonth(currentDate.getMonth() + 1);
    renderMonthCalendar();
}

function goToPreviousWeek() {
    currentDate.setDate(currentDate.getDate() - 7);
    renderWeeklyCalendar();
}

function goToNextWeek() {
    currentDate.setDate(currentDate.getDate() + 7);
    renderWeeklyCalendar();
}

function goToToday() {
    currentDate = new Date();
    renderCurrentView();
}

// 뷰 전환
function switchView(view) {
    if (view === 'month') {
        window.location.href = '/static/calendar-monthly.html';
    } else if (view === 'week') {
        window.location.href = '/static/calendar-weekly.html';
    } else if (view === 'list') {
        window.location.href = '/static/index.html';
    }
}
```

## 수정 방법 요약

현재 프로젝트에 달력 화면을 추가하려면:

1. **HTML 파일 추가**:
   - `static/calendar-monthly.html` (월간 달력)
   - `static/calendar-weekly.html` (주간 달력)

2. **CSS 스타일 추가**:
   - `static/css/style.css`에 달력 관련 스타일 추가

3. **JavaScript 기능 추가**:
   - `static/js/calendar.js` 파일 생성

4. **기존 시스템과 연동**:
   - 현재 `/schedules/` API 활용
   - 기존 일정 데이터 구조 그대로 사용
   - 기존 모달 시스템 재활용

5. **네비게이션 추가**:
   - 기존 `index.html`에 달력 보기 버튼 추가
   - 달력 화면에서 목록 보기 버튼으로 돌아가기

이렇게 구현하면 기존 일정 관리 시스템과 완전히 통합된 달력 화면을 제공할 수 있습니다.
