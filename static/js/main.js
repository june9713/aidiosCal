// 시간 처리를 일관되게 하기 위해 getCurrentTime 함수를 제거하고 new Date()를 직접 사용
// 서버에서 한국시간으로 처리되므로 클라이언트는 UTC 기준으로 일관되게 처리

// 현재 사용자 정보를 저장할 전역 변수
let currentUser = null;

// 현재 사용자 정보를 가져오는 함수
async function getCurrentUserInfo() {
    try {
        const token = localStorage.getItem('token');
        if (!token) {
            console.error('토큰이 없습니다.');
            return null;
        }
        
        const response = await fetch('/users/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const userData = await response.json();
            currentUser = userData;
            console.log('현재 사용자 정보:', currentUser);
            return userData;
        } else {
            console.error('사용자 정보 로드 실패:', response.status);
            return null;
        }
    } catch (error) {
        console.error('사용자 정보 로드 중 오류:', error);
        return null;
    }
}

// JWT 토큰 디코딩 유틸리티 함수 추가
function decodeJWTToken(token) {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        return JSON.parse(jsonPayload);
    } catch (error) {
        log('ERROR', 'Failed to decode JWT token', error);
        return null;
    }
}

// JWT 토큰 만료 확인 함수 (실제 토큰 기반)
function isJWTTokenExpired(token) {
    if (!token) return true;
    
    const decoded = decodeJWTToken(token);
    if (!decoded || !decoded.exp) return true;
    
    const now = Math.floor(Date.now() / 1000);
    const bufferTime = 5 * 60; // 5분 버퍼
    
    return (decoded.exp - bufferTime) <= now;
}

// 토큰이 곧 만료될 예정인지 확인 (자동 갱신 트리거용)
function shouldRefreshToken(token) {
    if (!token) return false;
    
    const decoded = decodeJWTToken(token);
    if (!decoded || !decoded.exp) return false;
    
    const now = Math.floor(Date.now() / 1000);
    const oneWeek = 7 * 24 * 60 * 60; // 7일을 초로 변환
    
    // 토큰이 1주일 이내에 만료되면 갱신 필요
    return (decoded.exp - oneWeek) <= now;
}

// API 요청 래퍼 함수 (자동 토큰 갱신 포함)
async function apiRequest(url, options = {}) {
    const token = localStorage.getItem('token');
    
    // 토큰이 없으면 로그인 필요
    if (!token) {
        clearSession();
        throw new Error('No token available');
    }
    
    // 토큰이 만료되었으면 갱신 시도
    if (isJWTTokenExpired(token)) {
        log('INFO', 'Token expired, attempting refresh');
        const refreshSuccess = await refreshToken();
        if (!refreshSuccess) {
            clearSession();
            throw new Error('Token refresh failed');
        }
    }
    
    // 기본 헤더 설정
    const defaultOptions = {
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json',
            ...options.headers
        },
        ...options
    };
    
    try {
        const response = await fetch(url, defaultOptions);
        
        // 401 에러 시 토큰 갱신 후 재시도
        if (response.status === 401) {
            log('INFO', '401 error, attempting token refresh');
            const refreshSuccess = await refreshToken();
            if (refreshSuccess) {
                // 새 토큰으로 재시도
                defaultOptions.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
                return await fetch(url, defaultOptions);
            } else {
                clearSession();
                throw new Error('Authentication failed');
            }
        }
        
        return response;
    } catch (error) {
        log('ERROR', 'API request failed', error);
        throw error;
    }
}

// 로깅 유틸리티 함수 수정
async function log(type, message, data = null) {
    const now = new Date();
    const timestamp = now.toISOString();
    const logMessage = `[${timestamp}] [${type}] ${message}`;
    
    switch(type) {
        case 'ERROR':
            console.error(logMessage, data || '');
            break;
        case 'WARN':
            console.warn(logMessage, data || '');
            break;
        case 'INFO':
            console.info(logMessage, data || '');
            break;
        case 'DEBUG':
            console.debug(logMessage, data || '');
            break;
        default:
            console.log(logMessage, data || '');
    }
}

// Global variables
window.currentUser = window.currentUser || null;
window.schedules = window.schedules || [];
let showCompleted = false;
let completedOnly = false; // 완료된 일정만 보기 상태
let selectedUsers = new Set();
let tokenRefreshInterval = null;
let currentPage = 1;
let isLoading = false;
let hasMoreSchedules = true;
const SCHEDULES_PER_PAGE = 50;

// DOM Elements
const authContainer = document.getElementById('auth-container');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const showRegisterLink = document.getElementById('show-register');
const showLoginLink = document.getElementById('show-login');

// 자동 새로고침 설정 함수
function setupAutoRefresh() {
    // 10초마다 일정 자동 새로고침
    setInterval(async () => {
        // 사용자가 로그인된 상태이고 auth-container가 숨겨진 상태(즉, 일정 화면이 보이는 상태)에서만 새로고침
        const authContainer = document.getElementById('auth-container');
        if (window.currentUser){//&& authContainer && authContainer.style.display === 'none') {
            log('DEBUG', '자동 새로고침 실행');
            await refreshSchedules();
        }
    }, 10000); // 10000ms = 10초
}

// Event Listeners
document.addEventListener('DOMContentLoaded', async () => {
    console.log("DOMContentLoaded 이벤트 발생");
    log('INFO', 'DOMContentLoaded 이벤트 발생');
    log('INFO', 'Application initialized');
    log('INFO', 'userData', localStorage.getItem('userData'));
    const currentUserData = JSON.parse(localStorage.getItem('userData'));
    log('INFO', 'currentUserData', currentUserData);

    // 자동 새로고침 설정
    setupAutoRefresh();
    
    const token = localStorage.getItem('token');
    const userData = localStorage.getItem('userData');
    
    log('DEBUG', '저장된 데이터 확인', { 
        hasToken: !!token, 
        hasUserData: !!userData,
        tokenLength: token ? token.length : 0
    });
    
    // JWT 토큰 만료 체크 (실제 토큰 기반)
    if (token && isJWTTokenExpired(token)) {
        //log('INFO', 'JWT Token expired, attempting refresh');
        const refreshSuccess = await refreshToken();
        if (!refreshSuccess) {
            log('INFO', 'Token refresh failed, clearing session');
            clearSession();
            return;
        }
    }
    
    if (token && userData) {
        log('DEBUG', 'Found stored token and user data');
        try {
            window.currentUser = JSON.parse(userData);
            log('DEBUG', 'Parsed user data', window.currentUser);
            console.log("Parsed user data window.currentUser", window.currentUser);
            
            // 토큰이 곧 만료될 예정이면 미리 갱신
            if (shouldRefreshToken(token)) {
                log('INFO', 'Token will expire soon, refreshing proactively');
                await refreshToken();
            }
            
            await fetchUserProfile();
            
            // 현재 사용자 정보 가져오기
            await getCurrentUserInfo();
            
            // 필터 상태 복원
            restoreUserFilterState();
            
            // 필터 상태 복원 후 일정 로드
            if (typeof main_loadSchedules === 'function') {
                await main_loadSchedules(1, false);
            }
        } catch (error) {
            log('ERROR', 'Failed to parse stored user data', error);
            clearSession();
        }
    } else {
        log('INFO', 'No stored session found - showing login form');
    }

    if (loginForm) loginForm.addEventListener('submit', handleLogin);
    if (registerForm) registerForm.addEventListener('submit', handleRegister);
    
    if (showRegisterLink) {
        showRegisterLink.addEventListener('click', (e) => {
            e.preventDefault();
            if(loginForm) loginForm.style.display = 'none';
            if(registerForm) registerForm.style.display = 'block';
        });
    }
    
    if (showLoginLink) {
        showLoginLink.addEventListener('click', (e) => {
            e.preventDefault();
            if(registerForm) registerForm.style.display = 'none';
            if(loginForm) loginForm.style.display = 'block';
        });
    }
});

// Session Management Functions (개선된 버전)
function isTokenExpired() {
    const token = localStorage.getItem('token');
    // JWT 토큰 기반 검사를 우선 사용
    if (token) {
        return isJWTTokenExpired(token);
    }
    
    // 토큰이 없으면 만료된 것으로 간주
    return true;
}

function clearSession() {
    log('INFO', 'clearSession 시작');
    localStorage.removeItem('token');
    localStorage.removeItem('userData');
    localStorage.removeItem('tokenCreatedAt'); // 토큰 생성 시간도 삭제
    localStorage.removeItem('lastPage'); // 마지막 페이지 정보도 삭제
    window.currentUser = null;
    if (tokenRefreshInterval) {
        clearInterval(tokenRefreshInterval);
        tokenRefreshInterval = null;
    }
    stopAlarmPolling(); // 알람 폴링 중지
    window.location.reload();
}

function logout() {
    if (confirm('로그아웃 하시겠습니까?')) {
        clearSession();
    }
}

// handleLogout 함수 추가 (logout 함수의 별칭)
function handleLogout() {
    logout();
}

function startTokenRefresh() {
    log('INFO', 'Starting token refresh interval');
    if (tokenRefreshInterval) clearInterval(tokenRefreshInterval);
    // 6시간마다 토큰 갱신 체크 (24시간에서 단축)
    tokenRefreshInterval = setInterval(async () => {
        const token = localStorage.getItem('token');
        if (token && shouldRefreshToken(token)) {
            await refreshToken();
        }
    }, 6 * 60 * 60 * 1000); // 6시간마다
}

