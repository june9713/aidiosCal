// 파일 뷰어 전역 변수
let currentFiles = [];
let filteredFiles = [];
let currentViewMode = 'grid';
let isSelectMode = false;
let selectedFiles = new Set();
let currentGalleryIndex = 0;
let currentFile = null; // 컨텍스트 메뉴용

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', async () => {
    console.log('File viewer initialized');
    
    // 사용자 정보 표시
    const userInfo = localStorage.getItem('userData');
    if (userInfo) {
        const userData = JSON.parse(userInfo);
        const userInfoElement = document.getElementById('user-info');
        if (userInfoElement) {
            userInfoElement.textContent = userData.name || userData.username || '사용자';
        }
    }

    // 필터 옵션 로드
    await loadFilterOptions();
    
    // 이벤트 리스너 설정
    setupEventListeners();
    
    // 오늘 날짜를 기본값으로 설정
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('end-date').value = today;
    
    // 한 달 전 날짜를 시작일로 설정
    const oneMonthAgo = new Date();
    oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1);
    document.getElementById('start-date').value = oneMonthAgo.toISOString().split('T')[0];
});

// 홈으로 이동
function goHome() {
    // URL에서 screen_id 추출
    const pathSegments = window.location.pathname.split('/');
    const lastSegment = pathSegments[pathSegments.length - 1];
    const currentIndex = /^\d+$/.test(lastSegment) ? lastSegment : '0';
    
    // entryScreen으로 이동
    window.location.href = `/entryScreen/${currentIndex}`;
}

// 필터 옵션 로드
async function loadFilterOptions() {
    try {
        // 사용자 목록 로드
        const usersResponse = await apiRequest('/users/');
        if (usersResponse.ok) {
            const users = await usersResponse.json();
            const uploaderSelect = document.getElementById('uploader-filter');
            users.forEach(user => {
                if (user.name !== "admin" && user.name !== "viewer") {
                    const option = document.createElement('option');
                    option.value = user.id;
                    option.textContent = user.name;
                    uploaderSelect.appendChild(option);
                }
            });
        }

        // 프로젝트 목록 로드
        const projectsResponse = await apiRequest('/projects/');
        if (projectsResponse.ok) {
            const projects = await projectsResponse.json();
            const projectSelect = document.getElementById('project-filter');
            projects.forEach(project => {
                const option = document.createElement('option');
                option.value = project.name;
                option.textContent = project.name;
                projectSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load filter options:', error);
        alert('파일 필터 설정 중 오류가 발생했습니다.');
        clearSession();
        window.location.href = '/static/login.html';
    }
}

// 이벤트 리스너 설정
function setupEventListeners() {
    // 클릭 외부 영역 클릭 시 컨텍스트 메뉴 닫기
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.context-menu')) {
            hideContextMenu();
        }
    });

    // ESC 키로 갤러리 모달 닫기
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeGallery();
            closeRenameModal();
        }
        if (e.key === 'ArrowLeft') {
            previousFile();
        }
        if (e.key === 'ArrowRight') {
            nextFile();
        }
    });
}

// 파일 검색
async function searchFiles() {
    const filters = {
        start_date: document.getElementById('start-date').value,
        end_date: document.getElementById('end-date').value,
        filename_pattern: document.getElementById('filename-pattern').value,
        uploader_id: document.getElementById('uploader-filter').value,
        project_name: document.getElementById('project-filter').value,
        schedule_title: document.getElementById('schedule-title-filter').value
    };

    try {
        // 쿼리 파라미터 구성
        const params = new URLSearchParams();
        Object.entries(filters).forEach(([key, value]) => {
            if (value) {
                params.append(key, value);
            }
        });

        const response = await apiRequest(`/attachments/search?${params.toString()}`);
        if (response.ok) {
            const files = await response.json();
            currentFiles = files;
            filteredFiles = files;
            renderFiles();
            
            document.getElementById('no-files-message').style.display = files.length === 0 ? 'block' : 'none';
        } else {
            console.error('Failed to search files:', response.status);
            document.getElementById('no-files-message').textContent = '파일 검색 중 오류가 발생했습니다.';
            document.getElementById('no-files-message').style.display = 'block';
        }
    } catch (error) {
        console.error('Search files error:', error);
        document.getElementById('no-files-message').textContent = '파일 검색 중 오류가 발생했습니다.';
        document.getElementById('no-files-message').style.display = 'block';
    }
}

