// 달력 관련 전역 변수
let currentDate = new Date();
let currentView = 'month'; // 'month' 또는 'week'
// schedules 변수는 main.js에서 전역으로 선언되므로 여기서는 제거
// window.schedules를 사용하여 참조

// 달력 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 현재 페이지를 로컬 스토리지에 저장
    const currentPath = window.location.pathname;
    localStorage.setItem('lastPage', currentPath);

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
            // 로그인 페이지로 리다이렉트
            window.location.href = '/static/index.html';
            return;
        }
        
        //console.log('[TIME_DEBUG] Loading schedules from API...');
        const response = await fetch('/schedules/', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            window.schedules = data.schedules || data || [];
            
            //console.log(`[TIME_DEBUG] Loaded ${window.schedules.length} schedules`);
            // 처음 3개 스케줄의 시간 정보 로그
            window.schedules.slice(0, 3).forEach((schedule, index) => {
                //console.log(`[TIME_DEBUG] Schedule ${index + 1}: "${schedule.title}"`);
                //console.log(`[TIME_DEBUG] - date: ${schedule.date}`);
                //console.log(`[TIME_DEBUG] - due_time: ${schedule.due_time}`);
            });
            
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
        
        daySchedules.forEach(schedule => {
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
    
    // 시간에 따른 위치 계산 (로컬 시간대 기준)
    let startTime, endTime;
    if (schedule.due_time) {
        const dueTime = new Date(schedule.due_time);
        //console.log(`[TIME_DEBUG] Schedule "${schedule.title}": raw due_time: ${schedule.due_time}`);
        //console.log(`[TIME_DEBUG] Parsed due_time (local): ${dueTime}`);
        //console.log(`[TIME_DEBUG] Local Hours: ${dueTime.getHours()}, Minutes: ${dueTime.getMinutes()}`);
        startTime = dueTime.getHours() + (dueTime.getMinutes() / 60);
        endTime = startTime + 1; // 기본 1시간
    } else if (schedule.date) {
        const date = new Date(schedule.date);
        //console.log(`[TIME_DEBUG] Schedule "${schedule.title}": raw date: ${schedule.date}`);
        //console.log(`[TIME_DEBUG] Parsed date (local): ${date}`);
        //console.log(`[TIME_DEBUG] Local Hours: ${date.getHours()}, Minutes: ${date.getMinutes()}`);
        startTime = date.getHours() + (date.getMinutes() / 60);
        endTime = startTime + 1;
    } else {
        //console.log(`[TIME_DEBUG] Schedule "${schedule.title}": No time specified, using default 9-10`);
        startTime = 9; // 기본 오전 9시
        endTime = 10;
    }
    
    //console.log(`[TIME_DEBUG] Final time calculation for "${schedule.title}": startTime: ${startTime}, endTime: ${endTime}`);
    
    scheduleElement.style.top = `${startTime * 60}px`;
    scheduleElement.style.height = `${(endTime - startTime) * 60 - 2}px`;
    scheduleElement.style.left = '2px';
    scheduleElement.style.right = '2px';
    
    scheduleElement.addEventListener('click', () => {
        showScheduleDetail(schedule);
    });
    
    return scheduleElement;
}

// 특정 날짜의 일정들 가져오기
function getSchedulesForDate(date) {
    // 로컬 시간대를 유지하여 날짜 문자열 생성
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    const dateStr = `${year}-${month}-${day}`;
    
    //console.log(`[TIME_DEBUG] getSchedulesForDate called with date: ${date}`);
    //console.log(`[TIME_DEBUG] dateStr for comparison (local time): ${dateStr}`);
    
    const filteredSchedules = (window.schedules || []).filter(schedule => {
        // 스케줄의 날짜도 로컬 시간대를 유지하여 비교
        const scheduleDate = new Date(schedule.date);
        const scheduleYear = scheduleDate.getFullYear();
        const scheduleMonth = (scheduleDate.getMonth() + 1).toString().padStart(2, '0');
        const scheduleDay = scheduleDate.getDate().toString().padStart(2, '0');
        const scheduleDateStr = `${scheduleYear}-${scheduleMonth}-${scheduleDay}`;
        
        //console.log(`[TIME_DEBUG] Schedule "${schedule.title}": raw date: ${schedule.date}, local converted: ${scheduleDateStr}, matches: ${scheduleDateStr === dateStr}`);
        return scheduleDateStr === dateStr;
    });
    
    //console.log(`[TIME_DEBUG] Found ${filteredSchedules.length} schedules for date ${dateStr}`);
    return filteredSchedules;
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
    return `${year}-${month}-${day}`;
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
        window.location.href = '/static/entryScreen.html';
    }
} 