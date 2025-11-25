from pydantic import BaseModel

class Income(BaseModel):
    total_salary: int #총급여
    non_taxable : int | None = 0 #비과세급액
    bonus : int | None = 0 #상여금

class Dependents(BaseModel):
    has_spouse: bool #배우자 유무
    dependents_count: int #부양가족 유무
    disabled_count: int #장애인 가족 수
    senior_count: int #70세 이상 가족 수
    single_parent : bool #한부모 여부

class Conditions(BaseModel):
    householder: bool                # 세대주 여부
    no_house: bool                   # 무주택 여부
    lease_contract: bool             # 임대차 계약 여부
    has_loan: bool                   # 주택자금대출 여부
    child_education: bool            # 자녀 교육비 발생 여부
    self_education: bool             # 본인 교육비 발생 여부
    female_householder: bool         # 부녀자 공제 여부


class UserInputRequest(BaseModel):
    income: Income
    dependents: Dependents
    conditions: Conditions