// 필터 초기화
function clearFilters() {
    document.getElementById('start-date').value = '';
    document.getElementById('end-date').value = '';
    document.getElementById('filename-pattern').value = '';
    document.getElementById('uploader-filter').value = '';
    document.getElementById('project-filter').value = '';
    document.getElementById('schedule-title-filter').value = '';
    
    // 파일 목록 숨기기
    document.getElementById('files-grid').style.display = 'none';
    document.getElementById('files-list').style.display = 'none';
    document.getElementById('no-files-message').textContent = '필터를 설정하고 조회 버튼을 클릭하여 파일을 검색하세요.';
    document.getElementById('no-files-message').style.display = 'block';
    
    currentFiles = [];
    filteredFiles = [];
}

// 뷰 모드 전환
function toggleViewMode(mode) {
    currentViewMode = mode;
    
    // 버튼 상태 업데이트
    document.getElementById('grid-view-btn').classList.toggle('active', mode === 'grid');
    document.getElementById('list-view-btn').classList.toggle('active', mode === 'list');
    
    renderFiles();
}

// 선택 모드 토글
function toggleSelectMode() {
    isSelectMode = !isSelectMode;
    selectedFiles.clear();
    
    // UI 업데이트
    const selectBtn = document.getElementById('select-btn');
    const downloadBtn = document.getElementById('download-selected-btn');
    const deleteBtn = document.getElementById('delete-selected-btn');
    const filesContainer = document.querySelector('.files-container');
    
    if (isSelectMode) {
        selectBtn.innerHTML = '<i class="fas fa-times"></i> 선택취소';
        selectBtn.style.backgroundColor = '#dc3545';
        downloadBtn.style.display = 'block';
        deleteBtn.style.display = 'block';
        filesContainer.classList.add('select-mode');
    } else {
        selectBtn.innerHTML = '<i class="fas fa-check-square"></i> 선택모드';
        selectBtn.style.backgroundColor = '#17a2b8';
        downloadBtn.style.display = 'none';
        deleteBtn.style.display = 'none';
        filesContainer.classList.remove('select-mode');
    }
    
    renderFiles();
}

// 파일 렌더링
function renderFiles() {
    const gridContainer = document.getElementById('files-grid');
    const listContainer = document.getElementById('files-list');
    
    // 컨테이너 초기화
    gridContainer.innerHTML = '';
    listContainer.innerHTML = '';
    
    if (currentViewMode === 'grid') {
        gridContainer.style.display = 'grid';
        listContainer.style.display = 'none';
        filteredFiles.forEach((file, index) => renderFileGrid(file, index));
    } else {
        gridContainer.style.display = 'none';
        listContainer.style.display = 'flex';
        filteredFiles.forEach((file, index) => renderFileList(file, index));
    }
}

