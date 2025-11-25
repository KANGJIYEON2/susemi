from typing import List, Optional
from pydantic import BaseModel, Field


# ----- 서브 스키마들 -----
class RentInfo(BaseModel):
    has_rent: bool = Field(..., description="월세 납부 여부")
    monthly_rent: int | None = Field(None, description="월세 금액")
    months_paid: int | None = Field(None, description="납부 개월 수")


class FamilyMedicalItem(BaseModel):
    name: str = Field(..., description="가족 관계 또는 이름")
    amount: int = Field(..., description="의료비 금액")


class HousingLoanInfo(BaseModel):
    has_loan: bool = Field(..., description="주택자금 대출 여부")
    interest_paid: int | None = Field(None, description="이자 상환액")


# ----- ManualInput 메인 -----
class ManualInputRequest(BaseModel):
    # 기부금 (간소화에 안 잡힌 지정/종교/소액 기부 등)
    donation_extra: int | None = Field(None, description="추가 기부금 합계")

    # 월세(간소화에 없는 경우)
    rent: Optional[RentInfo] = None

    # 주택자금 대출 상환 (간소화 누락분)
    housing_loan: Optional[HousingLoanInfo] = None

    # 가족 의료비 (간소화에 안 잡힌 병원/약국, 해외 의료비 등)
    family_medical_expenses: List[FamilyMedicalItem] | None = Field(
        None, description="부양가족 의료비"
    )

    # 시력 교정용 안경/콘택트 렌즈
    glasses_contacts_expense: int | None = Field(
        None, description="시력교정용 안경/콘택트렌즈 비용"
    )

    # 보청기, 장애인 보장구, 의료기기(처방전 기반)
    assistive_devices_expense: int | None = Field(
        None, description="보청기/장애인보장구/의료기기 구입/임차비"
    )

    # 난임 시술 의료비(간소화에서 일반 의료비로만 잡혀 있을 수 있음)
    infertility_treatment_expense: int | None = Field(
        None, description="난임 시술 의료비"
    )

    # 교육비(간소화에 안 잡힌 교복/도서/국외 교육비 등)
    preschool_education_expense: int | None = Field(
        None, description="취학 전 아동 교육비(학원, 체육시설 등)"
    )
    school_uniform_and_books_expense: int | None = Field(
        None, description="교복/방과후 학교용 도서 구입비"
    )
    foreign_education_expense: int | None = Field(
        None, description="국외 교육기관 교육비"
    )

    # 산후조리원 비용 등 (의료비 특례로 들어갈 여지 있는 항목)
    childbirth_care_expense: int | None = Field(
        None, description="산후조리원 비용 등 추가 의료성 비용"
    )

    # 중소기업 취업자 소득세 감면 신청 여부(간소화 자료와 별개)
    mid_small_company_reduction_applied: bool | None = Field(
        None, description="중소기업 취업자 소득세 감면 신청 여부"
    )


class ManualInputResponse(BaseModel):
    status: str
    message: str | None = None