async function refreshToken() {
    const token = localStorage.getItem('token');
    if (!token) {
        log('WARN', 'No token found for refresh');
        return false;
    }
    
    try {
        const response = await fetch('/token/refresh', {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${token}`, 
                'Content-Type': 'application/json' 
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('tokenCreatedAt', Date.now().toString());
            log('INFO', 'Token refreshed successfully');
            return true;
        } else {
            log('ERROR', 'Token refresh failed', { status: response.status });
            if (response.status === 401) {
                // 리프레시 토큰도 만료된 경우
                clearSession();
            }
            return false;
        }
    } catch (error) {
        log('ERROR', 'Token refresh error', error);
        return false;
    }
}

async function fetchUserProfile() {
    const token = localStorage.getItem('token');
    log('DEBUG', 'fetchUserProfile 시작', { token: token ? 'exists' : 'missing' });
    
    if (!token) { 
        clearSession(); 
        return; 
    }
    
    try {
        const response = await apiRequest('/users/me');
        
        if (response.ok) {
            const userData = await response.json();
            currentUser = userData;
            localStorage.setItem('userData', JSON.stringify(currentUser));
            showScheduleInterface();
            startTokenRefresh();
            startAlarmPolling(); // 알람 폴링 시작
        } else if (response.status === 401) {
            log('ERROR', 'Unauthorized in fetchUserProfile');
            clearSession();
        } else {
            log('ERROR', 'Failed to fetch user profile', { status: response.status });
            clearSession();
        }
    } catch (error) {
        log('ERROR', 'Network or other error in fetchUserProfile', error);
        clearSession();
    }
}


// Authentication Functions
async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        const response = await fetch('/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
        });

        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('username', username);
            localStorage.setItem('tokenCreatedAt', Date.now().toString()); // 토큰 생성 시간 저장 추가
            await fetchUserProfile(); // 토큰 파라미터 제거
            
            // 현재 사용자 정보 가져오기
            await getCurrentUserInfo();
            
            // 로그인 성공 시 lastPage 초기화 후 루트 경로로 리다이렉트
            localStorage.removeItem('lastPage');  // 기존 마지막 페이지 정보 제거
            window.location.href = '/';  // 루트 경로로 리다이렉트 (세션 확인 후 적절한 페이지로 이동)
        } else {
            const error = await response.json();
            alert(error.detail || '로그인에 실패했습니다.');
        }
    } catch (error) {
        console.error('로그인 중 오류 발생:', error);
        alert('로그인 중 오류가 발생했습니다.');
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const username = document.getElementById('reg-username').value;
    const name = document.getElementById('reg-name').value;
    const password = document.getElementById('reg-password').value;
    const confirmPassword = document.getElementById('reg-confirm-password').value;

    if (!username || !name || !password || !confirmPassword) {
        alert('모든 필드를 입력해주세요.'); return;
    }
    if (password !== confirmPassword) {
        alert('비밀번호가 일치하지 않습니다.'); return;
    }
    try {
        const payload = { username, name, password };
        const response = await fetch('/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (response.ok) {
            alert('회원가입이 완료되었습니다. 로그인해주세요.');
            showLoginForm();
        } else {
            const errorData = await response.json();
            // ... (error handling as before)
            if (response.status === 422) {
                log('ERROR', 'Registration validation failed', errorData);
                const errorMessages = errorData.detail.map(
                    err => `[${err.loc ? err.loc.join('.') : ''}] ${err.msg}`
                );
                alert(`입력값이 올바르지 않습니다:\n${errorMessages.join('\n')}`);
            } else {
                log('ERROR', 'Registration failed', { status: response.status, error: errorData });
                alert(errorData.detail || '회원가입 중 오류가 발생했습니다.');
            }
        }
    } catch (error) {
        log('ERROR', 'Registration error', error);
        alert('회원가입 중 오류가 발생했습니다.');
    }
}

function showLoginForm() {
    if(registerForm) registerForm.style.display = 'none';
    if(loginForm) loginForm.style.display = 'block';
}



function setupInfiniteScroll() {
    const scheduleContainer = document.getElementById('schedule-container');
    if (!scheduleContainer) return;
    scheduleContainer.addEventListener('scroll', async () => {
        const { scrollTop, scrollHeight, clientHeight } = scheduleContainer;
        if (scrollTop + clientHeight >= scrollHeight * 0.9 && hasMoreSchedules && !isLoading) {
            currentPage++;
            showLoadingIndicator(true);
            await main_loadSchedules(currentPage, true); // append = true
            showLoadingIndicator(false);
        }
    });
}

function showLoadingIndicator(show) {
    const indicator = document.getElementById('loading-indicator');
    if (indicator) indicator.style.display = show ? 'inline' : 'none';
}

function updateScheduleCount() {
    return;
    const countElement = document.getElementById('schedule-count');
    if (countElement) {
        const visibleSchedules = window.schedules.filter(s => {
            if (!showCompleted && s.is_completed && !completedOnly) return false;
            if (completedOnly && !s.is_completed) return false;
            if (selectedUsers.size > 0 && !selectedUsers.has(s.owner_id)) return false;
            return true;
        });
        countElement.textContent = `표시: ${visibleSchedules.length}개 / 전체: ${window.schedules.length}개 (DB)`;
    }
}

async function refreshSchedules() {
    log('DEBUG', 'refreshSchedules 시작');
    currentPage = 1;
    hasMoreSchedules = true; // 더 많은 스케줄이 있을 수 있다고 가정
    // schedules = []; // 바로 비우지 않고, main_loadSchedules에서 append=false로 처리
    await main_loadSchedules(1, false); // append = false
}

function updateToggleCompletedButtonText() {
    const button = document.querySelector('.controls button:first-child');
    if (!button) return;
    if (completedOnly) {
        button.textContent = '진행 일정 보기';
    } else if (!showCompleted) {
        button.textContent = '완료 일정만 보기';
    } else {
        button.textContent = '완료 일정 숨기기';
    }
}

function toggleCompletedFilter() {
    if (showCompleted) { // 현재: 완료일정 숨기기 버튼 (모든 일정 표시 중)
        showCompleted = false;
    
    } 
    else { // 현재: 완료 일정만 보기 버튼 (진행 일정만 표시 중 - !showCompleted)
        showCompleted = true; 
    }
    updateToggleCompletedButtonText();
    refreshSchedules();
}


function toggleFileView() {
    // fileviewer.html로 리다이렉트
    window.location.href = '/static/fileviewer.html';
}

async function showFileView() {
    const container = document.querySelector('.schedule-container');
    if (!container) return;
    
    const scheduleTable = container.querySelector('.schedule-table');
    if (scheduleTable) scheduleTable.style.display = 'none';

    let fileListView = container.querySelector('.file-list-view');
    if (!fileListView) {
        fileListView = document.createElement('div');
        fileListView.className = 'file-list-view'; // 새 클래스 이름
        fileListView.innerHTML = `<div class="file-list" id="file-list-main"></div>`; // ID 변경
        container.appendChild(fileListView);
    }
    fileListView.style.display = 'block';
    await loadFilesForMainView(); // 새 함수 호출
}

async function loadFilesForMainView() { // 새 함수
    try {
        // API 엔드포인트 수정: /attachments/ 사용
        const response = await apiRequest('/attachments/');
        if (response.ok) {
            const files = await response.json();
            renderFilesForMainView(files); // 새 함수 호출
        } else {
            log('ERROR', 'Failed to load files for main view', {status: response.status});
            const fileListMain = document.getElementById('file-list-main');
            if(fileListMain) fileListMain.innerHTML = '<p class="no-files">파일 목록을 불러오는데 실패했습니다.</p>';
        }
    } catch (error) {
        log('ERROR', 'File load error for main view', error);
        const fileListMain = document.getElementById('file-list-main');
        if(fileListMain) fileListMain.innerHTML = '<p class="no-files">파일 목록 로딩 중 오류 발생.</p>';
    }
}

function renderFilesForMainView(files) { // 새 함수
    const fileListMain = document.getElementById('file-list-main');
    if (!fileListMain) return;
    fileListMain.innerHTML = '';
    if (files.length === 0) {
        fileListMain.innerHTML = '<p class="no-files">첨부된 파일이 없습니다.</p>';
        return;
    }
    files.forEach(file => {
        const li = document.createElement('li');
        li.className = 'file-item';
        const fileCreatedDate = new Date(file.created_at);
        const year = fileCreatedDate.getFullYear();
        const month = (fileCreatedDate.getMonth() + 1).toString().padStart(2, '0');
        const day = fileCreatedDate.getDate().toString().padStart(2, '0');
        const hours = fileCreatedDate.getHours().toString().padStart(2, '0');
        const minutes = fileCreatedDate.getMinutes().toString().padStart(2, '0');
        const createdDate = `${year}-${month}-${day} ${hours}:${minutes}`;
        const thumbnailHtml = createFileThumbnail(file.filename, file.file_path, file.mime_type);
        
        li.innerHTML = `
            ${thumbnailHtml}
            <div class="file-info">
                <span class="file-name">${file.filename}</span>
                <span class="file-type">${getFileExtension(file.filename).toUpperCase()}</span>
                <span class="file-size">${formatFileSize(file.file_size || 0)}</span>
                <span class="file-date">${createdDate}</span>
                ${file.schedule_title ? `<span class="file-schedule">관련 일정: ${file.schedule_title}</span>` : ''}
            </div>
            <div class="file-actions">
                <button onclick="downloadFile('${file.file_path}')">다운로드</button>
                <button onclick="deleteFileFromMainView(${file.id})">삭제</button> 
            </div>
        `;
        fileListMain.appendChild(li);
    });
}

async function deleteFileFromMainView(fileId) { // 새 함수
    if (!confirm('정말로 이 파일을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) return;
    
    try {
        const response = await apiRequest(`/attachments/${fileId}`, {
            method: 'DELETE'
        });
        if (response.ok) {
            await loadFilesForMainView(); // 파일 목록 새로고침
        } else {
            const error = await response.json();
            log('ERROR', 'Failed to delete file from main view', error);
            alert(error.detail || '파일 삭제에 실패했습니다.');
        }
    } catch (error) {
        log('ERROR', 'File delete error from main view', error);
        alert('파일 삭제 중 오류가 발생했습니다.');
    }
}


async function main_loadSchedules(page = 1, append = false) {
    console.log("main_loadSchedules start");
    if (isLoading && append) return; // 추가 로드 중이면 중복 방지
    isLoading = true;
    showLoadingIndicator(true);

    const params = new URLSearchParams({
        skip: (page - 1) * SCHEDULES_PER_PAGE,
        limit: SCHEDULES_PER_PAGE,
    });
    // 필터링 조건 추가
    if (completedOnly) {
        params.append('completed_only', 'true');
    } else {
        params.append('show_completed', showCompleted.toString());
    }

    if (selectedUsers.size > 0) {
        // 백엔드에서 선택된 사용자의 일정 + 해당 사용자가 공동작업자인 일정을 모두 반환
        selectedUsers.forEach(userId => params.append('user_ids', userId));
        console.log('🔍 [FRONTEND_DEBUG] 선택된 사용자들:', Array.from(selectedUsers));
    }
    
    console.log('🔍 [FRONTEND_DEBUG] 최종 요청 파라미터:', params.toString());
    console.log('🔍 [FRONTEND_DEBUG] show_all_users 파라미터 전송 여부:', params.has('show_all_users'));
    log('DEBUG', `Requesting schedules from: /schedules/?${params.toString()}`);

    try {
        const response = await apiRequest(`/schedules/?${params.toString()}`);
        //console.log('🔍 [FRONTEND_DEBUG] 응답 상태:', response.status);
        
        if (response.ok) {
            const data = await response.json(); // FastAPI가 객체 {schedules: [], total_count: N}를 반환한다고 가정
            const newSchedules = data.schedules || (Array.isArray(data) ? data : []); // 호환성
            
            //console.log('🔍 [FRONTEND_DEBUG] 받은 데이터:', data);
            //console.log('🔍 [FRONTEND_DEBUG] 파싱된 일정 수:', newSchedules.length);
            //console.log('🔍 [FRONTEND_DEBUG] 첫 번째 일정:', newSchedules[0]);
            
            if (append) {
                window.schedules = window.schedules.concat(newSchedules);
            } else {
                window.schedules = newSchedules;
            }
            hasMoreSchedules = newSchedules.length === SCHEDULES_PER_PAGE;
            renderSchedules();
        } else if (response.status === 401) {
            clearSession();
        } else {
            log('ERROR', 'Failed to load schedules', {status: response.status});
        }
    } catch (error) {
        log('ERROR', 'Network or other error in main_loadSchedules', error);
    } finally {
        isLoading = false;
        showLoadingIndicator(false);
        updateScheduleCount();
    }
}

function renderSchedules() {
    const tbody = document.getElementById('schedule-body');
    if (!tbody) return;

    const fragment = document.createDocumentFragment();
    
    // 오늘 날짜 확인 - 한국시간 기준으로 처리
    const today = new Date();
    //const koreaTimeOffset = 9 * 60 * 60 * 1000; // 9시간을 밀리초로
    //const koreaToday = new Date(today.getTime() );
    const todayString = formatDateToMonthDay(today.toISOString());
    
    console.log("todayString", todayString);
    let hasTodaySchedule = false;

    // 필터링된 일정들을 수집
    const filteredSchedules = [];
    window.schedules.forEach(schedule => {
        // 클라이언트 사이드 필터링 (선택 사항, 백엔드 필터링이 주력)
        if (completedOnly && !schedule.is_completed) return;
        if (!showCompleted && schedule.is_completed && !completedOnly) return;
        // 백엔드에서 이미 선택된 사용자의 일정과 해당 사용자가 공동작업자인 일정을 모두 보내주므로
        // 프론트엔드에서 추가 필터링할 필요가 없음
        // 기존 코드: if (selectedUsers.size > 0 && !selectedUsers.has(schedule.owner_id)) return;
        if (selectedUsers.size > 0) {
            ;//console.log('🔍 [FRONTEND_DEBUG] 사용자 필터 적용됨 - 백엔드에서 이미 필터링된 데이터를 받음');
        }
        
        filteredSchedules.push(schedule);
        
        // 오늘 날짜 일정이 있는지 확인
        const scheduleDateString = schedule.due_time ? formatDateToMonthDay(schedule.due_time) : '';
        if (scheduleDateString === todayString) {
            hasTodaySchedule = true;
        }
    });

    // 날짜순으로 정렬 (due_time 기준)
    filteredSchedules.sort((a, b) => {
        const dateA = a.due_time ? new Date(a.due_time) : new Date(0);
        const dateB = b.due_time ? new Date(b.due_time) : new Date(0);
        return dateA - dateB;
    });

    // 더미 행이 삽입될 위치 찾기
    let dummyInserted = false;
    
    // 오늘 날짜를 Date 객체로 변환 (한국시간 기준)
    const koreaTimeOffset = 9 * 60 * 60 * 1000; // 9시간을 밀리초로
    const koreaToday = new Date(today.getTime() + koreaTimeOffset);
    const todayDate = new Date(koreaToday.getFullYear(), koreaToday.getMonth(), koreaToday.getDate());
    
    filteredSchedules.forEach((schedule, index) => {
        // 더미 행을 적절한 위치에 삽입
        if (!hasTodaySchedule && !dummyInserted) {
            const scheduleDate = schedule.due_time ? new Date(schedule.due_time) : null;
            
            if (scheduleDate) {
                // 일정 날짜를 한국 시간 기준으로 변환
                const scheduleKoreaDate = new Date(scheduleDate.getTime() + koreaTimeOffset);
                const scheduleDateOnly = new Date(scheduleKoreaDate.getFullYear(), scheduleKoreaDate.getMonth(), scheduleKoreaDate.getDate());
                
                // 현재 일정의 날짜가 오늘보다 나중이면, 이 위치에 더미 행 삽입
                if (scheduleDateOnly > todayDate) {
                    const dummyTr = createTodayDummyRow(todayString);
                    fragment.appendChild(dummyTr);
                    dummyInserted = true;
                }
            }
        }

        // 일반 일정 행 생성
        const tr = createScheduleRow(schedule, todayString);
        fragment.appendChild(tr);
        
        // 메모가 있는 경우 자식 라인 추가
        if (schedule.memo && schedule.memo.trim()) {
            const memoLines = schedule.memo.split('\n').filter(line => line.trim());
            memoLines.forEach((memoLine, memoIndex) => {
                const memoTr = createMemoRow(schedule, memoLine, memoIndex + 1);
                fragment.appendChild(memoTr);
            });
        }
    });

    // 모든 일정이 오늘보다 이전 날짜이거나 일정이 없는 경우, 마지막에 더미 행 추가
    if (!hasTodaySchedule && !dummyInserted) {
        const dummyTr = createTodayDummyRow(todayString);
        fragment.appendChild(dummyTr);
    }
    
    tbody.innerHTML = ''; // 기존 내용 삭제
    tbody.appendChild(fragment);
    updateScheduleCount();
}

// 오늘 더미 행을 생성하는 별도 함수
function createTodayDummyRow(todayString) {
    const dummyTr = document.createElement('tr');
    dummyTr.className = 'today-dummy-row';
    dummyTr.style.fontStyle = 'italic';
    dummyTr.style.opacity = '0.7';
    dummyTr.style.border = '1px solid #007bff';
    dummyTr.style.borderRadius = '1px';
    dummyTr.style.backgroundColor = 'rgb(154, 180, 209)';
    dummyTr.style.fontWeight = 'bold';
    
    dummyTr.innerHTML = `
        <td data-label="날짜" >${todayString}</td>
        <td data-label="작성자"></td>
        <td data-label="프로젝트">오늘</td>
        <td data-label="제목">오늘 등록된 일정이 없습니다</td>
    `;
    
    return dummyTr;
}

// 메모 행을 생성하는 함수
function createMemoRow(schedule, memoLine, memoIndex) {
    const tr = document.createElement('tr');
    tr.className = 'memo-row';
    tr.dataset.scheduleId = schedule.id;
    tr.dataset.memoIndex = memoIndex;
    
    // 메모 행 스타일 설정
    tr.style.backgroundColor = '#f8f9fa';
    tr.style.fontSize = '0.9em';
    tr.style.color = '#6c757d';
    tr.style.borderLeft = '3px solid #007bff';
    
    // 작성자, 프로젝트, 제목을 모두 merge하여 작성자 칸부터 표시
    const memoContent = `📝 ${memoLine}`;
    
    tr.innerHTML = `
        <td data-label="날짜"></td>
        <td data-label="작성자" colspan="3" style="padding-left: 20px;">
            ${memoContent}
        </td>
    `;
    
    // 메모 행 클릭 시 부모 스케줄 상세보기
    tr.addEventListener('click', () => handleScheduleClick(schedule));
    
    return tr;
}

// 일정 행을 생성하는 별도 함수
function createScheduleRow(schedule, todayString) {
    const tr = document.createElement('tr');
    tr.className = schedule.is_completed ? 'completed' : '';
    tr.dataset.scheduleId = schedule.id; // data-schedule-id 속성 추가
    
    const priorityClassMap = { '긴급': 'priority-urgent', '급함': 'priority-high', '곧임박': 'priority-medium', '일반': 'priority-low', '거북이': 'priority-turtle'};
    if (!schedule.is_completed && schedule.priority) {
        tr.classList.add(priorityClassMap[schedule.priority] || 'priority-low');
    }

    const dueTime = schedule.due_time ? new Date(schedule.due_time) : null;
    const now = new Date();
    const koreaTimeOffset = 9 * 60 * 60 * 1000;
    const koreaNow = new Date(now.getTime() + koreaTimeOffset);
    if (dueTime && dueTime < koreaNow && !schedule.is_completed) {
        tr.classList.add('overdue');
    }
    
    function formatPriorityIcon(priority) {
        return priority === '거북이' ? '🐢' : (priorityMap[priority] || priority || '');
    }
    const priorityMap = {'긴급':'🔥', '급함':'❗', '곧임박':'⚠️', '일반':'✉️', '거북이':'🐢'};

    // parent_order가 있으면 제목 앞에 추가
    const titlePrefix = typeof schedule.parent_order !== 'undefined' ? `(${schedule.parent_order}) ` : '';
    // 개인일정인 경우 🔒 아이콘 추가
    const individualIcon = schedule.individual ? '🔒 ' : '';
    const displayTitle = `${titlePrefix}${individualIcon}${schedule.title}`;

    // 일정의 날짜 포맷팅
    const scheduleDateString = schedule.due_time ? formatDateToMonthDay(schedule.due_time) : '';
    
    // 오늘 날짜인지 확인
    const isToday = scheduleDateString === todayString;

    // 공동작업자 배경색 적용 여부 확인
    let isCollaboratorAuthor = false;
    if (selectedUsers.size === 1) {
        // 1명만 선택된 경우에만 공동작업자 배경색 적용
        const selectedUserId = Array.from(selectedUsers)[0];
        const isSelectedUserSchedule = schedule.owner_id === selectedUserId;
        const isCollaboratorSchedule = schedule.shares && schedule.shares.some(share => share.shared_with_id === selectedUserId);
        
        // 선택된 사용자가 소유한 일정이 아니지만, 공동작업자로 포함된 일정인 경우
        if (!isSelectedUserSchedule && isCollaboratorSchedule) {
            isCollaboratorAuthor = true;
        }
    }

    // 날짜는 마감시간으로 표시
    tr.innerHTML = `
        <td data-label="날짜" ${isToday ? 'style=" background-color:rgb(148, 210, 255);"' : ''}>${isToday ? '오늘' : scheduleDateString}</td>
        <td data-label="작성자" id="author-${schedule.id}" class="${isCollaboratorAuthor ? 'collaborator-author' : ''}">${schedule.owner ? schedule.owner.name : '알수없음'}</td>
        <td data-label="프로젝트">${schedule.project_name || '일정'}</td>
        <td data-label="제목">${formatPriorityIcon(schedule.priority)} ${displayTitle}</td>
    `;
    
    // 작성자가 본인인지 확인하고 스타일 적용
    if (currentUser && schedule.owner && schedule.owner.name === currentUser.name) {
        const authorCell = tr.querySelector(`#author-${schedule.id}`);
        if (authorCell) {
            authorCell.classList.add('my-schedule-author');
        }
    }
    
    tr.addEventListener('click', () => handleScheduleClick(schedule)); // 변경된 함수 호출
    
    // 컨텍스트 메뉴 (우클릭 또는 길게 누르기)
    tr.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        showContextMenu(e, schedule);
    });
    // (터치 이벤트 리스너 추가 필요)
    let touchTimer;
    tr.addEventListener('touchstart', (e) => {
        touchTimer = setTimeout(() => {
            e.preventDefault(); // 기본 동작 방지 (예: 텍스트 선택)
            showContextMenu(e.touches[0], schedule);
        }, 700); // 700ms 길게 터치
    });
    tr.addEventListener('touchend', () => clearTimeout(touchTimer));
    tr.addEventListener('touchmove', () => clearTimeout(touchTimer));

    return tr;
}

// 메모 행을 생성하는 함수 (자식 라인)
function createMemoRow(schedule, memoLine, memoIndex) {
    const tr = document.createElement('tr');
    tr.className = 'memo-row';
    tr.dataset.scheduleId = schedule.id;
    tr.dataset.memoIndex = memoIndex;
    
    // 작성자, 프로젝트, 제목을 모두 merge하여 작성자 칸부터 표시
    const memoContent = `-->📝 ${memoLine}`;
    
    tr.innerHTML = `
        <td data-label="날짜"></td>
        <td data-label="작성자" colspan="3" style="padding-left: 20px;">
            ${memoContent}
        </td>
    `;
    
    // 메모 행 클릭 시 부모 스케줄 상세보기
    tr.addEventListener('click', () => handleScheduleClick(schedule));
    
    return tr;
}

// 전역에서 사용할 수 있도록 formatDateToMonthDay 함수를 별도로 정의
function formatDateToMonthDay(dateStr) {
    if (!dateStr) {
        return '';
    }
    const date = new Date(dateStr);
    const year = date.getFullYear(); // 4자리 연도로 변경
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    //console.log("year", year , "month", month, "day", day, "hours", hours, "minutes", minutes, "seconds", seconds);
    // 요일 배열
    const weekDays = ['일', '월', '화', '수', '목', '금', '토'];
    const dayOfWeek = weekDays[date.getDay()];
    
    const result = `${year}-${month}-${day}(${dayOfWeek})`;
    return result;
}

function showContextMenu(event, schedule) {
    hideContextMenu(); // 기존 메뉴 제거
    const menu = document.createElement('div');
    menu.className = 'context-menu';
    menu.innerHTML = `
        <div class="context-menu-item" onclick="showMemoPopup(${schedule.id})">메모추가/수정</div>
        <div class="context-menu-item" onclick="requestCompletion(${schedule.id})">완료 요청</div>
        <div class="context-menu-item" onclick="handleScheduleClick(${JSON.stringify(schedule).replace(/"/g, '&quot;')})">상세보기/수정</div>
    `;

    document.body.appendChild(menu);
    const menuWidth = menu.offsetWidth;
    const menuHeight = menu.offsetHeight;
    let x = event.clientX || event.pageX;
    let y = event.clientY || event.pageY;

    if (x + menuWidth > window.innerWidth) {
        x = window.innerWidth - menuWidth - 5;
    }
    if (y + menuHeight > window.innerHeight) {
        y = window.innerHeight - menuHeight - 5;
    }
    menu.style.left = `${x}px`;
    menu.style.top = `${y}px`;
    
    // 모바일 터치 이벤트 처리 개선
    menu.addEventListener('touchstart', (e) => {
        e.stopPropagation(); // 이벤트 전파 중단
    }, { passive: false });
    
    // 메뉴 아이템에 대한 터치 이벤트 처리
    const menuItems = menu.querySelectorAll('.context-menu-item');
    menuItems.forEach(item => {
        item.addEventListener('touchstart', (e) => {
            e.stopPropagation();
        }, { passive: false });
    });
    
    // 메뉴 외부 터치 시 메뉴 닫기
    setTimeout(() => {
        document.addEventListener('touchstart', hideContextMenu, { once: true });
    }, 0);
}

function hideContextMenu() {
    const menu = document.querySelector('.context-menu');
    if (menu) menu.remove();
    document.removeEventListener('click', hideContextMenu);
    document.removeEventListener('touchstart', hideContextMenu);
}


async function requestCompletion(scheduleId) {
    const token = localStorage.getItem('token');
    if (!token) return;
    try {
        const response = await fetch(`/schedules/${scheduleId}/request-completion`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
        });
        if (response.ok) {
            alert('완료 요청이 전송되었습니다.');
        } else if (response.status === 404 ) { // FastAPI에서 해당 기능 미구현 시 404 반환 가정
            alert('완료 요청 기능이 아직 지원되지 않습니다.');
        } else {
            const error = await response.json();
            alert(error.detail || '완료 요청 전송에 실패했습니다.');
        }
    } catch (error) {
        log('ERROR', 'Request completion error', error);
        alert('완료 요청 중 오류가 발생했습니다.');
    }
    hideContextMenu();
}