// 그리드 아이템 렌더링
function renderFileGrid(file, index) {
    const container = document.getElementById('files-grid');
    const fileDiv = document.createElement('div');
    fileDiv.className = `file-item-grid ${selectedFiles.has(file.id) ? 'selected' : ''}`;
    fileDiv.dataset.fileId = file.id;
    fileDiv.dataset.fileIndex = index;
    
    const thumbnailHtml = createThumbnail(file, 'grid');
    const fileCreatedDate = new Date(file.created_at);
    const year = fileCreatedDate.getFullYear();
    const month = (fileCreatedDate.getMonth() + 1).toString().padStart(2, '0');
    const day = fileCreatedDate.getDate().toString().padStart(2, '0');
    const hours = fileCreatedDate.getHours().toString().padStart(2, '0');
    const minutes = fileCreatedDate.getMinutes().toString().padStart(2, '0');
    const uploadDate = `${year}-${month}-${day} ${hours}:${minutes}`;
    const fileSize = formatFileSize(file.file_size || 0);
    
    fileDiv.innerHTML = `
        ${isSelectMode ? `<input type="checkbox" class="file-checkbox" ${selectedFiles.has(file.id) ? 'checked' : ''} onchange="toggleFileSelection(${file.id})">` : ''}
        <div class="file-thumbnail-grid" onclick="openGallery(${index})">
            ${thumbnailHtml}
        </div>
        <div class="file-info-grid">
            <div class="file-name-grid" title="${file.filename}">${truncateFileName(file.filename, 20)}</div>
            <div class="file-meta-grid">
                <span>${fileSize}</span>
                <span>${uploadDate}</span>
                ${file.uploader ? `<span>${file.uploader.name}</span>` : ''}
                ${file.schedule_title ? `<span title="${file.schedule_title}">${truncateText(file.schedule_title, 15)}</span>` : ''}
            </div>
        </div>
    `;
    
    // 우클릭 이벤트
    fileDiv.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        showContextMenu(e, file);
    });
    
    // 터치 이벤트 (모바일)
    let touchTimer;
    fileDiv.addEventListener('touchstart', (e) => {
        touchTimer = setTimeout(() => {
            e.preventDefault();
            showContextMenu(e.touches[0], file);
        }, 700);
    });
    fileDiv.addEventListener('touchend', () => clearTimeout(touchTimer));
    fileDiv.addEventListener('touchmove', () => clearTimeout(touchTimer));
    
    container.appendChild(fileDiv);
}

// 목록 아이템 렌더링
function renderFileList(file, index) {
    const container = document.getElementById('files-list');
    const fileDiv = document.createElement('div');
    fileDiv.className = `file-item-list ${selectedFiles.has(file.id) ? 'selected' : ''}`;
    fileDiv.dataset.fileId = file.id;
    fileDiv.dataset.fileIndex = index;
    
    const thumbnailHtml = createThumbnail(file, 'list');
    const fileCreatedDate = new Date(file.created_at);
    const year = fileCreatedDate.getFullYear();
    const month = (fileCreatedDate.getMonth() + 1).toString().padStart(2, '0');
    const day = fileCreatedDate.getDate().toString().padStart(2, '0');
    const hours = fileCreatedDate.getHours().toString().padStart(2, '0');
    const minutes = fileCreatedDate.getMinutes().toString().padStart(2, '0');
    const uploadDate = `${year}-${month}-${day} ${hours}:${minutes}`;
    const fileSize = formatFileSize(file.file_size || 0);
    
    fileDiv.innerHTML = `
        ${isSelectMode ? `<input type="checkbox" class="file-checkbox" ${selectedFiles.has(file.id) ? 'checked' : ''} onchange="toggleFileSelection(${file.id})" style="margin-right: 15px;">` : ''}
        <div class="file-thumbnail-list" onclick="openGallery(${index})">
            ${thumbnailHtml}
        </div>
        <div class="file-info-list">
            <div class="file-name-list">${file.filename}</div>
            <div class="file-meta-list">
                <span>${fileSize}</span>
                <span>${uploadDate}</span>
                ${file.uploader ? `<span>업로드: ${file.uploader.name}</span>` : ''}
                ${file.project_name ? `<span>프로젝트: ${file.project_name}</span>` : ''}
                ${file.schedule_title ? `<span>일정: ${file.schedule_title}</span>` : ''}
            </div>
        </div>
    `;
    
    // 우클릭 이벤트
    fileDiv.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        showContextMenu(e, file);
    });
    
    container.appendChild(fileDiv);
}

