from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..controllers.dependencies import current_user
from ..schemas.dataset import DatasetSummary, ObservationRow
from ..services.dataset_service import list_datasets,observations
router=APIRouter(prefix="/datasets",dependencies=[Depends(current_user)],tags=["datasets"])
@router.get("",response_model=list[DatasetSummary])
def index(db:Session=Depends(get_db)): return list_datasets(db)
@router.get("/{did}/observations")
def preview(did:int,db:Session=Depends(get_db)): return observations(db,did)