// --- MODAL RELATED FUNCTIONS ---
// Replaces showScheduleDetail, creates structure expected by editSchedule
function handleScheduleClick(schedule) {
    closeScheduleModal(); // Close any existing modal
 
    const modal = document.createElement('div');
    modal.className = 'schedule-modal';
    modal.dataset.scheduleId = schedule.id; // For deleteAttachment
    if (typeof schedule.parent_order !== 'undefined') {
        modal.dataset.parentOrder = schedule.parent_order;
    }
 
    // 부모 일정 정보 저장
    window.lastParentTitle = schedule.title;
    window.lastParentContent = schedule.content;
    window.lastParentProjectName = schedule.project_name;
    window.lastParentPriority = schedule.priority;
    window.lastParentDueTime = schedule.due_time; // 부모 일정의 마감시간 저장
 
    function formatDateModal(dateStr) {
        if (!dateStr) return '없음';
        const date = new Date(dateStr);
        const year = date.getFullYear();
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const day = date.getDate().toString().padStart(2, '0');
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        const seconds = date.getSeconds().toString().padStart(2, '0');
        
        return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
    }

    // 공동작업자 정보 렌더링 함수
    function renderCollaboratorsFromShares(shares) {
        if (!shares || shares.length === 0) {
            return '<span class="no-collaborators">공동작업자가 없습니다</span>';
        }
        
        const collaboratorsHtml = shares.map(share => {
            const permissions = [];
            if (share.can_edit) permissions.push('✏️ 수정');
            if (share.can_delete) permissions.push('🗑️ 삭제');
            if (share.can_complete) permissions.push('✅ 완료');
            if (share.can_share) permissions.push('📤 공유');
            
            const permissionsText = permissions.length > 0 ? permissions.join(' ') : '권한 없음';
            
            // shared_with 정보가 있는 경우 사용, 없으면 기본값 사용
            const collaboratorName = share.shared_with ? 
                (share.shared_with.name || share.shared_with.username || '알 수 없음') : 
                '알 수 없음';
            
            return `
                <div class="collaborator-item">
                    <span class="collaborator-name">${collaboratorName}</span>
                    <span class="collaborator-role">${share.role || '협업자'}</span>
                    <span class="collaborator-permissions">${permissionsText}</span>
                </div>
            `;
        }).join('');
        
        return collaboratorsHtml;
    }
 
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2>${schedule.title}</h2>
                <button onclick="closeDetail()" class="close-button">×</button>
            </div>
            <div class="modal-body">
                <div class="schedule-detail">
                    <div class="schedule-info-table">
                        <div class="schedule-info-label">프로젝트명</div>
                        <div class="schedule-info-value">${schedule.project_name || '일정'}</div>
                        <div class="schedule-info-label">일정명</div>
                        <div class="schedule-info-value">${schedule.title || '일정'}</div>
                        <div class="schedule-info-label">작성자</div>
                        <div class="schedule-info-value">${schedule.owner ? schedule.owner.name : '알 수 없음'}</div>
                        
                        <div class="schedule-info-label">공동작업자</div>
                        <div class="schedule-info-value" id="collaborators-list">
                            ${renderCollaboratorsFromShares(schedule.shares)}
                        </div>
                        
                        <div class="schedule-info-label">부모작업</div>
                        <div class="schedule-info-value">
                            ${schedule.parent ? schedule.parent.title : '없음'}
                        </div>
                        
                        <div class="schedule-info-label">우선순위</div>
                        <div class="schedule-info-value">
                            <span class="priority-display priority-${schedule.priority || 'none'}">
                                ${schedule.priority || '없음'}
                            </span>
                        </div>
                        
                        <div class="schedule-info-label">마감시간</div>
                        <div class="schedule-info-value">${formatDateModal(schedule.due_time)}</div>
                        
                        <div class="schedule-info-label">알람시간</div>
                        <div class="schedule-info-value">${formatDateModal(schedule.alarm_time)}</div>
                        
                        <div class="schedule-info-label">상태</div>
                        <div class="schedule-info-value">
                            <span class="${schedule.is_completed ? 'status-completed' : 'status-pending'}">
                                ${schedule.is_completed ? '완료' : '미완료'}
                            </span>
                        </div>
                        
                        <div class="schedule-info-label">개인일정</div>
                        <div class="schedule-info-value">
                            <span class="${schedule.individual ? 'individual-yes' : 'individual-no'}">
                                ${schedule.individual ? '🔒 개인일정' : '공개일정'}
                            </span>
                        </div>
                        
                        <div class="schedule-info-label">내용</div>
                        <div class="schedule-info-value">
                            <div class="schedule-content-display">
                                ${schedule.content ? schedule.content.replace(/\n/g, '<br>') : '없음'}
                            </div>
                        </div>
                    </div>
                    
                    <div class="attachments-section">
                        <div class="attachments-header">첨부 파일</div>
                        <div class="file-upload">
                            <input type="file" id="modal-file-upload" multiple>
                            <button onclick="uploadFilesToSchedule(${schedule.id})">업로드</button>
                        </div>
                        
                    </div>
                    
                    ${window.currentUser ? `
                    <div class="schedule-actions">
                        ${(window.currentUser.role === 'admin' || (schedule.owner && window.currentUser.id === schedule.owner.id)) ? `
                            <button onclick="editSchedule(${schedule.id})">수정</button>
                            <button onclick="shareSchedule(${schedule.id})">공유</button>
                            <button onclick="toggleComplete(${schedule.id}, ${!schedule.is_completed})">
                                ${schedule.is_completed ? '미완료로' : '완료로'}
                            </button>
                            <button onclick="deleteSchedule(${schedule.id})" class="clear-all-btn">삭제</button>
                            <button onclick="main_createChildSchedule(${schedule.id})">후속작업 생성</button>
                        ` : ''}
                        ${(window.currentUser.role === 'admin' || (schedule.owner && window.currentUser.id !== schedule.owner.id)) ? `
                            <button onclick="requestCompletion(${schedule.id})">완료 요청</button>
                        ` : ''}
                        ${schedule.parent ? `<button onclick="viewParentSchedule(${schedule.parent.id})">부모작업 보기</button>` : ''}
                        ${schedule.children && schedule.children.length > 0 ? `<button onclick="viewChildrenSchedules(${schedule.id})">후속작업 보기</button>` : ''}
                    </div>
                    ` : ''}
                    <div class="memo-section">
                        <div class="memo-header">메모</div>
                        <div class="memo-container">
                            ${schedule.memo ? schedule.memo.split('\n').map(line => `<div class="memo-line">${line}</div>`).join('') : '<div class="memo-line">없음</div>'}
                        </div>
                    </div>
                    <div id="modal-attachments-list"></div>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    loadAttachmentsForModal(schedule.id);
    // loadCollaboratorsForModal(schedule.id); // 이제 필요 없음 - schedule.shares에서 직접 표시
}

// 후속 작업 관련 함수들
async function main_createChildSchedule(parentId) {
    try {
        // 1. 상세 모달에서 parentOrder 값을 미리 읽어둠
        const parentModal = document.getElementsByClassName('schedule-modal')[0];
        const parent_order = parentModal ? Number(parentModal.dataset.parentOrder) : 0;
        const childCount = parent_order + 1;

        // 2. 상세 모달 닫기
        closeScheduleModal();

        // 3. 일정 추가 폼 띄우기
        showAddScheduleForm();

        // 4. 폼이 렌더링된 후 값을 세팅
        setTimeout(() => {
            // 제목은 비워두고 placeholder만 표시
            document.getElementById('schedule-title').value = '후속:' + window.lastParentTitle|| '';
            document.getElementById('schedule-content').value = window.lastParentContent || '';
            document.getElementById('schedule-project').value = window.lastParentProjectName || '';
            // 부모 프로젝트 정보 표시
            const parentInfoDiv = document.getElementById('schedule-parent-info');
            if (parentInfoDiv) {
                parentInfoDiv.textContent = window.lastParentTitle || '없음';
            }
            // 부모 일정의 마감시간으로 설정 (없으면 현재 날짜)
            if (window.lastParentDueTime) {
                // 서버에서 이미 한국시간으로 처리되므로 추가 오프셋 불필요
                const parentDueDate = new Date(window.lastParentDueTime);
                
                // 마감시간을 부모 일정의 마감시간으로 설정
                const dueTimeInput = document.getElementById('schedule-due-time');
                if (dueTimeInput) {
                    dueTimeInput.value = parentDueDate.toISOString().slice(0, 16);
                }
                
                // 알람시간을 부모 일정의 마감시간보다 1시간 전으로 설정
                const alarmTimeInput = document.getElementById('schedule-alarm-time');
                if (alarmTimeInput) {
                    const alarmTime = new Date(parentDueDate.getTime() - (1 * 60 * 60 * 1000)); // 1시간 전
                    alarmTimeInput.value = alarmTime.toISOString().slice(0, 16);
                }
            } else {
                const now = new Date();
                
                // 부모 마감시간이 없으면 현재 시간으로 설정
                const nowDateTime = now.toISOString().slice(0, 16);
                const dueTimeInput = document.getElementById('schedule-due-time');
                const alarmTimeInput = document.getElementById('schedule-alarm-time');
                if (dueTimeInput) dueTimeInput.value = nowDateTime;
                if (alarmTimeInput) {
                    const alarmTime = new Date(now.getTime() - (1 * 60 * 60 * 1000)); // 1시간 전
                    alarmTimeInput.value = alarmTime.toISOString().slice(0, 16);
                }
            }
            document.getElementById('schedule-priority').value = window.lastParentPriority || '일반';
            
            // 부모 ID와 parent_order를 hidden input으로 저장
            const form = document.getElementById('internal-add-schedule-form');
            if (form) {
                let parentIdInput = form.querySelector('#parent-id');
                if (!parentIdInput) {
                    parentIdInput = document.createElement('input');
                    parentIdInput.type = 'hidden';
                    parentIdInput.id = 'parent-id';
                    form.appendChild(parentIdInput);
                }
                parentIdInput.value = parentId;

                let parentOrderInput = form.querySelector('#parent-order');
                if (!parentOrderInput) {
                    parentOrderInput = document.createElement('input');
                    parentOrderInput.type = 'hidden';
                    parentOrderInput.id = 'parent-order';
                    form.appendChild(parentOrderInput);
                }
                parentOrderInput.value = childCount;
            }
        }, 100);
    } catch (error) {
        console.error('Create child schedule error:', error);
        alert(error.message);
    }
}

function closeDetail() {

    const detailDiv = document.querySelector('.schedule-modal');
    
    if (detailDiv) {
    
    detailDiv.remove();
    
    }
    
}

function closeScheduleModal() {
    const modal = document.querySelector('.schedule-modal');
    if (modal) {
        modal.remove();
    }
}

// --- ATTACHMENT FUNCTIONS FOR MODAL ---
async function loadAttachmentsForModal(scheduleId) {
    const token = localStorage.getItem('token');
    if (!token) return;
    const attachmentsList = document.getElementById('modal-attachments-list');
    if (!attachmentsList) return;
    attachmentsList.innerHTML = '<p>첨부 파일 로딩 중...</p>';

    try {
        // 스케줄 상세 정보를 가져와서 attachments를 얻어야 함
        const response = await fetch(`/schedules/${scheduleId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            const scheduleData = await response.json();
            renderAttachmentsForModal(scheduleData.attachments || [], scheduleId);
        } else {
            log('ERROR', 'Failed to load schedule details for attachments', {status: response.status});
            attachmentsList.innerHTML = '<p>첨부 파일을 불러오는데 실패했습니다.</p>';
        }
    } catch (error) {
        log('ERROR', 'Load attachments error for modal', error);
        attachmentsList.innerHTML = '<p>첨부 파일 로딩 중 오류 발생.</p>';
    }
}

// 공동작업자 관련 함수들
async function loadCollaboratorsForModal(scheduleId) {
    const token = localStorage.getItem('token');
    if (!token) return;
    
    const collaboratorsList = document.getElementById('collaborators-list');
    if (!collaboratorsList) return;
    
    try {
        const response = await fetch(`/schedules/${scheduleId}/collaborators`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const collaborators = await response.json();
            renderCollaboratorsForModal(collaborators, scheduleId);
        } else {
            log('ERROR', 'Failed to load collaborators', {status: response.status});
            let errorMessage = '공동작업자 정보를 불러오는데 실패했습니다.';
            
            if (response.status === 404) {
                errorMessage = '일정을 찾을 수 없습니다.';
            } else if (response.status === 401) {
                errorMessage = '인증이 필요합니다.';
            } else if (response.status === 403) {
                errorMessage = '접근 권한이 없습니다.';
            } else if (response.status >= 500) {
                errorMessage = '서버 오류가 발생했습니다.';
            }
            
            collaboratorsList.innerHTML = `<p style="color: #dc3545; font-size: 11px;">${errorMessage}</p>`;
        }
    } catch (error) {
        log('ERROR', 'Load collaborators error for modal', error);
        let errorMessage = '공동작업자 정보 로딩 중 오류 발생.';
        
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            errorMessage = '네트워크 연결을 확인해주세요.';
        }
        
        collaboratorsList.innerHTML = `<p style="color: #dc3545; font-size: 11px;">${errorMessage}</p>`;
    }
}

function renderCollaboratorsForModal(collaborators, scheduleId) {
    const collaboratorsList = document.getElementById('collaborators-list');
    if (!collaboratorsList) return;
    
    if (collaborators.length === 0) {
        collaboratorsList.innerHTML = '<span class="no-collaborators">공동작업자가 없습니다</span>';
        return;
    }
    
            const collaboratorsHtml = collaborators.map(collaborator => {
            const permissions = [];
            if (collaborator.can_edit) permissions.push('✏️ 수정');
            if (collaborator.can_delete) permissions.push('🗑️ 삭제');
            if (collaborator.can_complete) permissions.push('✅ 완료');
            if (collaborator.can_share) permissions.push('📤 공유');
            
            const permissionsText = permissions.length > 0 ? permissions.join(' ') : '권한 없음';
            
            return `
                <div class="collaborator-item">
                    <span class="collaborator-name">${collaborator.name || collaborator.username}</span>
                    <span class="collaborator-role">${collaborator.role || '협업자'}</span>
                    <span class="collaborator-permissions">${permissionsText}</span>
                </div>
            `;
        }).join('');
    
    collaboratorsList.innerHTML = collaboratorsHtml;
}

function renderAttachmentsForModal(attachments, scheduleId) {
    const attachmentsList = document.getElementById('modal-attachments-list');
    if (!attachmentsList) return;
    attachmentsList.innerHTML = '';
    if (attachments.length === 0) {
        attachmentsList.innerHTML = '<p>첨부된 파일이 없습니다.</p>';
        return;
    }
    attachments.forEach(attachment => {
        const attachmentDiv = document.createElement('div');
        attachmentDiv.className = 'attachment-item';
        const thumbnailHtml = createFileThumbnail(attachment.filename, attachment.file_path, attachment.mime_type);
        let attachment_filename_short = attachment.filename;
        if(attachment.filename.length>15){
            attachment_filename_short  = attachment.filename.substring(0, 12) + '...';
        }


        attachmentDiv.innerHTML = `
            ${thumbnailHtml}
            <div class="attachment-info">
                <a href="${attachment.file_path}" target="_blank" download="${attachment.filename || 'download'}">
                  <span class="attachment-name">${attachment_filename_short}</span>
                </a>
                <span class="attachment-size">${formatFileSize(attachment.file_size || 0)}</span>
            </div>
            <button onclick="deleteAttachmentFromModal(${attachment.id}, ${scheduleId})" class="delete-btn">삭제</button>
        `;
        attachmentsList.appendChild(attachmentDiv);
    });
}

async function uploadFilesToSchedule(scheduleId) {
    const token = localStorage.getItem('token');
    if (!token) return;
    const fileInput = document.getElementById('modal-file-upload');
    if (!fileInput || !fileInput.files.length) {
        alert('업로드할 파일을 선택해주세요.');
        return;
    }
    const formData = new FormData();
    for (const file of fileInput.files) {
        formData.append('files', file); // FastAPI에서는 List[UploadFile] = File(...) 이므로 'files'
    }
    try {
        const response = await fetch(`/attachments/schedules/${scheduleId}/attachments`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }, // Content-Type은 FormData가 자동 설정
            body: formData
        });
        if (response.ok) {
            await loadAttachmentsForModal(scheduleId); // 목록 새로고침
            fileInput.value = ''; // 입력 필드 초기화
            alert('파일이 성공적으로 업로드되었습니다.');
        } else {
            const error = await response.json();
            log('ERROR', 'File upload to schedule failed', error);
            alert(error.detail || '파일 업로드에 실패했습니다.');
        }
    } catch (error) {
        log('ERROR', 'File upload to schedule error', error);
        alert('파일 업로드 중 오류가 발생했습니다.');
    }
}

async function deleteAttachmentFromModal(attachmentId, scheduleId) {
    if (!confirm('정말로 이 첨부 파일을 삭제하시겠습니까?')) return;
    const token = localStorage.getItem('token');
    if (!token) return;
    try {
        // API 엔드포인트는 /attachments/{attachment_id}
        const response = await fetch(`/attachments/${attachmentId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            await loadAttachmentsForModal(scheduleId); // 목록 새로고침
            alert('첨부 파일이 삭제되었습니다.');
        } else {
            const error = await response.json();
            log('ERROR', 'Failed to delete attachment from modal', error);
            alert(error.detail || '첨부 파일 삭제에 실패했습니다.');
        }
    } catch (error) {
        log('ERROR', 'Delete attachment error from modal', error);
        alert('첨부 파일 삭제 중 오류가 발생했습니다.');
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}


// --- SCHEDULE CRUD FUNCTIONS (ADD, EDIT, DELETE, COMPLETE, SHARE, MEMO from backup) ---
async function toggleComplete(scheduleId, completed) { // completed 파라미터는 현재 상태의 반대.
    log('DEBUG', 'Toggling schedule completion', { scheduleId, toState: completed });
    const token = localStorage.getItem('token');
    if (!token) return;
    try {
        // API가 is_completed 값을 받는지, 아니면 그냥 토글인지 확인 필요.
        // FastAPI에서는 보통 PUT /schedules/{id}/complete 또는 /schedules/{id}/incomplete
        // 또는 POST /schedules/{id}/toggle_complete
        // 여기서는 POST /schedules/{id}/complete 가 토글 역할을 한다고 가정 (백업과 동일)
        const response = await fetch(`/schedules/${scheduleId}/complete`, {
            method: 'POST', // 또는 PUT
            headers: { 'Authorization': `Bearer ${token}` /*, 'Content-Type': 'application/json' */},
            // body: JSON.stringify({ is_completed: completed }) // API가 상태를 받는 경우
        });
        if (response.ok) {
            log('INFO', 'Schedule completion toggled successfully');
            // 모달이 열려있으면 모달 내 정보 업데이트, 아니면 목록 새로고침
            const modal = document.querySelector('.schedule-modal');
            if (modal && modal.dataset.scheduleId == scheduleId) {
                 // 특정 스케줄 데이터만 다시 로드하여 모달 업데이트
                const updatedScheduleData = await response.json(); // API가 업데이트된 스케줄 반환 가정
                const scheduleIndex = window.schedules.findIndex(s => s.id === scheduleId);
                if (scheduleIndex !== -1) window.schedules[scheduleIndex] = updatedScheduleData;
                handleScheduleClick(updatedScheduleData); // 모달 다시 그리기
            } else {
                 await refreshSchedules(); // 전체 목록 새로고침
            }
        } else {
            const error = await response.json();
            log('ERROR', 'Failed to toggle schedule completion', error);
            alert(error.detail || '일정 상태 변경에 실패했습니다.');
        }
    } catch (error) {
        log('ERROR', 'Toggle complete error', error);
        alert('일정 상태 변경 중 오류가 발생했습니다.');
    }
}

async function showQuickNoteForm() {
    // 기존 폼이 있으면 제거
    const existingForm = document.querySelector('.add-quicknote-form');
    if (existingForm) {
        existingForm.remove();
    }

    const formDiv = document.createElement('div');
    formDiv.className = 'add-quicknote-form';

    formDiv.style.position = 'fixed';
    formDiv.style.top = '0';
    formDiv.style.left = '0';
    formDiv.style.width = '100vw';
    formDiv.style.height = '100vh';
    formDiv.style.backgroundColor = 'rgba(0, 0, 0, 0.6)';
    formDiv.style.zIndex = '1000';
    formDiv.style.display = 'flex';
    formDiv.style.justifyContent = 'center';
    formDiv.style.alignItems = 'center';
    formDiv.style.padding = '20px';
    formDiv.style.boxSizing = 'border-box';

    formDiv.innerHTML = `
        <form id="quicknote-form" style="background-color: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 5px 15px rgba(0,0,0,0.3); max-width: 500px; width: 100%; box-sizing: border-box;">
            <h3 style="text-align: center; margin-top: 0; margin-bottom: 20px; color: #333;">퀵메모 추가</h3>
            
            <div class="form-group" style="margin-bottom: 15px;">
                <label for="quicknote-content" style="display: block; margin-bottom: 5px; font-weight: bold;">내용 *</label>
                <textarea id="quicknote-content" placeholder="메모 내용을 입력하세요..." rows="5" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; resize: vertical; min-height: 100px;" required></textarea>
            </div>

            <div style="font-size: 12px; color: #666; margin-bottom: 15px;">
                작성일시와 작성자는 자동으로 입력됩니다.
            </div>

            <div class="form-buttons" style="text-align: right;">
                <button type="submit" style="padding: 10px 20px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px;">추가</button>
                <button type="button" onclick="cancelQuickNoteForm()" style="padding: 10px 20px; background-color: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">취소</button>
            </div>
        </form>
    `;

    document.body.appendChild(formDiv);

    const form = formDiv.querySelector('#quicknote-form');
    if (form) {
        form.addEventListener('submit', handleAddQuickNote);
    }

    const contentInput = formDiv.querySelector('#quicknote-content');
    if (contentInput) {
        contentInput.focus();
    }
}

function cancelQuickNoteForm() {
    const formDiv = document.querySelector('.add-quicknote-form');
    if (formDiv) {
        formDiv.remove();
    }
}

async function handleAddQuickNote(e) {
    e.preventDefault();
    
    const content = document.getElementById('quicknote-content').value.trim();
    
    if (!content) {
        alert('내용을 입력해주세요.');
        return;
    }

    try {
        const response = await apiRequest('/api/quickmemos', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                content: content
            })
        });

        if (response.ok) {
            alert('퀵메모가 추가되었습니다.');
            cancelQuickNoteForm();
        } else {
            const errorData = await response.json();
            throw new Error(errorData.detail || '퀵메모 추가에 실패했습니다.');
        }
    } catch (error) {
        console.error('Error adding quicknote:', error);
        alert('퀵메모 추가 중 오류가 발생했습니다: ' + error.message);
    }
}