// 썸네일 생성
function createThumbnail(file, mode) {
    const isImage = isImageFile(file.filename, file.mime_type);
    const isVideo = isVideoFile(file.filename, file.mime_type);
    
    if (isImage) {
        return `<img src="${file.file_path}" alt="${file.filename}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                <div class="file-icon-large" style="display:none;">${getFileIcon(file.filename, file.mime_type)}</div>`;
    } else if (isVideo) {
        return `<video src="${file.file_path}" muted onclick="event.stopPropagation();">
                <div class="file-icon-large">${getFileIcon(file.filename, file.mime_type)}</div>
                </video>`;
    } else {
        return `<div class="file-icon-large">${getFileIcon(file.filename, file.mime_type)}</div>`;
    }
}

// 비디오 파일 체크
function isVideoFile(filename, mimeType) {
    if (mimeType && mimeType.startsWith('video/')) {
        return true;
    }
    const videoExtensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm', '.m4v'];
    const extension = filename.toLowerCase().substr(filename.lastIndexOf('.'));
    return videoExtensions.includes(extension);
}

// 파일 선택 토글
function toggleFileSelection(fileId) {
    if (selectedFiles.has(fileId)) {
        selectedFiles.delete(fileId);
    } else {
        selectedFiles.add(fileId);
    }
    
    // UI 업데이트
    const fileElement = document.querySelector(`[data-file-id="${fileId}"]`);
    if (fileElement) {
        fileElement.classList.toggle('selected', selectedFiles.has(fileId));
    }
    
    // 선택된 파일 수 표시 (옵션)
    const downloadBtn = document.getElementById('download-selected-btn');
    const deleteBtn = document.getElementById('delete-selected-btn');
    if (selectedFiles.size > 0) {
        downloadBtn.innerHTML = `<i class="fas fa-download"></i> 다운로드 (${selectedFiles.size})`;
        deleteBtn.innerHTML = `<i class="fas fa-trash"></i> 삭제 (${selectedFiles.size})`;
    } else {
        downloadBtn.innerHTML = '<i class="fas fa-download"></i> 다운로드';
        deleteBtn.innerHTML = '<i class="fas fa-trash"></i> 삭제';
    }
}

// 갤러리 열기
function openGallery(index) {
    if (isSelectMode) return; // 선택 모드에서는 갤러리 열지 않음
    
    currentGalleryIndex = index;
    const modal = document.getElementById('gallery-modal');
    modal.style.display = 'flex';
    
    updateGalleryContent();
}

// 갤러리 내용 업데이트
function updateGalleryContent() {
    const file = filteredFiles[currentGalleryIndex];
    if (!file) return;
    
    const mediaContainer = document.getElementById('gallery-media');
    const infoContainer = document.getElementById('gallery-info');
    const counter = document.getElementById('file-counter');
    
    // 카운터 업데이트
    counter.textContent = `${currentGalleryIndex + 1} / ${filteredFiles.length}`;
    
    // 미디어 컨테이너 업데이트
    const isImage = isImageFile(file.filename, file.mime_type);
    const isVideo = isVideoFile(file.filename, file.mime_type);
    
    if (isImage) {
        mediaContainer.innerHTML = `<img src="${file.file_path}" alt="${file.filename}">`;
    } else if (isVideo) {
        mediaContainer.innerHTML = `<video src="${file.file_path}" controls style="max-width: 100%; max-height: 100%;">`;
    } else {
        mediaContainer.innerHTML = `<div class="file-icon-large" style="font-size: 120px; color: #6c757d;">${getFileIcon(file.filename, file.mime_type)}</div>`;
    }
    
    // 정보 패널 업데이트
    const fileCreatedDate = new Date(file.created_at);
    const year = fileCreatedDate.getFullYear();
    const month = (fileCreatedDate.getMonth() + 1).toString().padStart(2, '0');
    const day = fileCreatedDate.getDate().toString().padStart(2, '0');
    const hours = fileCreatedDate.getHours().toString().padStart(2, '0');
    const minutes = fileCreatedDate.getMinutes().toString().padStart(2, '0');
    const uploadDate = `${year}-${month}-${day} ${hours}:${minutes}`;
    const fileSize = formatFileSize(file.file_size || 0);
    
    infoContainer.innerHTML = `
        <h3>${file.filename}</h3>
        <div class="info-item">
            <div class="info-label">파일 크기</div>
            <div class="info-value">${fileSize}</div>
        </div>
        <div class="info-item">
            <div class="info-label">업로드 날짜</div>
            <div class="info-value">${uploadDate}</div>
        </div>
        ${file.uploader ? `
        <div class="info-item">
            <div class="info-label">업로드한 사람</div>
            <div class="info-value">${file.uploader.name}</div>
        </div>
        ` : ''}
        ${file.project_name ? `
        <div class="info-item">
            <div class="info-label">프로젝트</div>
            <div class="info-value">${file.project_name}</div>
        </div>
        ` : ''}
        ${file.schedule_title ? `
        <div class="info-item">
            <div class="info-label">관련 일정</div>
            <div class="info-value">${file.schedule_title}</div>
        </div>
        ` : ''}
        ${file.mime_type ? `
        <div class="info-item">
            <div class="info-label">파일 형식</div>
            <div class="info-value">${file.mime_type}</div>
        </div>
        ` : ''}
    `;
}

