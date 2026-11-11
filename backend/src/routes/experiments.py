from ..constants.roles import Role
from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..controllers.dependencies import current_user,roles
from ..schemas.experiment import ExperimentInput
from ..services.experiment_service import list_experiments,create_experiment
router=APIRouter(prefix="/experiments",tags=["experiments"])
@router.get("")
def index(db:Session=Depends(get_db),user=Depends(current_user)): return list_experiments(db)
@router.post("",status_code=201)
def create(data:ExperimentInput,db:Session=Depends(get_db),user=Depends(roles(Role.ADMIN,Role.ANALYST))): return create_experiment(db,data,user)
