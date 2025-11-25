from fastapi import APIRouter
from app.schemas.user_input_schema import UserInputRequest, UserInputResponse

router = APIRouter()

@router.post("/user-input", response_model=UserInputResponse)
async def save_user_input(data: UserInputRequest):
    """
    PAGE 1~3: 기본 소득 + 인적공제 + 조건 설문
    - 현재는 DB 저장 없이, 단순 validation 성공 여부만 반환
    - 실제 분석 시에는 프론트에서 이 데이터를 그대로 /analyze 로 다시 전달
    """
    # 간단한 추가 validation 예시 (원하면 더 넣어도 됨)
    if data.income.total_salary <= 0:
        return UserInputResponse(status="error", validated=False, message="총급여는 0보다 커야 합니다.")

    return UserInputResponse(status="ok", validated=True)