async function showAddScheduleForm() {
    // 기존 폼이 있으면 제거
    cancelAddSchedule();

    const now = new Date();
    const koreaTimeOffset = 9 * 60 * 60 * 1000;
    const koreaNow = new Date(now.getTime() + koreaTimeOffset);
    const nowDateTime = koreaNow.toISOString().slice(0, 16);
    const alarmTime = new Date(koreaNow.getTime() - (1 * 60 * 60 * 1000)); // 1시간 전
    const alarmDateTime = alarmTime.toISOString().slice(0, 16);

    const formDiv = document.createElement('div');
    formDiv.className = 'add-schedule-form';

    formDiv.style.position = 'fixed';
    formDiv.style.top = '0';
    formDiv.style.left = '0';
    formDiv.style.width = '100vw';
    formDiv.style.height = '100vh';
    formDiv.style.backgroundColor = 'rgba(0, 0, 0, 0.6)';
    formDiv.style.zIndex = '1000';
    formDiv.style.display = 'flex';
    formDiv.style.justifyContent = 'center';
    formDiv.style.alignItems = 'flex-start';
    formDiv.style.padding = '6px';
    formDiv.style.boxSizing = 'border-box';

    formDiv.innerHTML = `
        <form id="internal-add-schedule-form" style="background-color: #fff; padding: 6px; border-radius: 8px; box-shadow: 0 5px 15px rgba(0,0,0,0.3); max-width: 500px; width: 100%; max-height: 90vh; overflow-y: auto; box-sizing: border-box;">
            <h3 style="text-align: center; margin-top: 0; margin-bottom: 0px; color: #333;">새 일정 추가</h3>
            
            <div class="form-group" style="position: relative;">
                <label for="schedule-project">프로젝트명 *</label>
                <div style="display: flex; gap: 10px;">
                    <input type="text" id="schedule-project" placeholder="프로젝트명을 입력하세요 (미입력시 '일정'으로 표시)" style="flex: 1;">
                    <button type="button" onclick="toggleProjectList()" style="padding: 5px 10px;">▼</button>
                </div>
                <div id="project-list" style="display: none; position: absolute; top: 100%; left: 0; right: 0; background: white; border: 1px solid #ddd; border-radius: 4px; max-height: 200px; overflow-y: auto; z-index: 1000;"></div>
            </div>

            <div class="form-group">
                <label for="schedule-title">제목 *</label>
                <input type="text" id="schedule-title" placeholder="제목을 입력하세요 (미입력시 '일정'으로 표시)">
            </div>

            

            <div class="form-group">
                <label for="schedule-priority">우선순위 *</label>
                <select id="schedule-priority" required>
                    <option value="긴급">긴급</option>
                    <option value="급함">급함</option>
                    <option value="곧임박">곧임박</option>
                    <option value="일반" selected>일반</option>
                    <option value="거북이">🐢 거북이</option>
                </select>
            </div>

            <div class="form-group">
                <label for="schedule-collaborators">공동 작업자</label>
                <div style="position: relative;">
                    <input type="text" id="schedule-collaborators-search" placeholder="사용자 검색..." style="width: 100%; margin-bottom: 5px;">
                    <select id="schedule-collaborators" multiple style="width: 100%; min-height: 100px;">
                        <option value="">사용자를 검색하여 선택하세요</option>
                    </select>
                    <div id="selected-collaborators" style="margin-top: 5px;"></div>
                </div>
            </div>

            <div class="form-group">
                <label for="schedule-content">내용</label>
                <textarea id="schedule-content" placeholder="내용" rows="3" style="height: 60px;"></textarea>
            </div>

            <div class="form-group">
                <label for="schedule-due-time">마감시간 *</label>
                <input type="datetime-local" id="schedule-due-time" value="${nowDateTime.split('T')[0]}" required>
                <div class="due-time-quick-buttons">
                    <button type="button" onclick="setQuickDueTime(1)">1시간뒤</button>
                    <button type="button" onclick="setQuickDueTime(6)">6시간뒤</button>
                    <button type="button" onclick="setQuickDueTime(12)">12시간뒤</button>
                    <button type="button" onclick="setQuickDueTime(24)">1일뒤</button>
                    <button type="button" onclick="setQuickDueTime(72)">3일뒤</button>
                    <button type="button" onclick="setQuickDueTime(168)">1주일뒤</button>
                    <button type="button" onclick="setQuickDueTime(720)">한달뒤</button>
                </div>
            </div>

            <div class="form-group">
                <label for="schedule-alarm-time">알람시간</label>
                <input type="datetime-local" id="schedule-alarm-time" value="${alarmDateTime.split('T')[0]}">
            </div>

            <div class="form-group">
                <label>알람 빠른 설정</label>
                <div class="alarm-quick-buttons">
                    <button type="button" onclick="setQuickAlarmTime(1)">1시간 전</button>
                    <button type="button" onclick="setQuickAlarmTime(3)">3시간 전</button>
                    <button type="button" onclick="setQuickAlarmTime(24)">하루 전</button>
                    <button type="button" id="repeat-toggle" onclick="toggleRepeatInForm()">매일 반복</button>
                    <input type="hidden" id="schedule-repeat" value="false">
                </div>
            </div>
            <div class="form-group">
                <label for="schedule-parent">부모작업</label>
                <div id="schedule-parent-info" style="font-size: 12px;">
                    없음
                </div>
            </div>
            <div class="indv_container" hidden>
                <div style="height: 20px;" hidden>&nbsp;&nbsp;개인일정 (본인만 볼 수 있습니다)&nbsp;&nbsp;&nbsp;</div>
                <input type="checkbox" id="schedule-individual" style="height: 20px;" hidden>
            </div>

            <div class="form-buttons" style="text-align: right; margin-top: 4px;">
                <button type="submit">공개일정 추가</button>
                <button type="button" onclick="addPrivateSchedule()" style="background-color:rgb(229, 125, 255);">개인일정 추가</button>
                <button type="button" onclick="cancelAddSchedule()" style="padding: 10px 15px; background-color: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">취소</button>
            </div>
        </form>
    `;

    document.body.appendChild(formDiv);

    const internalForm = formDiv.querySelector('#internal-add-schedule-form');
    if(internalForm) {
        internalForm.addEventListener('submit', handleAddSchedule);
        const dueTimeInput = internalForm.querySelector('#schedule-due-time');
        if(dueTimeInput) {
            dueTimeInput.addEventListener('change', updateAlarmTimeOnDueTimeChange);
        }
    }

    const firstInput = formDiv.querySelector('#schedule-project');
    if (firstInput) {
        firstInput.focus();
    }

    // 프로젝트 목록 로드
    await loadProjectList();
    
    // 공동 작업자 기능 초기화
    initializeCollaborators();
}

function toggleProjectList() {
    const projectList = document.getElementById('project-list');
    if (projectList) {
        projectList.style.display = projectList.style.display === 'none' ? 'block' : 'none';
    }
}

// 프로젝트 입력 필드 외부 클릭 시 드롭다운 닫기
document.addEventListener('click', (e) => {
    // 일정 추가 모드
    const projectList = document.getElementById('project-list');
    const projectInput = document.getElementById('schedule-project');
    const toggleButton = e.target.closest('button[onclick="toggleProjectList()"]');
    
    if (projectList && projectList.style.display !== 'none' && 
        !projectList.contains(e.target) && 
        !projectInput?.contains(e.target) && 
        !toggleButton) {
        projectList.style.display = 'none';
    }

    // 수정 모드
    const editProjectList = document.getElementById('edit-project-list');
    const editProjectInput = document.getElementById('edit-project');
    const editToggleButton = e.target.closest('button[onclick="toggleEditProjectList()"]');
    
    if (editProjectList && editProjectList.style.display !== 'none' && 
        !editProjectList.contains(e.target) && 
        !editProjectInput?.contains(e.target) && 
        !editToggleButton) {
        editProjectList.style.display = 'none';
    }
});

async function updateAlarmTimeOnDueTimeChange() {
    const dueTimeInput = document.getElementById('schedule-due-time');
    const alarmTimeInput = document.getElementById('schedule-alarm-time');
    
    if (!dueTimeInput || !alarmTimeInput || !dueTimeInput.value) return;
    
    const dueTime = new Date(dueTimeInput.value);
    if (isNaN(dueTime.getTime())) return;
    
    // 알람 시간을 마감시간보다 1시간 전으로 설정
    const alarmTime = new Date(dueTime.getTime() - (1 * 60 * 60 * 1000));
    alarmTimeInput.value = alarmTime.toISOString().slice(0, 16);
}

async function setQuickDueTime(hoursAfter) {
    console.log('setQuickDueTime0', hoursAfter);
    const dueTimeInput = document.getElementById('schedule-due-time');
    if (!dueTimeInput) {
        alert('마감시간 입력 필드를 찾을 수 없습니다.'); 
        return; 
    }
    
    // 현재 시간을 기준으로 계산
    const now = new Date();
    const koreaTimeOffset = 9 * 60 * 60 * 1000;
    const koreaNow = new Date(now.getTime() + koreaTimeOffset);
    
    // 현재 시간에 hoursAfter 시간을 더함
    const newDueTime = new Date(koreaNow.getTime() + (hoursAfter * 60 * 60 * 1000));
    console.log('setQuickDueTime1', newDueTime);
    
    // datetime-local 입력 필드 형식으로 변환 (YYYY-MM-DDTHH:mm)
    const year = newDueTime.getFullYear();
    const month = String(newDueTime.getMonth() + 1).padStart(2, '0');
    const day = String(newDueTime.getDate()).padStart(2, '0');
    const hours = String(newDueTime.getHours()).padStart(2, '0');
    const minutes = String(newDueTime.getMinutes()).padStart(2, '0');
    const dueDateTime = `${year}-${month}-${day}T${hours}:${minutes}`;
    console.log('setQuickDueTime2', dueDateTime);
    dueTimeInput.value = dueDateTime;
}

async function setQuickAlarmTime(hoursBefore) {
    console.log('setQuickAlarmTime0', hoursBefore);
    const dueTimeInput = document.getElementById('schedule-due-time');
    const alarmTimeInput = document.getElementById('schedule-alarm-time');
    if (!dueTimeInput || !alarmTimeInput || !dueTimeInput.value) {
        alert('먼저 마감시간을 설정해주세요.'); return;
    }
    
    // 마감시간을 Date 객체로 변환
    console.log('setQuickAlarmTime1', dueTimeInput);
    const dueTime = new Date(dueTimeInput.value);
    if (isNaN(dueTime.getTime())) { 
        alert('유효한 마감시간을 설정해주세요.'); 
        return; 
    }
    
    // 알람 시간 계산 (마감시간에서 hoursBefore 시간을 뺌)
    const alarmTime = new Date(dueTime.getTime() - (hoursBefore * 60 * 60 * 1000));
    console.log('setQuickAlarmTime2', alarmTime);
    
    // datetime-local 입력 필드 형식으로 변환 (YYYY-MM-DDTHH:mm)
    const year = alarmTime.getFullYear();
    const month = String(alarmTime.getMonth() + 1).padStart(2, '0');
    const day = String(alarmTime.getDate()).padStart(2, '0');
    const hours = String(alarmTime.getHours()).padStart(2, '0');
    const minutes = String(alarmTime.getMinutes()).padStart(2, '0');
    const alarmDateTime = `${year}-${month}-${day}T${hours}:${minutes}`;
    console.log('setQuickAlarmTime3', alarmDateTime);
    alarmTimeInput.value = alarmDateTime;
}

function toggleRepeatInForm() { // For Add Form
    const repeatButton = document.getElementById('repeat-toggle');
    const repeatInput = document.getElementById('schedule-repeat');
    if (!repeatButton || !repeatInput) return;
    if (repeatInput.value === 'false') {
        repeatInput.value = 'true';
        repeatButton.textContent = '매일 반복 해제';
        repeatButton.classList.add('active');
    } else {
        repeatInput.value = 'false';
        repeatButton.textContent = '매일 반복';
        repeatButton.classList.remove('active');
    }
}

function cancelAddSchedule() {
    const form = document.querySelector('.add-schedule-form');
    if (form) form.remove();
}

function addPrivateSchedule() {
    // 개인일정 체크박스를 체크
    const individualCheckbox = document.getElementById('schedule-individual');
    if (individualCheckbox) {
        individualCheckbox.checked = true;
    }
    
    // 폼을 제출
    const form = document.getElementById('internal-add-schedule-form');
    if (form) {
        const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
        form.dispatchEvent(submitEvent);
    }
}

async function handleAddSchedule(e) {
    e.preventDefault();
    const token = localStorage.getItem('token');
    if (!token) {
        console.error('❌ [SCHEDULE_CREATE] No authentication token found');
        return;
    }

    console.log('🚀 [SCHEDULE_CREATE] Starting schedule creation process...');

    // 개인일정이 아닌 경우(공개일정)에 확인 메시지 표시
    const isIndividual = document.getElementById('schedule-individual').checked;
    console.log(`📋 [SCHEDULE_CREATE] Individual schedule setting: ${isIndividual}`);
    
    if (!isIndividual) {
        console.log('⚠️ [SCHEDULE_CREATE] Public schedule detected, showing confirmation dialog');
        if (!confirm('공개일정은 모두가 이 일정을 함께 볼 수 있습니다. 발행하시겠습니까?')) {
            console.log('❌ [SCHEDULE_CREATE] User cancelled public schedule creation');
            return; // 사용자가 취소를 선택한 경우 함수 종료
        }
        console.log('✅ [SCHEDULE_CREATE] User confirmed public schedule creation');
    }

    function formatDateTimeForAPI(dateStr) {
        if (!dateStr) return null;
        const date = new Date(dateStr);
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        const formatted = `${year}-${month}-${day}T${hours}:${minutes}:${seconds}`;
        console.log(`🕒 [SCHEDULE_CREATE] Formatted datetime: ${dateStr} → ${formatted}`);
        return formatted;
    }

    // 폼 데이터 수집
    const projectInput = document.getElementById('schedule-project');
    const titleInput = document.getElementById('schedule-title');
    const project = projectInput.value.trim() || '일정';
    const title = titleInput.value.trim() || '일정';
    const dueTime = document.getElementById('schedule-due-time').value;
    const priority = document.getElementById('schedule-priority').value;
    
    console.log(`📋 [SCHEDULE_CREATE] Form data collected:`);
    console.log(`   Project: "${project}"`);
    console.log(`   Title: "${title}"`);
    console.log(`   Due Time: "${dueTime}"`);
    console.log(`   Priority: "${priority}"`);
    
    if (!dueTime || !priority) {
        console.error('❌ [SCHEDULE_CREATE] Required fields missing: dueTime or priority');
        alert('마감시간과 우선순위는 필수 입력 항목입니다.'); 
        return;
    }

    // 부모 ID와 parent_order 가져오기
    const parentIdInput = document.getElementById('parent-id');
    const parentOrderInput = document.getElementById('parent-order');
    const parent_id = parentIdInput && parentIdInput.value ? parseInt(parentIdInput.value) : null;
    const parent_order = parentOrderInput && parentOrderInput.value;
    
    console.log(`👨‍👦 [SCHEDULE_CREATE] Parent information:`);
    console.log(`   Parent ID: ${parent_id}`);
    console.log(`   Parent Order: ${parent_order}`);

    // 새로운 프로젝트명인 경우 projects.json에 추가
    if (project !== '일정') {
        console.log(`📁 [SCHEDULE_CREATE] New project detected: "${project}", attempting to add to projects...`);
        try {
            const response = await fetch('/projects/', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: project })
            });
            if (!response.ok) {
                const error = await response.json();
                // 이미 존재하는 프로젝트명인 경우는 무시
                if (error.detail !== "이미 존재하는 프로젝트입니다") {
                    console.error(`❌ [SCHEDULE_CREATE] Failed to add project "${project}":`, error);
                    throw new Error(error.detail);
                } else {
                    console.log(`ℹ️ [SCHEDULE_CREATE] Project "${project}" already exists, continuing...`);
                }
            } else {
                console.log(`✅ [SCHEDULE_CREATE] Successfully added new project: "${project}"`);
            }
        } catch (error) {
            console.error('❌ [SCHEDULE_CREATE] Project creation error:', error);
            // 프로젝트 추가 실패는 일정 생성에 영향을 주지 않도록 함
        }
    } else {
        console.log(`ℹ️ [SCHEDULE_CREATE] Using default project name: "일정"`);
    }

    // 공동 작업자 정보 가져오기
    console.log('👥 [SCHEDULE_CREATE] Processing collaborators...');
    const collaboratorsSelect = document.getElementById('schedule-collaborators');
    const selectedCollaborators = [];
    
    if (collaboratorsSelect) {
        const selectedOptions = Array.from(collaboratorsSelect.selectedOptions);
        console.log(`👥 [SCHEDULE_CREATE] Selected options count: ${selectedOptions.length}`);
        
        for (let i = 0; i < selectedOptions.length; i++) {
            const option = selectedOptions[i];
            if (option.value && option.value.trim() !== '') {
                const collaboratorId = parseInt(option.value);
                const collaboratorName = option.textContent;
                selectedCollaborators.push(collaboratorId);
                console.log(`👥 [SCHEDULE_CREATE] Collaborator ${i+1}: ID ${collaboratorId}, Name: "${collaboratorName}"`);
            }
        }
        
        console.log(`👥 [SCHEDULE_CREATE] Final collaborators array: [${selectedCollaborators.join(', ')}]`);
    } else {
        console.warn('⚠️ [SCHEDULE_CREATE] Collaborators select element not found');
    }

    // 일정 데이터 구성
    const scheduleData = {
        project_name: project,
        title: title,
        date: formatDateTimeForAPI(dueTime), // DB의 date 필드에 due_time 값 저장
        priority: priority,
        content: document.getElementById('schedule-content').value || null,
        due_time: formatDateTimeForAPI(dueTime),
        alarm_time: formatDateTimeForAPI(document.getElementById('schedule-alarm-time').value),
        individual: document.getElementById('schedule-individual').checked,
        is_repeat: document.getElementById('schedule-repeat').value === 'true',
        parent_id: parent_id,
        parent_order: parent_order,
        collaborators: selectedCollaborators
    };
    
    console.log('📤 [SCHEDULE_CREATE] Final schedule data prepared:');
    console.log('   ', JSON.stringify(scheduleData, null, 2));

    try {
        console.log('🌐 [SCHEDULE_CREATE] Sending POST request to /schedules/...');
        const response = await fetch('/schedules/', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(scheduleData),
        });
        
        console.log(`🌐 [SCHEDULE_CREATE] Response received: ${response.status} ${response.statusText}`);
        
        if (response.ok) {
            const responseData = await response.json();
            console.log('✅ [SCHEDULE_CREATE] Schedule created successfully!');
            console.log('✅ [SCHEDULE_CREATE] Response data:', responseData);
            
            // 공동작업자 정보 확인
            if (responseData.shares && responseData.shares.length > 0) {
                console.log(`👥 [SCHEDULE_CREATE] Collaborators confirmed in response: ${responseData.shares.length} shares`);
                responseData.shares.forEach((share, index) => {
                    console.log(`👥 [SCHEDULE_CREATE] Share ${index+1}: Schedule ID ${share.schedule_id}, User ID ${share.shared_with_id}`);
                });
            } else {
                console.log('ℹ️ [SCHEDULE_CREATE] No collaborators in response (may be individual schedule)');
            }
            
            cancelAddSchedule();
            console.log('🔄 [SCHEDULE_CREATE] Refreshing schedules...');
            await refreshSchedules();
            
            console.log('🔄 [SCHEDULE_CREATE] Refreshing project list...');
            await loadProjectList();
            
            console.log('🎉 [SCHEDULE_CREATE] Schedule creation process completed successfully!');
        } else {
            const error = await response.json();
            console.error('❌ [SCHEDULE_CREATE] Schedule creation failed:', error);
            log('ERROR', 'Schedule creation error', error);
            alert(error.detail || '일정 추가에 실패했습니다.');
        }
    } catch (error) {
        console.error('❌ [SCHEDULE_CREATE] Network or other error during schedule creation:', error);
        log('ERROR', 'Add schedule error', error);
        alert('일정 추가 중 오류가 발생했습니다.');
    }
}