// 이전 파일
function previousFile() {
    if (currentGalleryIndex > 0) {
        currentGalleryIndex--;
        updateGalleryContent();
    }
}

// 다음 파일
function nextFile() {
    if (currentGalleryIndex < filteredFiles.length - 1) {
        currentGalleryIndex++;
        updateGalleryContent();
    }
}

// 갤러리 닫기
function closeGallery() {
    document.getElementById('gallery-modal').style.display = 'none';
}

// 컨텍스트 메뉴 표시
function showContextMenu(event, file) {
    hideContextMenu();
    
    currentFile = file;
    const menu = document.getElementById('context-menu');
    menu.style.display = 'block';
    
    // 메뉴 위치 설정
    const x = event.clientX || event.pageX;
    const y = event.clientY || event.pageY;
    
    const menuRect = menu.getBoundingClientRect();
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;
    
    // 화면 밖으로 나가지 않도록 조정
    let menuX = x;
    let menuY = y;
    
    if (x + menuRect.width > windowWidth) {
        menuX = windowWidth - menuRect.width - 10;
    }
    
    if (y + menuRect.height > windowHeight) {
        menuY = windowHeight - menuRect.height - 10;
    }
    
    menu.style.left = `${menuX}px`;
    menu.style.top = `${menuY}px`;
}

// 컨텍스트 메뉴 숨기기
function hideContextMenu() {
    document.getElementById('context-menu').style.display = 'none';
}

// 파일 다운로드
function downloadFile() {
    if (!currentFile) return;
    
    const link = document.createElement('a');
    link.href = currentFile.file_path;
    link.download = currentFile.filename;
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    hideContextMenu();
}

