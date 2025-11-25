from pydantic import BaseModel, Field

# ----- Income -----
class Income(BaseModel):
    total_salary: int = Field(..., description="총급여")
    non_taxable: int | None = Field(0, description="비과세 급여")
    bonus: int | None = Field(0, description="상여금")


# ----- Dependents (인적공제) -----
class Dependents(BaseModel):
    has_spouse: bool = Field(..., description="배우자 유무")
    dependents_count: int = Field(0, description="부양가족 수")
    disabled_count: int = Field(0, description="장애인 가족 수")
    senior_count: int = Field(0, description="경로우대(만 70세 이상) 가족 수")
    single_parent: bool = Field(False, description="한부모 여부")
    female_householder: bool = Field(False, description="부녀자 공제 해당 여부")


# ----- Conditions (세법 요건 설문) -----
class Conditions(BaseModel):
    householder: bool = Field(..., description="세대주 여부")
    no_house: bool = Field(..., description="무주택 여부")
    lease_contract: bool = Field(..., description="임대차 계약 여부")
    has_loan: bool = Field(..., description="주택자금대출 여부")
    child_education: bool = Field(False, description="자녀 교육비 발생 여부")
    self_education: bool = Field(False, description="본인 교육비 발생 여부")
    mid_small_company_worker: bool | None = Field(
        False, description="중소기업 취업자 소득세 감면 대상 여부"
    )
    # 향후 필요 시 조건 더 추가


# ----- UserInput Request/Response -----
class UserInputRequest(BaseModel):
    income: Income
    dependents: Dependents
    conditions: Conditions


class UserInputResponse(BaseModel):
    status: str
    validated: bool
    message: str | None = None