// Provided editSchedule by user
async function editSchedule(scheduleId) {
    const schedule = window.schedules.find(s => s.id === scheduleId);
    if (!schedule) { log('ERROR', `Schedule with id ${scheduleId} not found for editing.`); return; }
 
    const modal = document.querySelector('.schedule-modal');
    if (!modal) {
        alert("오류: 수정 대상 모달을 찾을 수 없습니다.");
        return;
    }

    // 기존 수정 폼이 있으면 제거
    const existingEditForm = document.querySelector('.edit-schedule-form');
    if (existingEditForm) existingEditForm.remove();
 
    const form = document.createElement('div');
    form.className = 'edit-schedule-form';

    // add-schedule-form과 동일한 스타일 적용
    form.style.position = 'fixed';
    form.style.top = '0';
    form.style.left = '0';
    form.style.width = '100vw';
    form.style.height = '100vh';
    form.style.backgroundColor = 'rgba(0, 0, 0, 0.6)';
    form.style.zIndex = '1001'; // modal보다 위에 표시
    form.style.display = 'flex';
    form.style.justifyContent = 'center';
    form.style.alignItems = 'center';
    form.style.padding = '6px';
    form.style.boxSizing = 'border-box';
    
    //날짜는 서버에서 이미 한국시간으로 처리되므로 추가 오프셋 불필요
    const scheduleDueTime_ = new Date(schedule.due_time);
    const scheduleDueTime = scheduleDueTime_.toISOString().slice(0, 16);
    //알람시간도 서버에서 이미 한국시간으로 처리되므로 추가 오프셋 불필요
    const scheduleAlarmTime_ = new Date(schedule.alarm_time);
    const scheduleAlarmTime = scheduleAlarmTime_.toISOString().slice(0, 16);

    form.innerHTML = `
        <form id="internal-edit-schedule-form" style="background-color: #fff; padding: 6px; border-radius: 8px; box-shadow: 0 5px 15px rgba(0,0,0,0.3); max-width: 500px; width: 100%; max-height: 90vh; overflow-y: auto; box-sizing: border-box;">
            <h3 style="text-align: center; margin-top: 0; margin-bottom: 0px; color: #333;">일정 수정</h3>
            
            <div class="form-group" style="position: relative;">
                <label for="edit-project">프로젝트명 *</label>
                <div style="display: flex; gap: 10px;">
                    <input type="text" id="edit-project" value="${schedule.project_name || '일정'}" placeholder="프로젝트명을 입력하세요 (미입력시 '일정'으로 표시)" style="flex: 1;">
                    <button type="button" onclick="toggleEditProjectList()" style="padding: 5px 10px;">▼</button>
                </div>
                <div id="edit-project-list" style="display: none; position: absolute; top: 100%; left: 0; right: 0; background: white; border: 1px solid #ddd; border-radius: 4px; max-height: 200px; overflow-y: auto; z-index: 1000;"></div>
            </div>

            <div class="form-group">
                <label for="edit-title">제목 *</label>
                <input type="text" id="edit-title" value="${schedule.title}" placeholder="제목을 입력하세요 (미입력시 '일정'으로 표시)">
            </div>

            <div class="form-group">
                <label for="edit-priority">우선순위 *</label>
                <select id="edit-priority" required>
                    <option value="긴급" ${schedule.priority === '긴급' ? 'selected' : ''}>긴급</option>
                    <option value="급함" ${schedule.priority === '급함' ? 'selected' : ''}>급함</option>
                    <option value="곧임박" ${schedule.priority === '곧임박' ? 'selected' : ''}>곧임박</option>
                    <option value="일반" ${schedule.priority === '일반' ? 'selected' : ''}>일반</option>
                    <option value="거북이" ${schedule.priority === '거북이' ? 'selected' : ''}>🐢 거북이</option>
                </select>
            </div>

            <div class="form-group">
                <label for="edit-schedule-collaborators">공동 작업자</label>
                <div style="position: relative;">
                    <input type="text" id="edit-schedule-collaborators-search" placeholder="사용자 검색..." style="width: 100%; margin-bottom: 5px;">
                    <select id="edit-schedule-collaborators" multiple style="width: 100%; min-height: 100px;">
                        <option value="">사용자를 검색하여 선택하세요</option>
                    </select>
                    <div id="edit-selected-collaborators" style="margin-top: 5px;"></div>
                </div>
            </div>

            <div class="form-group">
                <label for="edit-content">내용</label>
                <textarea id="edit-content" placeholder="내용" rows="3" style="height: 60px;">${schedule.content || ''}</textarea>
            </div>

            <div class="form-group">
                <label for="edit-due-time">마감시간 *</label>
                <input type="datetime-local" id="edit-due-time" value="${scheduleDueTime}" required>
            </div>

            <div class="form-group">
                <label for="edit-alarm-time">알람시간</label>
                <input type="datetime-local" id="edit-alarm-time" value="${scheduleAlarmTime}">
            </div>

            <div class="form-group">
                <label>알람 빠른 설정</label>
                <div class="alarm-quick-buttons">
                    <button type="button" onclick="setQuickAlarmTimeForEdit(1)">1시간 전</button>
                    <button type="button" onclick="setQuickAlarmTimeForEdit(3)">3시간 전</button>
                    <button type="button" onclick="setQuickAlarmTimeForEdit(24)">하루 전</button>
                </div>
            </div>

            <div class="indv_container">
                <div style="height: 20px;">&nbsp;&nbsp;개인일정 (본인만 볼 수 있습니다)&nbsp;&nbsp;&nbsp;</div>
                    <input type="checkbox" id="edit-individual" ${schedule.individual ? 'checked' : ''} style="height: 20px;">
            </div>

            <div class="form-buttons" style="text-align: right; margin-top: 4px;">
                <button type="submit">저장</button>
                <button type="button" onclick="cancelEdit(${scheduleId})" style="padding: 10px 15px; background-color: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">취소</button>
            </div>
        </form>
    `;
 
    // body에 직접 추가 (add-schedule-form과 동일)
    document.body.appendChild(form);

    const internalForm = form.querySelector('#internal-edit-schedule-form');
    if(internalForm) {
        internalForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await updateSchedule(scheduleId);
        });
        const dueTimeInput = internalForm.querySelector('#edit-due-time');
        if(dueTimeInput) {
            dueTimeInput.addEventListener('change', updateAlarmTimeOnDueTimeChangeForEdit);
        }
    }

    const firstInput = form.querySelector('#edit-project');
    if (firstInput) {
        firstInput.focus();
    }

    // 수정 모드용 프로젝트 목록 로드
    await loadProjectList('edit-project', 'edit-project-list');
    
    // 공동 작업자 기능 초기화 (수정 모드)
    console.log(`[DEBUG] editSchedule - 공동 작업자 기능 초기화 시작`);
    initializeCollaborators('edit');
    
    // select 요소 상태 확인
    setTimeout(() => {
        const collaboratorsSelect = document.getElementById('edit-schedule-collaborators');
        console.log(`[DEBUG] editSchedule - select 요소 생성 후 상태:`, collaboratorsSelect);
        if (collaboratorsSelect) {
            console.log(`[DEBUG] select의 multiple 속성:`, collaboratorsSelect.multiple);
            console.log(`[DEBUG] select의 옵션 개수:`, collaboratorsSelect.options.length);
            console.log(`[DEBUG] select의 선택된 옵션 개수:`, collaboratorsSelect.selectedOptions.length);
        }
    }, 100);
    
    // 기존 공동 작업자 정보 로드 및 설정
    console.log(`[DEBUG] editSchedule - 기존 공동 작업자 정보 로드 시작`);
    loadExistingCollaborators(schedule.id, 'edit');
}

// cancelEdit from backup
function cancelEdit(scheduleId) {
    // 수정 폼 제거 (새로운 스타일링에 맞춰 수정)
    const editForm = document.querySelector('.edit-schedule-form');
    if (editForm) editForm.remove();
}

// updateSchedule from backup
async function updateSchedule(scheduleId) {
    const token = localStorage.getItem('token');
    if (!token) return;

    function formatDateTimeForAPI(dateStr) {
        if (!dateStr) return null;
        const date = new Date(dateStr);
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}`;
    }

    const projectName = document.getElementById('edit-project').value.trim() || '일정';
    const dueTime = document.getElementById('edit-due-time').value;
    
    // 공동 작업자 정보 수집
    const collaboratorsSelect = document.getElementById('edit-schedule-collaborators');
    const selectedCollaborators = Array.from(collaboratorsSelect.selectedOptions).map(option => parseInt(option.value));
    
    // 디버깅: 선택된 공동작업자 정보 로그
    console.log('Selected collaborators:', selectedCollaborators);
    console.log('Selected options:', Array.from(collaboratorsSelect.selectedOptions));
    
    const updatedData = {
        project_name: projectName,
        title: document.getElementById('edit-title').value,
        date: formatDateTimeForAPI(dueTime), // DB의 date 필드에 due_time 값 저장
        priority: document.getElementById('edit-priority').value,
        content: document.getElementById('edit-content').value || null,
        due_time: formatDateTimeForAPI(dueTime),
        alarm_time: formatDateTimeForAPI(document.getElementById('edit-alarm-time').value),
        individual: document.getElementById('edit-individual').checked,
        collaborators: selectedCollaborators,
    };

    // 새로운 프로젝트명인 경우 projects.json에 추가
    if (projectName !== '일정') {
        try {
            const response = await fetch('/projects/', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: projectName })
            });
            if (!response.ok) {
                const error = await response.json();
                // 이미 존재하는 프로젝트명인 경우는 무시
                if (error.detail !== "이미 존재하는 프로젝트입니다") {
                    throw new Error(error.detail);
                }
            }
        } catch (error) {
            log('ERROR', 'Add project error during update', error);
            // 프로젝트 추가 실패는 일정 수정에 영향을 주지 않도록 함
        }
    }

    try {
        const response = await fetch(`/schedules/${scheduleId}`, {
            method: 'PUT',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(updatedData),
        });
        if (response.ok) {
            // 수정 폼 닫기
            cancelEdit(scheduleId);
            closeScheduleModal();
            await refreshSchedules();
            // 프로젝트 목록 새로고침
            await loadProjectList();
        } else {
            const error = await response.json();
            log('ERROR', 'Failed to update schedule', error);
            alert(error.detail || '일정 수정에 실패했습니다.');
        }
    } catch (error) {
        log('ERROR', 'Update schedule error', error);
        alert('일정 수정 중 오류가 발생했습니다.');
    }
}

// 수정 폼용 알람 빠른 설정 함수
async function setQuickAlarmTimeForEdit(hoursBefore) {
    const dueTimeInput = document.getElementById('edit-due-time');
    const alarmTimeInput = document.getElementById('edit-alarm-time');
    if (!dueTimeInput || !alarmTimeInput || !dueTimeInput.value) {
        alert('먼저 마감시간을 설정해주세요.'); return;
    }
    
    // 마감시간을 Date 객체로 변환
    const dueTime = new Date(dueTimeInput.value);
    if (isNaN(dueTime.getTime())) { 
        alert('유효한 마감시간을 설정해주세요.'); 
        return; 
    }
    
    // 알람 시간 계산 (마감시간에서 hoursBefore 시간을 뺌)
    const alarmTime = new Date(dueTime.getTime() - (hoursBefore * 60 * 60 * 1000));
    
    // datetime-local 입력 필드 형식으로 변환 (YYYY-MM-DDTHH:mm)
    const year = alarmTime.getFullYear();
    const month = String(alarmTime.getMonth() + 1).padStart(2, '0');
    const day = String(alarmTime.getDate()).padStart(2, '0');
    const hours = String(alarmTime.getHours()).padStart(2, '0');
    const minutes = String(alarmTime.getMinutes()).padStart(2, '0');
    const alarmDateTime = `${year}-${month}-${day}T${hours}:${minutes}`;
    alarmTimeInput.value = alarmDateTime;
}


async function deleteSchedule(scheduleId) {
    if (!confirm('정말로 이 일정을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) return;
    const token = localStorage.getItem('token');
    if (!token) return;
    try {
        const response = await fetch(`/schedules/${scheduleId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            closeScheduleModal();
            await refreshSchedules(); // 목록 새로고침
            alert('일정이 삭제되었습니다.');
        } else {
            const error = await response.json();
            log('ERROR', 'Failed to delete schedule', error);
            alert(error.detail || '일정 삭제에 실패했습니다.');
        }
    } catch (error) {
        log('ERROR', 'Delete schedule error', error);
        alert('일정 삭제 중 오류가 발생했습니다.');
    }
}

// shareSchedule and shareScheduleWithUser from backup
async function shareSchedule(scheduleId) {
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
        const usersResponse = await fetch('/users/', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!usersResponse.ok) throw new Error('Failed to fetch users for sharing.');
        
        const users = await usersResponse.json();
        const currentUserData = JSON.parse(localStorage.getItem('userData'));
        const otherUsers = users.filter(user => user.id !== currentUserData.id);

        if (otherUsers.length === 0) {
            alert('공유할 다른 사용자가 없습니다.'); return;
        }

        const modalBody = document.querySelector('.schedule-modal .modal-body');
        if (!modalBody) { alert('공유 폼을 표시할 위치를 찾지 못했습니다.'); return; }

        // 기존 공유 폼 제거
        const existingShareForm = modalBody.querySelector('.share-schedule-form-container');
        if (existingShareForm) existingShareForm.remove();

        const formContainer = document.createElement('div');
        formContainer.className = 'share-schedule-form-container'; // For styling and removal
        formContainer.innerHTML = `
            <form id="internal-share-schedule-form">
                <h4>일정 공유</h4>
                <div class="form-group">
                    <label for="share-user">공유할 사용자</label>
                    <select id="share-user" required>
                        ${otherUsers.map(user => `<option value="${user.id}">${user.name} (${user.username})</option>`).join('')}
                    </select>
                </div>
                <div class="form-group">
                    <label for="share-memo">메모 (선택)</label>
                    <textarea id="share-memo" placeholder="공유 시 전달할 메모"></textarea>
                </div>
                <div class="form-buttons">
                    <button type="submit">공유 실행</button>
                    <button type="button" onclick="this.closest('.share-schedule-form-container').remove()">취소</button>
                </div>
            </form>
        `;
        // 상세정보와 액션버튼 사이에 폼 삽입 또는 특정 위치에 append
        const scheduleDetailDiv = modalBody.querySelector('.schedule-detail');
        if (scheduleDetailDiv) {
            scheduleDetailDiv.parentNode.insertBefore(formContainer, scheduleDetailDiv.nextSibling); // 상세정보 다음에 삽입
        } else {
            modalBody.appendChild(formContainer); // fallback
        }
        
        formContainer.querySelector('#internal-share-schedule-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await shareScheduleWithUser(scheduleId);
            formContainer.remove(); // 성공 여부와 관계없이 폼 제거
        });

    } catch (error) {
        log('ERROR', 'Share schedule setup error', error);
        alert('공유 기능 준비 중 오류가 발생했습니다: ' + error.message);
    }
}

async function shareScheduleWithUser(scheduleId) {
    const token = localStorage.getItem('token');
    if (!token) return;
    const sharedWithId = document.getElementById('share-user').value;
    const memo = document.getElementById('share-memo').value || null;

    const shareData = {
        schedule_id: scheduleId, // API 스키마에 따라 필드명 확인
        shared_with_id: parseInt(sharedWithId),
        memo: memo
    };
    log('DEBUG', 'Sharing schedule data', shareData);

    try {
        // API 엔드포인트: /schedules/{schedule_id}/share 또는 /shares/
        const response = await fetch(`/schedules/${scheduleId}/share`, { 
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(shareData),
        });
        if (response.ok) {
            alert('일정이 성공적으로 공유되었습니다.');
            // 공유 후 특별한 UI 변경이 필요하면 여기에 추가 (예: 알림 생성)
        } else if (response.status === 404 && (await response.json()).detail === "Share endpoint not implemented yet") {
            alert("공유 기능이 아직 구현되지 않았습니다.");
        }
         else {
            const error = await response.json();
            log('ERROR', 'Failed to share schedule', error);
            alert(error.detail || '일정 공유에 실패했습니다.');
        }
    } catch (error) {
        log('ERROR', 'Share schedule execution error', error);
        alert('일정 공유 중 오류가 발생했습니다.');
    }
}



function showMemoPopup(scheduleId) {
    hideContextMenu(); // 컨텍스트 메뉴는 닫기
    const schedule = window.schedules.find(s => s.id === scheduleId);
    if (!schedule) { alert('메모를 추가할 일정을 찾지 못했습니다.'); return;}

    // 기존 메모 모달이 있다면 제거
    const existingMemoModal = document.querySelector('.memo-modal-overlay');
    if (existingMemoModal) existingMemoModal.remove();

    const memoModalOverlay = document.createElement('div');
    memoModalOverlay.className = 'memo-modal-overlay';
    
    memoModalOverlay.innerHTML = `
        <div class="memo-modal-content">
            <div class="modal-header">
                <h3>메모 추가</h3>
                <button class="close-button" onclick="this.closest('.memo-modal-overlay').remove()">&times;</button>
            </div>
            <div class="modal-body">
                <form id="internal-memo-form">
                    <div class="form-group">
                        <label for="memo-text-content">메모 내용</label>
                        <textarea id="memo-text-content" rows="5" placeholder="여기에 메모를 입력하세요..."></textarea>
                    </div>
                    <div class="form-buttons">
                        <button type="submit">추가</button>
                        <button type="button" onclick="this.closest('.memo-modal-overlay').remove()">취소</button>
                    </div>
                </form>
            </div>
        </div>
    `;
    
    // controls-collapsible과 schedule-container 사이에 삽입
    const controlsCollapsible = document.querySelector('.controls-collapsible');
    const scheduleContainer = document.getElementById('schedule-container');
    
    if (controlsCollapsible && scheduleContainer) {
        // controls-collapsible 다음, schedule-container 앞에 삽입
        scheduleContainer.parentNode.insertBefore(memoModalOverlay, scheduleContainer);
    } else {
        // 요소를 찾지 못한 경우 body에 추가 (기본값)
        document.body.appendChild(memoModalOverlay);
    }
    
    memoModalOverlay.querySelector('#internal-memo-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await updateMemo(scheduleId);
    });
    document.getElementById('memo-text-content').focus();
}


