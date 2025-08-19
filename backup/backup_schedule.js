let currentScheduleId = null;
let parentScheduleId = null;

// 스케줄 모달 표시
function showScheduleModal(scheduleId = null) {
    currentScheduleId = scheduleId;
    const modal = new bootstrap.Modal(document.getElementById('scheduleModal'));
    
    // 버튼 표시/숨김 설정
    const viewParentBtn = document.getElementById('viewParentBtn');
    const viewChildrenBtn = document.getElementById('viewChildrenBtn');
    const createChildBtn = document.getElementById('createChildBtn');
    
    if (scheduleId) {
        // 기존 스케줄 수정
        fetch(`/schedules/${scheduleId}`)
            .then(response => response.json())
            .then(schedule => {
                // 모든 필드 초기화
                document.getElementById('scheduleForm').reset();
                
                // 필드 값 설정
                document.getElementById('title').value = schedule.title || '';
                document.getElementById('content').value = schedule.content || '';
                document.getElementById('projectName').value = schedule.project_name || '';
                document.getElementById('date').value = schedule.date ? schedule.date.split('T')[0] : '';
                document.getElementById('dueTime').value = schedule.due_time ? schedule.due_time.split('T')[1].slice(0, 5) : '';
                document.getElementById('alarmTime').value = schedule.alarm_time ? schedule.alarm_time.split('T')[1].slice(0, 5) : '';
                document.getElementById('priority').value = schedule.priority || 'medium';
                
                // 부모-자식 관계 버튼 표시
                viewParentBtn.style.display = schedule.parent_id ? 'block' : 'none';
                viewChildrenBtn.style.display = schedule.children && schedule.children.length > 0 ? 'block' : 'none';
                createChildBtn.style.display = 'block';
                
                parentScheduleId = schedule.parent_id;
            })
            .catch(error => {
                console.error('스케줄 로드 중 오류 발생:', error);
                alert('스케줄 정보를 불러오는데 실패했습니다.');
            });
    } else {
        // 새 스케줄 생성
        document.getElementById('scheduleForm').reset();
        
        // 부모 스케줄이 있는 경우 프로젝트명 가져오기
        if (parentScheduleId) {
            fetch(`/schedules/${parentScheduleId}`)
                .then(response => response.json())
                .then(parentSchedule => {
                    // 부모 스케줄의 프로젝트명을 기본값으로 설정
                    document.getElementById('projectName').value = parentSchedule.project_name || '';
                })
                .catch(error => {
                    console.error('부모 스케줄 로드 중 오류 발생:', error);
                });
        }
        
        viewParentBtn.style.display = 'none';
        viewChildrenBtn.style.display = 'none';
        createChildBtn.style.display = parentScheduleId ? 'block' : 'none';
    }
    
    modal.show();
}

// 후속 작업 생성
async function createChildSchedule(parentId) {
    parentScheduleId = parentId;
    showScheduleModal();
}

// 부모 작업 보기
async function viewParentSchedule(parentId) {
    showScheduleModal(parentId);
}

// 후속 작업 보기
async function viewChildrenSchedules(scheduleId) {
    const response = await fetch(`/schedules/${scheduleId}/children`);
    const children = await response.json();
    
    // children-modal.html을 사용하여 후속 작업 목록 표시
    const modal = new bootstrap.Modal(document.getElementById('childrenModal'));
    const childrenList = document.getElementById('childrenList');
    
    childrenList.innerHTML = children.map(child => `
        <div class="child-schedule" onclick="showScheduleModal(${child.id})">
            <div class="child-title">${child.title}</div>
            <div class="child-date">${new Date(child.date).toLocaleDateString()}</div>
        </div>
    `).join('');
    
    modal.show();
}

// 스케줄 저장
document.getElementById('saveScheduleBtn').addEventListener('click', function() {
    const formData = {
        title: document.getElementById('title').value,
        content: document.getElementById('content').value,
        project_name: document.getElementById('projectName').value,
        date: document.getElementById('date').value,
        due_time: document.getElementById('dueTime').value,
        alarm_time: document.getElementById('alarmTime').value,
        priority: document.getElementById('priority').value,
        parent_id: parentScheduleId
    };

    const method = currentScheduleId ? 'PUT' : 'POST';
    const url = currentScheduleId ? `/schedules/${currentScheduleId}` : '/schedules';

    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        const modal = bootstrap.Modal.getInstance(document.getElementById('scheduleModal'));
        modal.hide();
        loadSchedules();
    })
    .catch(error => {
        console.error('Error:', error);
        alert('스케줄 저장 중 오류가 발생했습니다.');
    });
}); 