// 파일 삭제
async function deleteFile() {
    if (!currentFile) return;
    
    if (!confirm(`'${currentFile.filename}' 파일을 삭제하시겠습니까?`)) {
        hideContextMenu();
        return;
    }
    
    try {
        const response = await apiRequest(`/attachments/${currentFile.id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            // 파일 목록에서 제거
            currentFiles = currentFiles.filter(f => f.id !== currentFile.id);
            filteredFiles = filteredFiles.filter(f => f.id !== currentFile.id);
            renderFiles();
            
            // 갤러리가 열려있으면 닫기
            if (document.getElementById('gallery-modal').style.display === 'flex') {
                closeGallery();
            }
        } else {
            const error = await response.json();
            alert(error.detail || '파일 삭제에 실패했습니다.');
        }
    } catch (error) {
        console.error('Delete file error:', error);
        alert('파일 삭제 중 오류가 발생했습니다.');
    }
    
    hideContextMenu();
}

// 파일 이름 변경
function renameFile() {
    if (!currentFile) return;
    
    document.getElementById('new-filename').value = currentFile.filename;
    document.getElementById('rename-modal').style.display = 'flex';
    document.getElementById('new-filename').focus();
    
    hideContextMenu();
}

// 이름 변경 확인
async function confirmRename() {
    const newName = document.getElementById('new-filename').value.trim();
    if (!newName) {
        alert('파일명을 입력해주세요.');
        return;
    }
    
    try {
        const response = await apiRequest(`/attachments/${currentFile.id}/rename`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: newName })
        });
        
        if (response.ok) {
            // 파일 목록 업데이트
            const fileIndex = currentFiles.findIndex(f => f.id === currentFile.id);
            if (fileIndex !== -1) {
                currentFiles[fileIndex].filename = newName;
            }
            const filteredIndex = filteredFiles.findIndex(f => f.id === currentFile.id);
            if (filteredIndex !== -1) {
                filteredFiles[filteredIndex].filename = newName;
            }
            
            renderFiles();
            closeRenameModal();
        } else {
            const error = await response.json();
            alert(error.detail || '파일 이름 변경에 실패했습니다.');
        }
    } catch (error) {
        console.error('Rename file error:', error);
        alert('파일 이름 변경 중 오류가 발생했습니다.');
    }
}

// 이름 변경 모달 닫기
function closeRenameModal() {
    document.getElementById('rename-modal').style.display = 'none';
}

// 선택된 파일 다운로드
async function downloadSelected() {
    if (selectedFiles.size === 0) {
        alert('다운로드할 파일을 선택해주세요.');
        return;
    }
    
    if (selectedFiles.size === 1) {
        // 단일 파일은 직접 다운로드
        const fileId = Array.from(selectedFiles)[0];
        const file = currentFiles.find(f => f.id === fileId);
        if (file) {
            const link = document.createElement('a');
            link.href = file.file_path;
            link.download = file.filename;
            link.target = '_blank';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    } else {
        // 다중 파일은 zip으로 압축 다운로드
        try {
            const fileIds = Array.from(selectedFiles);
            const response = await apiRequest('/attachments/download/zip', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_ids: fileIds })
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = `files_${new Date().toISOString().split('T')[0]}.zip`;
                document.body.appendChild(link);
                link.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(link);
            } else {
                const error = await response.json();
                alert(error.detail || '파일 다운로드에 실패했습니다.');
            }
        } catch (error) {
            console.error('Download selected files error:', error);
            alert('파일 다운로드 중 오류가 발생했습니다.');
        }
    }
}

// 선택된 파일 삭제
async function deleteSelected() {
    if (selectedFiles.size === 0) {
        alert('삭제할 파일을 선택해주세요.');
        return;
    }
    
    if (!confirm(`선택된 ${selectedFiles.size}개 파일을 삭제하시겠습니까?`)) {
        return;
    }
    
    try {
        const fileIds = Array.from(selectedFiles);
        const response = await apiRequest('/attachments/delete/batch', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_ids: fileIds })
        });
        
        if (response.ok) {
            // 파일 목록에서 삭제된 파일들 제거
            currentFiles = currentFiles.filter(f => !selectedFiles.has(f.id));
            filteredFiles = filteredFiles.filter(f => !selectedFiles.has(f.id));
            selectedFiles.clear();
            renderFiles();
            
            // 선택 모드 해제
            if (currentFiles.length === 0) {
                toggleSelectMode();
            }
        } else {
            const error = await response.json();
            alert(error.detail || '파일 삭제에 실패했습니다.');
        }
    } catch (error) {
        console.error('Delete selected files error:', error);
        alert('파일 삭제 중 오류가 발생했습니다.');
    }
}

// 유틸리티 함수들
function truncateFileName(filename, maxLength) {
    if (filename.length <= maxLength) return filename;
    
    const extension = filename.includes('.') ? filename.split('.').pop() : '';
    const nameWithoutExt = filename.includes('.') ? filename.substring(0, filename.lastIndexOf('.')) : filename;
    
    if (extension) {
        const availableLength = maxLength - extension.length - 1; // -1 for the dot
        return nameWithoutExt.substring(0, availableLength) + '...' + '.' + extension;
    } else {
        return filename.substring(0, maxLength - 3) + '...';
    }
}

function truncateText(text, maxLength) {
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
} 