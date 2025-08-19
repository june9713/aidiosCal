from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime
import uuid
import secrets
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.models import User, Team, TeamMember, TeamInvitation, TeamMemberStatus, TeamMemberRole
from app.schemas.schemas import (
    Team as TeamSchema, TeamCreate, TeamUpdate, TeamJoinRequest, 
    TeamMember as TeamMemberSchema, TeamInvitation as TeamInvitationSchema,
    TeamMemberAction
)

router = APIRouter()

def generate_invite_code(length: int = 8) -> str:
    """초대 코드 생성"""
    return secrets.token_urlsafe(length)[:length].lower()

@router.post("/teams", response_model=TeamSchema)
async def create_team(
    team_data: TeamCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """새 팀 생성"""
    try:
        # 고유 팀 ID 생성
        team_id = str(uuid.uuid4())
        
        # 초대 코드 생성 (중복 체크)
        while True:
            invite_code = generate_invite_code()
            existing_team = db.query(Team).filter(Team.invite_code == invite_code).first()
            if not existing_team:
                break
        
        # 팀 생성
        new_team = Team(
            id=team_id,
            name=team_data.name,
            description=team_data.description,
            invite_code=invite_code,
            leader_id=current_user.id
        )
        
        db.add(new_team)
        db.flush()  # ID 생성을 위해
        
        # 리더를 팀원으로 추가
        leader_member = TeamMember(
            team_id=team_id,
            user_id=current_user.id,
            role=TeamMemberRole.LEADER,
            status=TeamMemberStatus.APPROVED,
            joined_at=datetime.now()
        )
        
        db.add(leader_member)
        db.commit()
        db.refresh(new_team)
        
        print(f"Team created: {team_data.name} (ID: {team_id}, Code: {invite_code})")
        return new_team
        
    except Exception as e:
        db.rollback()
        print(f"Failed to create team: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create team: {str(e)}"
        )

@router.get("/teams", response_model=List[TeamSchema])
async def get_user_teams(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """사용자가 속한 팀 목록 조회"""
    try:
        # 사용자가 멤버인 팀들 조회
        teams = db.query(Team).join(TeamMember).filter(
            TeamMember.user_id == current_user.id,
            TeamMember.status == TeamMemberStatus.APPROVED,
            Team.is_active == True
        ).all()
        
        return teams
        
    except Exception as e:
        print(f"Failed to fetch user teams: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch teams: {str(e)}"
        )

@router.post("/teams/join")
async def request_team_join(
    join_data: TeamJoinRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """초대 코드로 팀 가입 요청"""
    try:
        # 팀 조회
        team = db.query(Team).filter(
            Team.invite_code == join_data.invite_code,
            Team.is_active == True
        ).first()
        
        if not team:
            raise HTTPException(
                status_code=404,
                detail="유효하지 않은 초대 코드입니다."
            )
        
        # 이미 팀원인지 확인
        existing_member = db.query(TeamMember).filter(
            TeamMember.team_id == team.id,
            TeamMember.user_id == current_user.id
        ).first()
        
        if existing_member:
            if existing_member.status == TeamMemberStatus.APPROVED:
                raise HTTPException(
                    status_code=400,
                    detail="이미 이 팀의 멤버입니다."
                )
            elif existing_member.status == TeamMemberStatus.PENDING:
                raise HTTPException(
                    status_code=400,
                    detail="이미 가입 요청이 대기 중입니다."
                )
        
        # 가입 요청 생성
        invitation = TeamInvitation(
            team_id=team.id,
            user_id=current_user.id,
            invite_code=join_data.invite_code
        )
        
        # 팀 멤버 레코드도 생성 (대기 상태)
        team_member = TeamMember(
            team_id=team.id,
            user_id=current_user.id,
            role=TeamMemberRole.MEMBER,
            status=TeamMemberStatus.PENDING
        )
        
        db.add(invitation)
        db.add(team_member)
        db.commit()
        
        return {"message": f"'{team.name}' 팀에 가입 요청을 보냈습니다.", "team_name": team.name}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Failed to request team join: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"팀 가입 요청에 실패했습니다: {str(e)}"
        )

@router.get("/teams/{team_id}/members", response_model=List[dict])
async def get_team_members(
    team_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """팀 멤버 목록 조회"""
    try:
        # 사용자가 해당 팀의 멤버인지 확인
        user_member = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.status == TeamMemberStatus.APPROVED
        ).first()
        
        if not user_member:
            raise HTTPException(
                status_code=403,
                detail="이 팀의 멤버가 아닙니다."
            )
        
        # 팀 멤버들 조회 (사용자 정보 포함)
        members = db.query(TeamMember).options(
            joinedload(TeamMember.user)
        ).filter(
            TeamMember.team_id == team_id
        ).all()
        
        result = []
        for member in members:
            result.append({
                "id": member.id,
                "user_id": member.user_id,
                "username": member.user.username,
                "name": member.user.name,
                "role": member.role.value,
                "status": member.status.value,
                "joined_at": member.joined_at,
                "created_at": member.created_at
            })
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Failed to fetch team members: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"팀 멤버 조회에 실패했습니다: {str(e)}"
        )

@router.get("/teams/{team_id}/pending-requests", response_model=List[dict])
async def get_pending_requests(
    team_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """팀 가입 대기 중인 요청 목록 조회 (리더만)"""
    try:
        # 팀 리더인지 확인
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team or team.leader_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="팀 리더만 접근할 수 있습니다."
            )
        
        # 대기 중인 요청들 조회
        pending_requests = db.query(TeamInvitation).options(
            joinedload(TeamInvitation.user)
        ).filter(
            TeamInvitation.team_id == team_id,
            TeamInvitation.status == TeamMemberStatus.PENDING
        ).order_by(TeamInvitation.requested_at.desc()).all()
        
        result = []
        for request in pending_requests:
            result.append({
                "id": request.id,
                "user_id": request.user_id,
                "username": request.user.username,
                "name": request.user.name,
                "requested_at": request.requested_at,
                "invite_code": request.invite_code
            })
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Failed to fetch pending requests: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"대기 요청 조회에 실패했습니다: {str(e)}"
        )

