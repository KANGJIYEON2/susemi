from fastapi import APIRouter
from app.schemas.manual_input_schema import ManualInputRequest, ManualInputResponse

router = APIRouter()


@router.post("/manual-input", response_model=ManualInputResponse)
async def save_manual_input(data: ManualInputRequest):
    """
    PAGE 5: 간소화 PDF에 없는 항목 수기 입력
    - 난임시술, 안경/콘택트렌즈, 교복/도서, 월세, 위탁아동 등
    - 여기서도 저장 없이 validation만 수행
    """
    # 예시: 월세 입력 시 has_rent가 True인데 monthly_rent = 0 이면 에러
    if data.rent and data.rent.has_rent and (data.rent.monthly_rent is None or data.rent.monthly_rent <= 0):
        return ManualInputResponse(status="error", message="월세액을 입력해주세요.")

    return ManualInputResponse(status="ok")