async function updateMemo(scheduleId) {
    const token = localStorage.getItem('token');
    if (!token) return;
    const memoContent = document.getElementById('memo-text-content').value;
    if (!memoContent.trim()) return;

    const now = new Date();
    const formattedDate = now.toLocaleDateString('ko-KR', {
        year: '2-digit',
        month: '2-digit',
        day: '2-digit'
    }).replace(/\./g, '').replace(/\s/g, '');

    const currentUserData = JSON.parse(localStorage.getItem('userData'));
    const userName = currentUserData ? currentUserData.name : '알 수 없음';

    const newMemoLine = `${formattedDate} (${userName}) : ${memoContent}`;

    try {
        // 기존 메모 가져오기
        const schedule = window.schedules.find(s => s.id === scheduleId);
        const existingMemo = schedule ? schedule.memo : '';
        
        // 기존 메모가 있으면 줄바꿈 추가
        const combinedMemo = existingMemo ? `${existingMemo}\n${newMemoLine}` : newMemoLine;

        const response = await fetch(`/schedules/${scheduleId}/memo`, {
            method: 'PUT',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ memo: combinedMemo }),
        });
        
        const data = await response.json();
        
        if (response.ok) {
            const memoModalOverlay = document.querySelector('.memo-modal-overlay');
            if (memoModalOverlay) memoModalOverlay.remove();
            
            // 스케줄 목록 실시간 업데이트 또는 모달 내용 업데이트
            const scheduleIndex = window.schedules.findIndex(s => s.id === scheduleId);
            if (scheduleIndex !== -1) {
                window.schedules[scheduleIndex].memo = data.memo;
            }
            // 현재 열려있는 상세 모달이 있다면 해당 모달도 업데이트
            const detailModal = document.querySelector('.schedule-modal[data-schedule-id="'+scheduleId+'"]');
            if (detailModal) {
                const memoDiv = detailModal.querySelector('.memo-content');
                if (memoDiv) {
                    memoDiv.innerHTML = data.memo ? data.memo.split('\n').map(line => `<div>${line}</div>`).join('') : '없음';
                }
            }
            renderSchedules();
        } else {
            log('ERROR', 'Failed to update memo', data);
            alert(data.detail || '메모 추가에 실패했습니다.');
        }
    } catch (error) {
        log('ERROR', 'Update memo error', error);
        alert('메모 추가 중 오류가 발생했습니다.');
    }
}

// User Filtering Functions <label for="user-${user.id}">${user.name}</label>

// 필터 상태 복원 함수
function restoreUserFilterState() {
    try {
        const savedCheckboxStates = localStorage.getItem('userCheckboxStates');
        if (savedCheckboxStates) {
            const activatedFilter = JSON.parse(savedCheckboxStates);
            console.log('🔍 [FILTER_RESTORE] 저장된 필터 상태:', activatedFilter);
            
            // selectedUsers Set 초기화
            selectedUsers.clear();
            
            if (activatedFilter.activated_id !== 'user-all') {
                // 사용자 ID 추출 (user-1 -> 1)
                const userId = activatedFilter.activated_id.replace('user-', '');
                if (!isNaN(userId)) {
                    selectedUsers.add(parseInt(userId));
                    console.log('🔍 [FILTER_RESTORE] 사용자 필터 복원됨:', userId);
                }
            } else {
                console.log('🔍 [FILTER_RESTORE] 모든 사용자 필터 복원됨');
            }
        }
    } catch (error) {
        console.error('🔍 [FILTER_RESTORE] 필터 상태 복원 오류:', error);
    }
}

async function loadUserCheckboxes() {
    const token = localStorage.getItem('token');
    if (!token) return;
    try {
        const response = await fetch('/users/', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            const users = await response.json();
            const container = document.getElementById('user-checkboxes');
            if (!container) return;
            container.innerHTML = ''; // Clear previous
            // "전체 사용자" 옵션 추가
            const allUsersDiv = document.createElement('div');
            allUsersDiv.className = 'user-checkbox';
            allUsersDiv.innerHTML = `
                <input type="checkbox" id="user-all" value="all" onchange="toggleAllUsersFilter(this.checked)" ${selectedUsers.size === 0 ? 'checked' : ''}>
                <label for="user-all">모든 사용자</label>
            `;
            container.appendChild(allUsersDiv);

            users.forEach(user => {
                if(user.name!="admin" && user.name!="viewer"){
                    const div = document.createElement('div');
                    div.className = 'user-checkbox';
                    div.innerHTML = `
                        <input type="checkbox" id="user-${user.id}" value="${user.id}" 
                            onchange="toggleUserFilter(${user.id}, this.checked)"
                            ${selectedUsers.has(user.id) ? 'checked' : ''}>
                        <label for="user-${user.id}">${user.name}</label>
                    `;
                    container.appendChild(div);
                }
            });
            
            // 체크박스 상태 동기화
            updateUserFilterCheckboxes();
        } else {
             log('ERROR', 'Failed to load users for filter', {status: response.status});
        }
    } catch (error) {
        log('ERROR', 'Load users filter error', error);
    }
}

function toggleAllUsersFilter(checked) {
    const userCheckboxes = document.querySelectorAll('#user-checkboxes input[type="checkbox"]:not(#user-all)');
    if (checked) {
        selectedUsers.clear();
        userCheckboxes.forEach(cb => cb.checked = false);
    }
    // "모든 사용자"가 체크되면 다른 필터는 의미 없음 (백엔드에서 user_ids 파라미터 없이 요청)
    // 만약 "모든 사용자" 체크 해제 시, 어떤 동작을 할지 정의 필요 (예: 이전에 선택된 사용자 복원 또는 아무것도 안함)
    // 여기서는 "모든 사용자" 체크 시 다른 사용자 선택 해제하고, selectedUsers 비움.
    refreshSchedules();
    updateUserFilterCheckboxes();
}

function toggleUserFilter(userId, checked) {
    if (checked) {
        selectedUsers.add(userId);
    } else {
        selectedUsers.delete(userId);
    }
    // 다른 사용자 필터가 선택되면 "모든 사용자"는 자동 해제
    const allUserCb = document.getElementById('user-all');
    if (allUserCb) allUserCb.checked = selectedUsers.size === 0;
    
    refreshSchedules();
    updateUserFilterCheckboxes(); // 체크박스 상태 동기화
}

function updateUserFilterCheckboxes() {
    const allUserCb = document.getElementById('user-all');
    if (allUserCb) {
        allUserCb.checked = selectedUsers.size === 0;
    }
    document.querySelectorAll('#user-checkboxes input[type="checkbox"]:not(#user-all)').forEach(cb => {
        cb.checked = selectedUsers.has(parseInt(cb.value));
    });
}


// --- ALARM FUNCTIONS ---
let alarmPollingInterval = null;
let alarms = [];

async function loadAlarms() {
    try {
        const response = await apiRequest('/alarms'); // API 엔드포인트 확인
        if (response.ok) {
            const alarmsData = await response.json();
            // 전역 alarms 변수 업데이트
            alarms = alarmsData || [];
            window.alarms = alarms; // window 객체에도 설정
            console.log('Alarms loaded:', alarms.length, 'alarms'); // 디버깅 로그
            renderAlarms();
        } else {
            log('ERROR', 'Failed to load alarms', {status: response.status});
            console.error('Failed to load alarms, status:', response.status);
            document.getElementById('alarm-list').innerHTML = '<p>알람을 불러오는데 실패했습니다.</p>';
        }
    } catch (error) {
        log('ERROR', 'Alarm load error', error);
        console.error('Alarm load error:', error);
        document.getElementById('alarm-list').innerHTML = '<p>알람 로딩 중 오류 발생.</p>';
    }
}

// renderAlarms 함수 수정 - 미확인 알람 체크 기능 추가
function renderAlarms() {
    const alarmListDiv = document.getElementById('alarm-list');
    if (!alarmListDiv) {
        console.warn('alarm-list element not found');
        return;
    }
    alarmListDiv.innerHTML = '';
    
    // 전역 alarms 변수 사용 (window.alarms도 동일)
    const currentAlarms = window.alarms || alarms || [];
    console.log('Rendering alarms:', currentAlarms.length, 'total alarms'); // 디버깅 로그
    
    // 미확인 알람 개수 체크
    const unackedCount = currentAlarms.filter(alarm => !alarm.is_acked).length;
    console.log('Unacked alarms count:', unackedCount); // 디버깅 로그
    updateAlarmIndicator(unackedCount);
    
    if (currentAlarms.length === 0) {
        alarmListDiv.innerHTML = '<div class="no-alarms">새로운 알람이 없습니다.</div>';
        return;
    }
    
    currentAlarms.slice().sort((a,b) => new Date(b.created_at) - new Date(a.created_at)).forEach(alarm => { // 최신순 정렬
        const alarmDiv = document.createElement('div');
        alarmDiv.className = `alarm-item ${alarm.type} ${alarm.is_acked ? 'acked' : 'unacked'}`;
        const createdDate = new Date(alarm.created_at);
        const year = createdDate.getFullYear();
        const month = (createdDate.getMonth() + 1).toString().padStart(2, '0');
        const day = createdDate.getDate().toString().padStart(2, '0');
        const hours = createdDate.getHours().toString().padStart(2, '0');
        const minutes = createdDate.getMinutes().toString().padStart(2, '0');
        const createdTime = `${year}-${month}-${day} ${hours}:${minutes}`;
        
        alarmDiv.innerHTML = `
            <div class="alarm-content">
                <span class="alarm-type-badge">${getAlarmTypeText(alarm.type)}</span>
                <span class="alarm-message">${alarm.message}</span>
                <span class="alarm-time">${createdTime}</span>
            </div>
            <div class="alarm-actions">
                ${!alarm.is_acked ? `<button onclick="ackAlarm(${alarm.id})" class="ack-btn" title="확인됨으로 표시">✔️</button>` : `<span class="acked-mark" title="확인됨">✅</span>`}
                <button onclick="deleteAlarm(${alarm.id})" class="delete-btn" title="알람 삭제">🗑️</button>
                ${alarm.schedule_id ? `<button onclick="goToSchedule(${alarm.schedule_id})" class="memo-link-btn">바로가기</button>` : ''}
            </div>
        `;
        alarmListDiv.appendChild(alarmDiv);
    });
    
    console.log('Alarms rendered successfully'); // 디버깅 로그
}

// 일정으로 이동하는 함수
function goToSchedule(scheduleId) {
    // 해당 일정의 테이블 행 찾기
    const scheduleRow = document.querySelector(`tr[data-schedule-id="${scheduleId}"]`);
    if (!scheduleRow) {
        // data-schedule-id 속성이 없는 경우, 일정 목록에서 해당 ID를 가진 일정 찾기
        const schedule = window.schedules.find(s => s.id === scheduleId);
        if (schedule) {
            // 일정 모달 열기
            handleScheduleClick(schedule);
            // 스크롤 위치 조정
            const scheduleContainer = document.querySelector('.schedule-container');
            if (scheduleContainer) {
                const scheduleIndex = window.schedules.findIndex(s => s.id === scheduleId);
                if (scheduleIndex !== -1) {
                    const rowHeight = 40; // 예상되는 행 높이
                    const scrollPosition = scheduleIndex * rowHeight;
                    scheduleContainer.scrollTo({
                        top: scrollPosition,
                        behavior: 'smooth'
                    });
                }
            }
        }
    } else {
        // 행이 있는 경우 해당 행으로 스크롤
        scheduleRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // 일정 모달 열기
        const schedule = window.schedules.find(s => s.id === scheduleId);
        if (schedule) {
            handleScheduleClick(schedule);
        }
    }
}

// 새로운 함수: 알람 인디케이터 업데이트
function updateAlarmIndicator(unackedCount) {
    const alarmCollapsible = document.getElementById('alarm-collapsible');
    const alarmHeaderCollapsible = alarmCollapsible?.querySelector('.alarm-header-collapsible');
    
    if (!alarmHeaderCollapsible) return;
    
    // 기존 인디케이터 제거
    const existingIndicator = alarmHeaderCollapsible.querySelector('.unacked-indicator');
    if (existingIndicator) {
        existingIndicator.remove();
    }
    
    if (unackedCount > 0) {
        // 미확인 알람 개수 표시
        const indicator = document.createElement('span');
        indicator.className = 'unacked-indicator';
        indicator.textContent = unackedCount;
        
        const h3 = alarmHeaderCollapsible.querySelector('h3');
        h3.appendChild(indicator);
        
        // 깜빡임 효과 시작
        alarmCollapsible.classList.add('has-unacked-alarms');
    } else {
        // 깜빡임 효과 제거
        alarmCollapsible.classList.remove('has-unacked-alarms');
    }
}

function getAlarmTypeText(type) {
    const map = { 'schedule_due': '일정', 'memo': '새메모', 'share': '공유됨', 'completion_request': '완료요청', 'new_schedule': '새일정' };
    return map[type] || type;
}

// ackAlarm과 deleteAlarm 함수 수정하여 인디케이터 업데이트
async function ackAlarm(alarmId) {
    const token = localStorage.getItem('token');
    if (!token) return;
    try {
        const response = await fetch(`/ack_alarms/${alarmId}/ack`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            await loadAlarms(); // 목록 새로고침 (renderAlarms에서 인디케이터도 업데이트됨)
        } else {
            log('ERROR', 'Failed to ack alarm', {status: response.status});
            alert('알람 확인 처리에 실패했습니다.');
        }
    } catch (error) {
        log('ERROR', 'Ack alarm error', error);
        alert('알람 확인 처리 중 오류 발생.');
    }
}



async function deleteAlarm(alarmId) {
    // 확인 없이 바로 삭제 또는 confirm 추가
    const token = localStorage.getItem('token');
    if (!token) return;
    try {
        const response = await fetch(`/delete_alarms/${alarmId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            await loadAlarms(); // 목록 새로고침 (renderAlarms에서 인디케이터도 업데이트됨)
        } else {
            log('ERROR', 'Failed to delete alarm', {status: response.status});
            alert('알람 삭제에 실패했습니다.');
        }
    } catch (error) {
        log('ERROR', 'Delete alarm error', error);
        alert('알람 삭제 중 오류 발생.');
    }
}

async function clearAllAlarms() {
    if (!confirm('모든 알람을 삭제하시겠습니까?')) return;
    
    try {
        const response = await apiRequest('/clear_alarms/clear', { // 엔드포인트 확인 /clear_alarms/clear 또는 /alarms/clear_all
            method: 'DELETE'
        });
        
        if (response.ok) {
            await loadAlarms(); // 알람 목록 새로고침
        } else {
            const error = await response.json();
            alert(error.detail || '알람 삭제에 실패했습니다.');
        }
    } catch (error) {
        log('ERROR', 'Clear all alarms error', error);
        alert('알람 삭제 중 오류가 발생했습니다.');
    }
}

function startAlarmPolling() {
    stopAlarmPolling(); // 기존 인터벌이 있다면 중지
    loadAlarms(); // 즉시 한번 로드
    alarmPollingInterval = setInterval(loadAlarms, 30000); // 30초마다
    log('INFO', 'Alarm polling started.');
    console.log('Alarm polling started - will check every 30 seconds'); // 디버깅 로그
}

function stopAlarmPolling() {
    if (alarmPollingInterval) {
        clearInterval(alarmPollingInterval);
        alarmPollingInterval = null;
        log('INFO', 'Alarm polling stopped.');
        console.log('Alarm polling stopped'); // 디버깅 로그
    }
}

// 디버깅 함수들 추가
window.debugAlarms = function() {
    console.log('=== ALARM DEBUG INFO ===');
    console.log('Global alarms variable:', alarms);
    console.log('Window alarms variable:', window.alarms);
    console.log('Alarm polling interval:', alarmPollingInterval);
    console.log('Alarm list element:', document.getElementById('alarm-list'));
    console.log('Alarm collapsible element:', document.getElementById('alarm-collapsible'));
    
    // 수동으로 알람 로드 테스트
    console.log('Testing manual alarm load...');
    loadAlarms();
};

window.manualLoadAlarms = function() {
    console.log('Manual alarm load triggered');
    loadAlarms();
};

window.manualRenderAlarms = function() {
    console.log('Manual alarm render triggered');
    renderAlarms();
};

// --- BROWSER NOTIFICATIONS (for schedule due times) ---
// (이 부분은 백업 파일에 있던 setInterval(checkScheduleAlarms, 60000)과 유사)
function checkScheduleAlarmsForNotification() {
    const now = new Date();
    const koreaTimeOffset = 9 * 60 * 60 * 1000;
    const koreaNow = new Date(now.getTime() + koreaTimeOffset);
    window.schedules.forEach(schedule => {
        if (schedule.alarm_time && !schedule.is_completed) {
            const alarmTime = new Date(schedule.alarm_time);
            // 알람 시간이 현재 시간 이전이고, 마지막 알림 체크 시간보다 이후인 경우 알림 (중복 방지)
            if (alarmTime <= koreaNow && (!schedule.last_notified_at || new Date(schedule.last_notified_at) < alarmTime)) {
                showBrowserNotification('일정 알림: ' + schedule.title, schedule.content || '세부 내용 없음');
                schedule.last_notified_at = koreaNow.toISOString(); // 알림 발생 시간 기록 (클라이언트 사이드)
            }
        }
    });
}

function showBrowserNotification(title, body) {
    if (!("Notification" in window)) {
        log('WARN', 'Browser does not support notifications.');
        return;
    }
    if (Notification.permission === "granted") {
        new Notification(title, { body, icon: '/icon.png' }); // 아이콘 경로 추가 가능
    } else if (Notification.permission !== "denied") {
        Notification.requestPermission().then(permission => {
            if (permission === "granted") {
                new Notification(title, { body, icon: '/icon.png' });
            }
        });
    }
}
// 페이지 로드 시 알림 권한 요청 (선택적)
// document.addEventListener('DOMContentLoaded', () => {
//     if (Notification.permission !== "granted" && Notification.permission !== "denied") {
//         Notification.requestPermission();
//     }
// });


// Global Error Handlers
window.addEventListener('error', (event) => {
    log('ERROR', 'Global error caught', {
        message: event.message, filename: event.filename,
        lineno: event.lineno, colno: event.colno, error: event.error
    });
});
window.addEventListener('unhandledrejection', (event) => {
    log('ERROR', 'Unhandled promise rejection', { reason: event.reason });
});

// 테스트용: 모든 일정 삭제 함수
async function deleteAllSchedules() {
    if (!confirm('정말로 모든 일정을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) return;
    
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
        // 먼저 모든 일정 목록을 가져옵니다
        const response = await fetch('/schedules/', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (!response.ok) {
            throw new Error('일정 목록을 가져오는데 실패했습니다.');
        }
        
        const schedules = await response.json();
        
        // 각 일정을 순차적으로 삭제
        for (const schedule of schedules) {
            const deleteResponse = await fetch(`/schedules/${schedule.id}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (!deleteResponse.ok) {
                console.error(`일정 ID ${schedule.id} 삭제 실패`);
            }
        }
        
        // 일정 목록 새로고침
        await refreshSchedules();
        alert('모든 일정이 삭제되었습니다.');
        
    } catch (error) {
        log('ERROR', 'Delete all schedules error', error);
        alert('일정 삭제 중 오류가 발생했습니다.');
    }
}

// 테스트용: 모든 일정 삭제 버튼 추가
function addDeleteAllButton() {
    const controls = document.querySelector('.controls');
    if (!controls) return;
    
    const deleteAllButton = document.createElement('button');
    deleteAllButton.textContent = '모든 일정 삭제';
    deleteAllButton.onclick = deleteAllSchedules;
    deleteAllButton.style.backgroundColor = '#dc3545'; // 빨간색 배경
    deleteAllButton.style.color = 'white';
    deleteAllButton.style.marginLeft = '10px';
    
    controls.appendChild(deleteAllButton);
}