@router.post("/teams/{team_id}/manage-member")
async def manage_team_member(
    team_id: str,
    action_data: TeamMemberAction,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """팀 멤버 관리 (승인/거절/추방) - 리더만"""
    try:
        # 팀 리더인지 확인
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team or team.leader_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="팀 리더만 접근할 수 있습니다."
            )
        
        target_user_id = action_data.user_id
        action = action_data.action.lower()
        
        if action in ["approve", "reject"]:
            # 가입 요청 처리
            invitation = db.query(TeamInvitation).filter(
                TeamInvitation.team_id == team_id,
                TeamInvitation.user_id == target_user_id,
                TeamInvitation.status == TeamMemberStatus.PENDING
            ).first()
            
            if not invitation:
                raise HTTPException(
                    status_code=404,
                    detail="해당 가입 요청을 찾을 수 없습니다."
                )
            
            # 팀 멤버 레코드 조회
            team_member = db.query(TeamMember).filter(
                TeamMember.team_id == team_id,
                TeamMember.user_id == target_user_id
            ).first()
            
            if action == "approve":
                invitation.status = TeamMemberStatus.APPROVED
                invitation.processed_at = datetime.now()
                invitation.processed_by = current_user.id
                
                if team_member:
                    team_member.status = TeamMemberStatus.APPROVED
                    team_member.joined_at = datetime.now()
                
                message = "팀 가입이 승인되었습니다."
                
            elif action == "reject":
                invitation.status = TeamMemberStatus.REJECTED
                invitation.processed_at = datetime.now()
                invitation.processed_by = current_user.id
                
                if team_member:
                    team_member.status = TeamMemberStatus.REJECTED
                
                message = "팀 가입이 거절되었습니다."
        
        elif action == "kick":
            # 팀원 추방
            team_member = db.query(TeamMember).filter(
                TeamMember.team_id == team_id,
                TeamMember.user_id == target_user_id,
                TeamMember.status == TeamMemberStatus.APPROVED
            ).first()
            
            if not team_member:
                raise HTTPException(
                    status_code=404,
                    detail="해당 팀원을 찾을 수 없습니다."
                )
            
            # 리더는 추방할 수 없음
            if team_member.role == TeamMemberRole.LEADER:
                raise HTTPException(
                    status_code=400,
                    detail="팀 리더는 추방할 수 없습니다."
                )
            
            db.delete(team_member)
            message = "팀원이 추방되었습니다."
        
        else:
            raise HTTPException(
                status_code=400,
                detail="유효하지 않은 액션입니다. (approve, reject, kick 중 선택)"
            )
        
        db.commit()
        return {"message": message}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Failed to manage team member: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"팀 멤버 관리에 실패했습니다: {str(e)}"
        )

@router.get("/teams/{team_id}")
async def get_team_details(
    team_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """팀 상세 정보 조회"""
    try:
        # 사용자가 해당 팀의 멤버인지 확인
        user_member = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.status == TeamMemberStatus.APPROVED
        ).first()
        
        if not user_member:
            raise HTTPException(
                status_code=403,
                detail="이 팀의 멤버가 아닙니다."
            )
        
        # 팀 정보 조회
        team = db.query(Team).options(joinedload(Team.leader)).filter(
            Team.id == team_id
        ).first()
        
        if not team:
            raise HTTPException(
                status_code=404,
                detail="팀을 찾을 수 없습니다."
            )
        
        # 팀 멤버 수 조회
        member_count = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.status == TeamMemberStatus.APPROVED
        ).count()
        
        return {
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "invite_code": team.invite_code,
            "leader_id": team.leader_id,
            "leader_name": team.leader.name,
            "member_count": member_count,
            "user_role": user_member.role.value,
            "created_at": team.created_at,
            "updated_at": team.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Failed to fetch team details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"팀 정보 조회에 실패했습니다: {str(e)}"
        ) 