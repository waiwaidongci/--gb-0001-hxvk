from ..constants.roles import Role
from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..controllers.dependencies import current_user,roles
from ..schemas.decision import DecisionInput
from ..services.decision_service import list_decisions,create_decision
router=APIRouter(prefix="/decisions",tags=["decisions"])
@router.get("")
def index(db:Session=Depends(get_db),user=Depends(current_user)): return list_decisions(db)
@router.post("",status_code=201)
def create(data:DecisionInput,db:Session=Depends(get_db),user=Depends(roles(Role.ADMIN))): return create_decision(db,data,user)