async function loadProjectList(inputId = 'schedule-project', listId = 'project-list') {
    try {
        const response = await apiRequest('/projects/');
        if (response.ok) {
            const projects = await response.json();
            
            const projectInput = document.getElementById(inputId);
            const projectList = document.getElementById(listId);
            
            if (!projectInput || !projectList) return;
            
            // 기존 옵션들 제거
            projectList.innerHTML = '';
            
            // 프로젝트 목록을 datalist에 추가
            projects.forEach(project => {
                const option = document.createElement('option');
                option.value = project.name;
                projectList.appendChild(option);
            });
        }
    } catch (error) {
        log('ERROR', 'Failed to load project list', error);
    }
}


async function exportToExcel() {
    // 기존 함수를 새로운 모달 표시 함수로 변경
    showExcelExportModal();
}

// 엑셀 출력 모달 표시
function showExcelExportModal() {
    const modal = document.getElementById('excel-export-modal');
    modal.style.display = 'block';
    
    // 기본 날짜 설정: 지난 1개월 + 앞으로 6개월
    const today = new Date();
    const oneMonthAgo = new Date(today);
    oneMonthAgo.setMonth(today.getMonth() - 1);
    const sixMonthsLater = new Date(today);
    sixMonthsLater.setMonth(today.getMonth() + 6);
    
    document.getElementById('export-start-date').value = oneMonthAgo.toISOString().split('T')[0];
    document.getElementById('export-end-date').value = sixMonthsLater.toISOString().split('T')[0];
    
    // 폼 이벤트 리스너 설정
    const form = document.getElementById('excel-export-form');
    form.onsubmit = handleExcelExport;
}

// 엑셀 출력 모달 닫기
function closeExcelExportModal() {
    const modal = document.getElementById('excel-export-modal');
    modal.style.display = 'none';
}

// 날짜 범위 조정 함수
function adjustDateRange(days, target) {
    const startDateInput = document.getElementById('export-start-date');
    const endDateInput = document.getElementById('export-end-date');
    
    if (target === 'start') {
        const currentDate = startDateInput.value ? new Date(startDateInput.value) : new Date();
        const newDate = new Date(currentDate);
        newDate.setDate(currentDate.getDate() + days);
        startDateInput.value = newDate.toISOString().split('T')[0];
    } else if (target === 'end') {
        const currentDate = endDateInput.value ? new Date(endDateInput.value) : new Date();
        const newDate = new Date(currentDate);
        newDate.setDate(currentDate.getDate() + days);
        endDateInput.value = newDate.toISOString().split('T')[0];
    }
}

// 엑셀 출력 요청 처리
async function handleExcelExport(e) {
    e.preventDefault();
    
    const token = localStorage.getItem('token');
    if (!token) {
        alert('로그인이 필요합니다.');
        return;
    }

    try {
        // 로딩 표시
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'loading-overlay';
        loadingDiv.innerHTML = '<div class="loading-spinner"></div><div>엑셀 파일 생성 중...</div>';
        document.body.appendChild(loadingDiv);

        // 폼 데이터 수집
        const formData = new FormData(e.target);
        const exportOptions = {
            start_date: document.getElementById('export-start-date').value,
            end_date: document.getElementById('export-end-date').value,
            include_individual: formData.get('individual-schedule') === 'include',
            export_by_project: document.getElementById('export-by-project').checked,
            export_by_author: document.getElementById('export-by-author').checked,
            export_by_month: document.getElementById('export-by-month').checked,
            export_by_week: document.getElementById('export-by-week').checked,
            export_by_priority: document.getElementById('export-by-priority').checked
        };

        // URL 파라미터 생성
        const params = new URLSearchParams();
        Object.entries(exportOptions).forEach(([key, value]) => {
            if (value !== null && value !== undefined) {
                params.append(key, value);
            }
        });

        const response = await fetch(`/schedules/export/excel?${params}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '엑셀 파일 생성에 실패했습니다.');
        }

        // Content-Type 확인하여 ZIP 파일인지 Excel 파일인지 구분
        const contentType = response.headers.get('content-type');
        const contentDisposition = response.headers.get('content-disposition');
        
        let filename = `schedules_export_${new Date().toISOString().split('T')[0]}`;
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="([^"]+)"/);
            if (filenameMatch) {
                filename = filenameMatch[1];
            }
        } else {
            // 파일 형식에 따라 확장자 설정
            filename += contentType.includes('zip') ? '.zip' : '.xlsx';
        }

        // 파일 다운로드
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        // 모달 닫기
        closeExcelExportModal();

    } catch (error) {
        console.error('Export error:', error);
        alert(error.message || '엑셀 파일 생성 중 오류가 발생했습니다.');
    } finally {
        // 로딩 표시 제거
        const loadingDiv = document.querySelector('.loading-overlay');
        if (loadingDiv) {
            document.body.removeChild(loadingDiv);
        }
    }
}

// 모달 외부 클릭시 닫기
window.onclick = function(event) {
    const modal = document.getElementById('excel-export-modal');
    if (event.target === modal) {
        closeExcelExportModal();
    }
}



function toggleEditProjectList() {
    const projectList = document.getElementById('edit-project-list');
    if (projectList) {
        projectList.style.display = projectList.style.display === 'none' ? 'block' : 'none';
    }
}

// 달력 보기 버튼 이벤트 핸들러
function setupCalendarViewButtons() {
    const monthViewBtn = document.getElementById('month-view-btn');
    const weekViewBtn = document.getElementById('week-view-btn');
    const totalViewBtn = document.getElementById('total-view-btn');
    const quickMemoViewBtn = document.getElementById('quickMemo-view-btn');
    
    if (monthViewBtn) {
        monthViewBtn.addEventListener('click', () => {
            window.location.href = '/static/calendar-monthly.html';
        });
    }
    
    if (weekViewBtn) {
        weekViewBtn.addEventListener('click', () => {
            window.location.href = '/static/calendar-weekly.html';
        });
    }
    
    if (totalViewBtn) {
        totalViewBtn.addEventListener('click', () => {
            window.location.href = '/static/totalview.html';
        });
    }
    
    if (quickMemoViewBtn) {
        quickMemoViewBtn.addEventListener('click', () => {
            window.location.href = '/static/quicknote.html';
        });
    }
}

function initializeApp() {
    // 사용자 정보 표시
    const username = localStorage.getItem('username');
    if (username) {
        const userInfoElement = document.querySelector('.user-info');
        if (userInfoElement) {
            userInfoElement.textContent = `\u00a0\u00a0\u00a0${username}`;
        }
    }

    // 이벤트 리스너 설정
    setupEventListeners();
    
    // 컨트롤 버튼 설정
    setupControlButtons();
    
    // 캘린더 뷰 버튼 설정
    setupCalendarViewButtons();
}

function setupEventListeners() {
    // 검색 이벤트
    const searchInput = document.getElementById('searchInput');
    const searchButton = document.getElementById('searchButton');
    
    if (searchInput && searchButton) {
        searchButton.addEventListener('click', () => {
            const searchTerm = searchInput.value.trim();
            if (searchTerm) {
                searchSchedules(searchTerm);
            }
        });

        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const searchTerm = searchInput.value.trim();
                if (searchTerm) {
                    searchSchedules(searchTerm);
                }
            }
        });
    }

    // 일정 추가 버튼
    const addScheduleBtn = document.getElementById('addScheduleBtn');
    if (addScheduleBtn) {
        addScheduleBtn.addEventListener('click', () => {
            showScheduleModal();
        });
    }

    
}

function setupControlButtons() {
    // 완료된 일정 토글 버튼
    const toggleCompletedBtn = document.getElementById('toggleCompletedBtn');
    if (toggleCompletedBtn) {
        toggleCompletedBtn.addEventListener('click', () => {
            showCompleted = !showCompleted;
            updateToggleCompletedButtonText();
            main_loadSchedules();
        });
    }

    // 파일 보기 버튼
    const viewFilesBtn = document.getElementById('viewFilesBtn');
    if (viewFilesBtn) {
        viewFilesBtn.addEventListener('click', () => {
            window.location.href = '/static/files.html';
        });
    }

    // 엑셀 내보내기 버튼
    const exportExcelBtn = document.getElementById('exportExcelBtn');
    if (exportExcelBtn) {
        exportExcelBtn.addEventListener('click', exportToExcel);
    }
}

// 수정 폼용 알람시간 자동 업데이트
async function updateAlarmTimeOnDueTimeChangeForEdit() {
    const dueTimeInput = document.getElementById('edit-due-time');
    const alarmTimeInput = document.getElementById('edit-alarm-time');
    
    if (!dueTimeInput || !alarmTimeInput || !dueTimeInput.value) return;
    
    const dueTime = new Date(dueTimeInput.value);
    if (isNaN(dueTime.getTime())) return;
    
    // 알람 시간을 마감시간보다 1시간 전으로 설정
    const alarmTime = new Date(dueTime.getTime() - (1 * 60 * 60 * 1000));
    alarmTimeInput.value = alarmTime.toISOString().slice(0, 16);
}

// 파일 타입 처리 유틸리티 함수들
function isImageFile(filename, mimeType) {
    if (mimeType && mimeType.startsWith('image/')) {
        return true;
    }
    const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'];
    const extension = filename.toLowerCase().substr(filename.lastIndexOf('.'));
    return imageExtensions.includes(extension);
}

function getFileExtension(filename) {
    return filename.toLowerCase().substr(filename.lastIndexOf('.') + 1);
}

function getFileIcon(filename, mimeType) {
    const extension = getFileExtension(filename);
    
    // 이미지 파일
    if (isImageFile(filename, mimeType)) {
        return '<i class="fas fa-image"></i>';
    }
    
    // 문서 파일들
    const fileIcons = {
        // Microsoft Office
        'doc': '<i class="fas fa-file-word"></i>', 
        'docx': '<i class="fas fa-file-word"></i>',
        'xls': '<i class="fas fa-file-excel"></i>', 
        'xlsx': '<i class="fas fa-file-excel"></i>',
        'ppt': '<i class="fas fa-file-powerpoint"></i>', 
        'pptx': '<i class="fas fa-file-powerpoint"></i>',
        
        // PDF
        'pdf': '<i class="fas fa-file-pdf"></i>',
        
        // 텍스트 파일들
        'txt': '<i class="fas fa-file-alt"></i>', 
        'md': '<i class="fab fa-markdown"></i>', 
        'rtf': '<i class="fas fa-file-alt"></i>',
        
        // 코드 파일들
        'js': '<i class="fab fa-js-square"></i>', 
        'html': '<i class="fab fa-html5"></i>', 
        'css': '<i class="fab fa-css3-alt"></i>', 
        'py': '<i class="fab fa-python"></i>', 
        'java': '<i class="fab fa-java"></i>',
        'cpp': '<i class="fas fa-file-code"></i>', 
        'c': '<i class="fas fa-file-code"></i>', 
        'php': '<i class="fab fa-php"></i>', 
        'rb': '<i class="fas fa-gem"></i>', 
        'go': '<i class="fas fa-file-code"></i>',
        'ts': '<i class="fas fa-file-code"></i>', 
        'jsx': '<i class="fab fa-react"></i>', 
        'vue': '<i class="fab fa-vuejs"></i>', 
        'sql': '<i class="fas fa-database"></i>',
        
        // 압축 파일들
        'zip': '<i class="fas fa-file-archive"></i>', 
        'rar': '<i class="fas fa-file-archive"></i>', 
        '7z': '<i class="fas fa-file-archive"></i>', 
        'tar': '<i class="fas fa-file-archive"></i>', 
        'gz': '<i class="fas fa-file-archive"></i>',
        
        // 비디오 파일들
        'mp4': '<i class="fas fa-file-video"></i>', 
        'avi': '<i class="fas fa-file-video"></i>', 
        'mov': '<i class="fas fa-file-video"></i>', 
        'wmv': '<i class="fas fa-file-video"></i>', 
        'flv': '<i class="fas fa-file-video"></i>',
        'mkv': '<i class="fas fa-file-video"></i>', 
        'webm': '<i class="fas fa-file-video"></i>', 
        'm4v': '<i class="fas fa-file-video"></i>',
        
        // 오디오 파일들
        'mp3': '<i class="fas fa-file-audio"></i>', 
        'wav': '<i class="fas fa-file-audio"></i>', 
        'flac': '<i class="fas fa-file-audio"></i>', 
        'aac': '<i class="fas fa-file-audio"></i>', 
        'ogg': '<i class="fas fa-file-audio"></i>',
        'm4a': '<i class="fas fa-file-audio"></i>', 
        'wma': '<i class="fas fa-file-audio"></i>',
        
        // 실행 파일들
        'exe': '<i class="fas fa-cog"></i>', 
        'msi': '<i class="fas fa-cog"></i>', 
        'app': '<i class="fas fa-mobile-alt"></i>', 
        'deb': '<i class="fab fa-ubuntu"></i>', 
        'rpm': '<i class="fab fa-redhat"></i>',
        
        // 데이터 파일들
        'json': '<i class="fas fa-code"></i>', 
        'xml': '<i class="fas fa-code"></i>', 
        'csv': '<i class="fas fa-file-csv"></i>', 
        'yaml': '<i class="fas fa-code"></i>', 
        'yml': '<i class="fas fa-code"></i>',
        
        // 폰트 파일들
        'ttf': '<i class="fas fa-font"></i>', 
        'otf': '<i class="fas fa-font"></i>', 
        'woff': '<i class="fas fa-font"></i>', 
        'woff2': '<i class="fas fa-font"></i>',
        
        // 기타
        'iso': '<i class="fas fa-compact-disc"></i>', 
        'dmg': '<i class="fas fa-compact-disc"></i>', 
        'bin': '<i class="fas fa-compact-disc"></i>'
    };
    
    return fileIcons[extension] || '<i class="fas fa-file"></i>'; // 기본 아이콘
}

function createFileThumbnail(filename, filepath, mimeType) {
    if (isImageFile(filename, mimeType)) {
        return `<div class="file-thumbnail">
            <img src="${filepath}" alt="${filename}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
            <div class="file-icon-fallback" style="display:none;">${getFileIcon(filename, mimeType)}</div>
            <span class="attachment-type">${getFileExtension(filename).toUpperCase()}</span>
        </div>`;
    } else {
        return `<div class="file-thumbnail">
            <div class="file-icon">${getFileIcon(filename, mimeType)}</div>
        </div>`;
    }
}

function downloadFile(filePath) {
    // 파일 다운로드를 위한 임시 링크 생성
    const link = document.createElement('a');
    link.href = filePath;
    link.download = filePath.split('/').pop(); // 파일명만 추출
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Schedule Interface Functions
function showScheduleInterface() {
    log('INFO', 'showScheduleInterface 시작');
    if (!authContainer) {
        log('ERROR', 'authContainer not found');
        return;
    }
    
    loadUserCheckboxes();
    loadAlarms();
    setupInfiniteScroll();
    updateToggleCompletedButtonText();
    main_loadSchedules(); // 초기 일정 로드 추가
}

// 공동 작업자 관련 함수들
let collaboratorsSearchTimeout = null;
let allUsers = [];

// 현재 로그인한 사용자 ID 가져오기
function getCurrentUserId() {
    try {
        const token = localStorage.getItem('token');
        if (!token) return null;
        
        const decoded = decodeJWTToken(token);
        if (!decoded || !decoded.sub) return null;
        
        // JWT 토큰에서 사용자 정보를 가져와서 ID 찾기
        const username = decoded.sub;
        const currentUser = allUsers.find(user => user.username === username);
        return currentUser ? currentUser.id : null;
    } catch (error) {
        log('ERROR', '현재 사용자 ID 가져오기 실패', error);
        return null;
    }
}

// 사용자 목록 로드
async function loadUsers() {
    console.log('👥 [USERS_LOAD] loadUsers 함수 호출 시작');
    try {
        console.log('🌐 [USERS_LOAD] /users/ API 호출 중...');
        const response = await apiRequest('/users/');
        console.log(`🌐 [USERS_LOAD] API 응답: ${response.status} ${response.statusText}`);
        
        if (response.ok) {
            allUsers = await response.json();
            console.log(`✅ [USERS_LOAD] 사용자 ${allUsers.length}명 로드 완료`);
            console.log(`👥 [USERS_LOAD] 로드된 사용자들:`, allUsers.map(u => `${u.username} (${u.name}) - ID: ${u.id}`));
            
            // 사용자 로드 완료 후 드롭다운 즉시 업데이트
            const collaboratorsSelect = document.getElementById('schedule-collaborators');
            if (collaboratorsSelect) {
                console.log('🔄 [USERS_LOAD] collaboratorsSelect 요소 발견, 드롭다운 업데이트 실행');
                updateCollaboratorsDropdown('');
            } else {
                console.log('ℹ️ [USERS_LOAD] collaboratorsSelect 요소를 찾을 수 없음 (폼이 아직 로드되지 않음)');
            }
        } else {
            console.error('❌ [USERS_LOAD] 사용자 목록 로드 실패:', response.status, response.statusText);
            log('ERROR', '사용자 목록 로드 실패');
        }
    } catch (error) {
        console.error('❌ [USERS_LOAD] 사용자 목록 로드 중 오류 발생:', error);
        log('ERROR', '사용자 목록 로드 실패', error);
    }
}

// 사용자 검색 및 필터링
function searchUsers(searchTerm) {
    console.log(`🔍 [USERS_SEARCH] searchUsers 호출 - searchTerm: "${searchTerm}"`);
    
    // admin, viewer만 제외 (자기 자신은 포함)
    const currentUserId = getCurrentUserId();
    console.log(`🔍 [USERS_SEARCH] 현재 사용자 ID: ${currentUserId}`);
    
    const filteredUsers = allUsers.filter(user => 
        user.username !== 'admin' && 
        user.username !== 'viewer'
    );
    
    console.log(`🔍 [USERS_SEARCH] 필터링 전 사용자 수: ${allUsers.length}`);
    console.log(`🔍 [USERS_SEARCH] admin/viewer/자기자신 제외 후 사용자 수: ${filteredUsers.length}`);
    
    // 중복 사용자 제거 (username 기준으로 첫 번째만 유지)
    const uniqueUsers = [];
    const seenUsernames = new Set();
    
    filteredUsers.forEach(user => {
        if (!seenUsernames.has(user.username)) {
            seenUsernames.add(user.username);
            uniqueUsers.push(user);
        } else {
            console.log(`⚠️ [USERS_SEARCH] 중복 사용자 제거: ${user.username} (${user.name})`);
        }
    });
    
    console.log(`🔍 [USERS_SEARCH] 중복 제거 후 사용자 수: ${uniqueUsers.length}`);
    
    if (!searchTerm || searchTerm.trim() === '') {
        console.log(`🔍 [USERS_SEARCH] 검색어 없음, 전체 사용자 반환`);
        return uniqueUsers;
    }
    
    const term = searchTerm.toLowerCase();
    const searchResults = uniqueUsers.filter(user => 
        user.username.toLowerCase().includes(term) || 
        user.name.toLowerCase().includes(term)
    );
    
    console.log(`🔍 [USERS_SEARCH] 검색어 "${searchTerm}"에 대한 결과: ${searchResults.length}명`);
    console.log(`🔍 [USERS_SEARCH] 검색 결과:`, searchResults.map(u => `${u.username} (${u.name})`));
    
    return searchResults;
}

// 공동 작업자 검색 입력 이벤트 처리
function setupCollaboratorsSearch(formType = 'add') {
    const prefix = formType === 'edit' ? 'edit-' : '';
    const searchInput = document.getElementById(`${prefix}schedule-collaborators-search`);
    const collaboratorsSelect = document.getElementById(`${prefix}schedule-collaborators`);
    
    console.log(`🔍 [COLLABORATORS_SEARCH] setupCollaboratorsSearch 호출 - formType: ${formType}`);
    console.log(`🔍 [COLLABORATORS_SEARCH] searchInput:`, searchInput);
    console.log(`🔍 [COLLABORATORS_SEARCH] collaboratorsSelect:`, collaboratorsSelect);
    
    if (!searchInput || !collaboratorsSelect) {
        console.error(`❌ [COLLABORATORS_SEARCH] 필수 요소가 없음 - searchInput: ${!!searchInput}, collaboratorsSelect: ${!!collaboratorsSelect}`);
        return;
    }
    
    console.log(`✅ [COLLABORATORS_SEARCH] input 이벤트 리스너 추가`);
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.trim();
        console.log(`🔍 [COLLABORATORS_SEARCH] 검색 입력: "${searchTerm}"`);
        
        // 디바운싱 적용
        if (collaboratorsSearchTimeout) {
            clearTimeout(collaboratorsSearchTimeout);
            console.log(`⏱️ [COLLABORATORS_SEARCH] 기존 타임아웃 취소`);
        }
        
        collaboratorsSearchTimeout = setTimeout(() => {
            console.log(`🔍 [COLLABORATORS_SEARCH] 디바운싱 후 updateCollaboratorsDropdown 호출: "${searchTerm}"`);
            updateCollaboratorsDropdown(searchTerm, formType);
        }, 300);
    });
    
    // 검색 입력 필드가 비어있을 때 전체 사용자 목록 표시 (선택된 값들 유지)
    console.log(`✅ [COLLABORATORS_SEARCH] blur 이벤트 리스너 추가`);
    searchInput.addEventListener('blur', function() {
        if (this.value.trim() === '') {
            console.log(`🔍 [COLLABORATORS_SEARCH] 검색 필드가 비어있음, 전체 목록 표시 예정`);
            setTimeout(() => {
                console.log(`🔍 [COLLABORATORS_SEARCH] blur setTimeout 실행 - updateCollaboratorsDropdown 호출`);
                updateCollaboratorsDropdown('', formType);
            }, 100);
        }
    });
    
    console.log(`✅ [COLLABORATORS_SEARCH] setupCollaboratorsSearch 완료`);
}

// 공동 작업자 드롭다운 업데이트
function updateCollaboratorsDropdown(searchTerm, formType = 'add') {
    const prefix = formType === 'edit' ? 'edit-' : '';
    const collaboratorsSelect = document.getElementById(`${prefix}schedule-collaborators`);
    if (!collaboratorsSelect) {
        console.error(`❌ [COLLABORATORS_DROPDOWN] collaboratorsSelect 요소를 찾을 수 없음`);
        return;
    }
    
    console.log(`🔄 [COLLABORATORS_DROPDOWN] updateCollaboratorsDropdown 호출 - formType: ${formType}, searchTerm: "${searchTerm}"`);
    console.log(`🔄 [COLLABORATORS_DROPDOWN] 현재 select 요소:`, collaboratorsSelect);
    console.log(`🔄 [COLLABORATORS_DROPDOWN] select의 multiple 속성:`, collaboratorsSelect.multiple);
    
    // 현재 선택된 값들을 보존
    const currentlySelected = Array.from(collaboratorsSelect.selectedOptions).map(option => option.value);
    console.log(`🔄 [COLLABORATORS_DROPDOWN] 현재 선택된 값들:`, currentlySelected);
    console.log(`🔄 [COLLABORATORS_DROPDOWN] 현재 선택된 옵션 개수:`, collaboratorsSelect.selectedOptions.length);
    
    // 기존 옵션 제거 (첫 번째 안내 메시지 제외)
    const originalLength = collaboratorsSelect.children.length;
    console.log(`🔄 [COLLABORATORS_DROPDOWN] 기존 옵션 개수:`, originalLength);
    
    while (collaboratorsSelect.children.length > 1) {
        collaboratorsSelect.removeChild(collaboratorsSelect.lastChild);
    }
    console.log(`🔄 [COLLABORATORS_DROPDOWN] 옵션 제거 후 개수:`, collaboratorsSelect.children.length);
    
    const filteredUsers = searchUsers(searchTerm);
    console.log(`🔍 [COLLABORATORS_DROPDOWN] 필터링된 사용자 수:`, filteredUsers.length);
    console.log(`🔍 [COLLABORATORS_DROPDOWN] 필터링된 사용자들:`, filteredUsers.map(u => `${u.username} (${u.name})`));
    
    // 사용자가 있는 경우 안내 메시지 제거
    if (filteredUsers.length > 0) {
        if (collaboratorsSelect.children.length > 0) {
            collaboratorsSelect.removeChild(collaboratorsSelect.firstChild);
            console.log(`🔄 [COLLABORATORS_DROPDOWN] 안내 메시지 제거됨`);
        }
        
        // 필터링된 사용자들을 옵션으로 추가
        filteredUsers.forEach((user, index) => {
            const option = document.createElement('option');
            option.value = user.id;
            option.textContent = `${user.username} (${user.name})`;
            
            // 이전에 선택되었던 사용자인지 확인
            if (currentlySelected.includes(user.id.toString())) {
                option.selected = true;
                console.log(`✅ [COLLABORATORS_DROPDOWN] 사용자 ${user.username} 선택 상태 복원`);
            }
            
            collaboratorsSelect.appendChild(option);
            console.log(`➕ [COLLABORATORS_DROPDOWN] 옵션 추가: ${user.username} (${user.name}) - ID: ${user.id}`);
        });
        
        console.log(`✅ [COLLABORATORS_DROPDOWN] 총 ${filteredUsers.length}개 옵션 추가 완료`);
    } else {
        // 사용자가 없는 경우 안내 메시지 추가
        if (collaboratorsSelect.children.length === 0) {
            const noUsersOption = document.createElement('option');
            noUsersOption.value = '';
            noUsersOption.textContent = '검색 결과가 없습니다.';
            noUsersOption.disabled = true;
            collaboratorsSelect.appendChild(noUsersOption);
            console.log(`ℹ️ [COLLABORATORS_DROPDOWN] "검색 결과 없음" 메시지 추가`);
        }
    }
    
    // 선택된 공동 작업자 표시 업데이트
    updateSelectedCollaborators(formType);
    console.log(`🔄 [COLLABORATORS_DROPDOWN] updateCollaboratorsDropdown 완료`);
}

// 선택된 공동 작업자 표시
function updateSelectedCollaborators(formType = 'add') {
    const prefix = formType === 'edit' ? 'edit-' : '';
    const collaboratorsSelect = document.getElementById(`${prefix}schedule-collaborators`);
    const selectedContainer = document.getElementById(`${prefix}selected-collaborators`);
    
    console.log(`👥 [COLLABORATORS_DISPLAY] updateSelectedCollaborators 호출 - formType: ${formType}`);
    console.log(`👥 [COLLABORATORS_DISPLAY] select 요소:`, collaboratorsSelect);
    console.log(`👥 [COLLABORATORS_DISPLAY] selectedContainer:`, selectedContainer);
    
    if (!collaboratorsSelect || !selectedContainer) {
        console.error(`❌ [COLLABORATORS_DISPLAY] 필수 요소가 없음 - select: ${!!collaboratorsSelect}, container: ${!!selectedContainer}`);
        return;
    }
    
    const selectedOptions = Array.from(collaboratorsSelect.selectedOptions);
    console.log(`👥 [COLLABORATORS_DISPLAY] 선택된 옵션들:`, selectedOptions.map(opt => `${opt.value} (${opt.textContent})`));
    console.log(`👥 [COLLABORATORS_DISPLAY] 선택된 옵션 개수:`, selectedOptions.length);
    
    const selectedUsers = selectedOptions.map(option => {
        const user = allUsers.find(u => u.id == option.value);
        console.log(`👥 [COLLABORATORS_DISPLAY] 옵션 ${option.value}에 대한 사용자:`, user ? `${user.username} (${user.name})` : '사용자를 찾을 수 없음');
        return user ? { id: user.id, username: user.username, name: user.name } : null;
    }).filter(Boolean);
    
    console.log(`👥 [COLLABORATORS_DISPLAY] 최종 선택된 사용자들:`, selectedUsers.map(u => `${u.username} (${u.name}) - ID: ${u.id}`));
    
    if (selectedUsers.length === 0) {
        selectedContainer.innerHTML = '<span style="color: #666;">선택된 공동 작업자가 없습니다</span>';
        console.log(`ℹ️ [COLLABORATORS_DISPLAY] 선택된 사용자가 없음 - 빈 메시지 표시`);
        return;
    }
    
    const selectedHtml = selectedUsers.map(user => 
        `<span class="selected-collaborator">
            ${user.username} (${user.name})
            <button type="button" onclick="removeCollaborator(${user.id}, '${formType}')">×</button>
        </span>`
    ).join('');
    
    selectedContainer.innerHTML = selectedHtml;
    console.log(`✅ [COLLABORATORS_DISPLAY] 선택된 사용자 HTML 업데이트 완료 - ${selectedUsers.length}명`);
    console.log(`✅ [COLLABORATORS_DISPLAY] HTML 내용:`, selectedHtml);
}

// 공동 작업자 제거
function removeCollaborator(userId, formType = 'add') {
    const prefix = formType === 'edit' ? 'edit-' : '';
    const collaboratorsSelect = document.getElementById(`${prefix}schedule-collaborators`);
    
    console.log(`[DEBUG] removeCollaborator 호출 - userId: ${userId}, formType: ${formType}`);
    console.log(`[DEBUG] select 요소:`, collaboratorsSelect);
    
    if (!collaboratorsSelect) {
        console.log(`[DEBUG] select 요소를 찾을 수 없음`);
        return;
    }
    
    const option = collaboratorsSelect.querySelector(`option[value="${userId}"]`);
    console.log(`[DEBUG] 제거할 옵션:`, option);
    
    if (option) {
        console.log(`[DEBUG] 옵션 선택 해제 전 - selected: ${option.selected}`);
        option.selected = false;
        console.log(`[DEBUG] 옵션 선택 해제 후 - selected: ${option.selected}`);
        updateSelectedCollaborators(formType);
    } else {
        console.log(`[DEBUG] 제거할 옵션을 찾을 수 없음`);
    }
}

// 공동 작업자 선택 이벤트 설정
function setupCollaboratorsSelection(formType = 'add') {
    const prefix = formType === 'edit' ? 'edit-' : '';
    const collaboratorsSelect = document.getElementById(`${prefix}schedule-collaborators`);
    
    console.log(`👥 [COLLABORATORS_SELECTION] setupCollaboratorsSelection 호출 - formType: ${formType}`);
    console.log(`👥 [COLLABORATORS_SELECTION] collaboratorsSelect:`, collaboratorsSelect);
    
    if (!collaboratorsSelect) {
        console.error(`❌ [COLLABORATORS_SELECTION] select 요소를 찾을 수 없음`);
        return;
    }
    
    // 기존 이벤트 리스너 제거 (중복 방지)
    const newSelect = collaboratorsSelect.cloneNode(true);
    collaboratorsSelect.parentNode.replaceChild(newSelect, collaboratorsSelect);
    console.log(`🔄 [COLLABORATORS_SELECTION] 기존 select 요소를 새 요소로 교체하여 이벤트 리스너 중복 방지`);
    
    console.log(`✅ [COLLABORATORS_SELECTION] mousedown 이벤트 리스너 추가 (다중선택 지원)`);
    
    // mousedown 이벤트로 다중선택 처리
    newSelect.addEventListener('mousedown', (event) => {
        const targetOption = event.target;
        
        // 옵션이 아닌 경우 무시
        if (targetOption.tagName !== 'OPTION') {
            console.log(`ℹ️ [COLLABORATORS_SELECTION] mousedown 이벤트 - 옵션이 아닌 요소 클릭:`, targetOption.tagName);
            return;
        }
        
        console.log(`👥 [COLLABORATORS_SELECTION] mousedown 이벤트 - 옵션: ${targetOption.value}, 현재 선택됨: ${targetOption.selected}`);
        console.log(`👥 [COLLABORATORS_SELECTION] 옵션 텍스트: "${targetOption.textContent}"`);
        
        // Ctrl/Cmd 키가 눌려있지 않은 경우에만 커스텀 처리
        if (!event.ctrlKey && !event.metaKey) {
            event.preventDefault();
            console.log(`👥 [COLLABORATORS_SELECTION] Ctrl/Cmd 키가 눌리지 않음, 커스텀 처리 실행`);
            
            // 현재 선택된 모든 옵션들
            const currentSelected = Array.from(newSelect.selectedOptions);
            console.log(`👥 [COLLABORATORS_SELECTION] 현재 선택된 옵션들:`, currentSelected.map(opt => `${opt.value} (${opt.textContent})`));
            
            // 클릭된 옵션이 이미 선택되어 있는지 확인
            const isAlreadySelected = targetOption.selected;
            
            if (isAlreadySelected) {
                // 이미 선택된 옵션이면 선택 해제
                console.log(`👥 [COLLABORATORS_SELECTION] 옵션 ${targetOption.value} (${targetOption.textContent}) 선택 해제`);
                targetOption.selected = false;
            } else {
                // 선택되지 않은 옵션이면 선택 추가 (기존 선택 유지)
                console.log(`👥 [COLLABORATORS_SELECTION] 옵션 ${targetOption.value} (${targetOption.textContent}) 선택 추가`);
                targetOption.selected = true;
            }
            
            // 선택 상태 업데이트
            setTimeout(() => {
                console.log(`🔄 [COLLABORATORS_SELECTION] 선택 상태 변경 후 updateSelectedCollaborators 호출`);
                updateSelectedCollaborators(formType);
            }, 10);
        } else {
            console.log(`👥 [COLLABORATORS_SELECTION] Ctrl/Cmd 키가 눌림, 기본 다중선택 동작 허용`);
        }
    });
    
    // change 이벤트도 유지 (Ctrl/Cmd 키를 사용한 경우를 위해)
    console.log(`✅ [COLLABORATORS_SELECTION] change 이벤트 리스너 추가`);
    newSelect.addEventListener('change', (event) => {
        console.log(`🔄 [COLLABORATORS_SELECTION] change 이벤트 발생!`);
        console.log(`🔄 [COLLABORATORS_SELECTION] 이벤트 타겟:`, event.target);
        console.log(`🔄 [COLLABORATORS_SELECTION] 선택된 옵션 개수:`, event.target.selectedOptions.length);
        console.log(`🔄 [COLLABORATORS_SELECTION] 선택된 값들:`, Array.from(event.target.selectedOptions).map(option => `${option.value} (${option.textContent})`));
        updateSelectedCollaborators(formType);
    });
    
    console.log(`✅ [COLLABORATORS_SELECTION] setupCollaboratorsSelection 완료`);
}

// 기존 공동 작업자 정보 로드
async function loadExistingCollaborators(scheduleId, formType) {
    try {
        const response = await apiRequest(`/schedules/${scheduleId}/collaborators`);
        if (response.ok) {
            const collaborators = await response.json();
            setSelectedCollaborators(collaborators, formType);
        } else {
            // API가 아직 구현되지 않았거나 오류가 발생한 경우 무시
            log('INFO', 'Collaborators API not available yet, skipping');
        }
    } catch (error) {
        // API가 아직 구현되지 않은 경우 무시
        log('INFO', 'Collaborators API not available yet, skipping');
    }
}

// 선택된 공동 작업자 설정
function setSelectedCollaborators(collaborators, formType) {
    const prefix = formType === 'edit' ? 'edit-' : '';
    const collaboratorsSelect = document.getElementById(`${prefix}schedule-collaborators`);
    
    console.log(`[DEBUG] setSelectedCollaborators 호출 - collaborators:`, collaborators, `formType: ${formType}`);
    console.log(`[DEBUG] select 요소:`, collaboratorsSelect);
    
    if (!collaboratorsSelect) {
        console.log(`[DEBUG] select 요소를 찾을 수 없음`);
        return;
    }
    
    console.log(`[DEBUG] 설정 전 선택된 옵션 개수:`, collaboratorsSelect.selectedOptions.length);
    
    // 모든 옵션 선택 해제
    Array.from(collaboratorsSelect.options).forEach(option => {
        option.selected = false;
    });
    console.log(`[DEBUG] 모든 옵션 선택 해제 완료`);
    
    // 기존 공동 작업자 선택
    collaborators.forEach(collaborator => {
        const option = collaboratorsSelect.querySelector(`option[value="${collaborator.user_id}"]`);
        console.log(`[DEBUG] collaborator ${collaborator.user_id}에 대한 옵션:`, option);
        if (option) {
            option.selected = true;
            console.log(`[DEBUG] 옵션 ${collaborator.user_id} 선택됨`);
        } else {
            console.log(`[DEBUG] 옵션 ${collaborator.user_id}를 찾을 수 없음`);
        }
    });
    
    console.log(`[DEBUG] 설정 후 선택된 옵션 개수:`, collaboratorsSelect.selectedOptions.length);
    
    // 선택된 공동 작업자 표시 업데이트
    updateSelectedCollaborators(formType);
    
    // 드롭다운에 사용자가 없는 경우, 사용자 목록을 다시 로드하여 선택 상태 설정
    if (collaborators.length > 0) {
        console.log(`[DEBUG] setTimeout으로 updateCollaboratorsDropdown 호출 예정`);
        setTimeout(() => {
            console.log(`[DEBUG] setTimeout 실행 - updateCollaboratorsDropdown 호출`);
            updateCollaboratorsDropdown('', formType);
        }, 100);
    }
}

// 공동 작업자 기능 초기화
function initializeCollaborators(formType = 'add') {
    const prefix = formType === 'edit' ? 'edit-' : '';
    
    console.log(`[DEBUG] initializeCollaborators 호출 - formType: ${formType}`);
    
    loadUsers().then(() => {
        console.log(`[DEBUG] 사용자 로드 완료, 드롭다운 초기화 시작`);
        
        // 사용자 로드 완료 후 드롭다운 초기화
        updateCollaboratorsDropdown('', formType);
        setupCollaboratorsSearch(formType);
        setupCollaboratorsSelection(formType);
        
        // 수정 모드인 경우, 기존 선택된 값들이 유지되도록 추가 처리
        if (formType === 'edit') {
            console.log(`[DEBUG] 수정 모드 - 기존 선택된 값들 유지 처리`);
            const collaboratorsSelect = document.getElementById(`${prefix}schedule-collaborators`);
            console.log(`[DEBUG] 수정 모드 select 요소:`, collaboratorsSelect);
            if (collaboratorsSelect && collaboratorsSelect.selectedOptions.length > 0) {
                console.log(`[DEBUG] 기존 선택된 옵션이 있음, setTimeout으로 updateSelectedCollaborators 호출 예정`);
                setTimeout(() => {
                    console.log(`[DEBUG] setTimeout 실행 - updateSelectedCollaborators 호출`);
                    updateSelectedCollaborators(formType);
                }, 200);
            } else {
                console.log(`[DEBUG] 기존 선택된 옵션이 없음`);
            }
        }
        
        console.log(`[DEBUG] initializeCollaborators 완료`);
    });
}

// 퀵노트 보기 함수 (아이콘 버튼용)
function showQuickNoteView() {
    window.location.href = '/static/quicknote.html';
}