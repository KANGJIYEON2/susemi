export type Income = {
  total_salary: number;
  non_taxable: number;
  bonus: number;
};

export type Dependents = {
  has_spouse: boolean;
  dependents_count: number;
  disabled_count: number;
  senior_count: number;
  single_parent: boolean;
  female_householder: boolean;
};

export type Conditions = {
  householder: boolean;
  no_house: boolean;
  lease_contract: boolean;
  has_loan: boolean;
  child_education: boolean;
  self_education: boolean;
  mid_small_company_worker: boolean;
};

export type ParsedPdfData = {
  credit_card: number;
  debit_card: number;
  cash_receipt: number;
  medical_expense: number;
  severe_medical_for_disabled: number;
  insurance: number;
  pension_saving: number;
  retirement_pension: number;
  donation_total: number;
  housing_loan_interest: number;
  rent_in_pdf: number;
  tax_credit_type: string;
};

export type PdfParseResult = {
  parsed_pdf: ParsedPdfData;
  missing_fields: string[];
};

export type RentInput = {
  has_rent: boolean;
  monthly_rent: number;
  months_paid: number;
};

export type HousingLoanInput = {
  has_loan: boolean;
  interest_paid: number;
};

export type FamilyMedicalExpense = {
  name: string;
  amount: number;
};

export type ManualInput = {
  donation_extra: number;
  rent: RentInput;
  housing_loan: HousingLoanInput;
  family_medical_expenses: FamilyMedicalExpense[];
  glasses_contacts_expense: number;
  assistive_devices_expense: number;
  infertility_treatment_expense: number;
  preschool_education_expense: number;
  school_uniform_and_books_expense: number;
  foreign_education_expense: number;
  childbirth_care_expense: number;
  mid_small_company_reduction_applied: boolean;
};

export type AnalyzeRequest = {
  income: Income;
  dependents: Dependents;
  conditions: Conditions;
  parsed_pdf: ParsedPdfData;
  manual_input: ManualInput;
};

export type Summary = {
  headline: string;
  key_points: string[];
};

export type RuleEvaluation = {
  rule_id: string;
  title: string;
  legal_anchor: string;
  legal_text_hash: string | null;
  computed: Record<string, number | boolean | string | null>;
  result: boolean | null;
  formula: string | null;
};

export type Section = {
  id: string;
  title: string;
  highlight: string;
  detail: string;
  tips: string[];
  /** Phase 3-1: 백엔드가 부착한 룰 평가 근거 (legal_anchor + computed) */
  provenance: RuleEvaluation[];
};

export type AnalyzeResponse = {
  summary: Summary;
  sections: Section[];
  tax_tips: string[];
  /** 모든 룰 평가 결과 (UI 가 [rule_id] anchor 를 lookup 할 때 사용) */
  evaluations: RuleEvaluation[];
};

/* -------------------- Phase 3-3: 검증 -------------------- */

export type CompanyFiling = {
  determined_tax: number;
  prepaid_tax: number;
  earned_income_deduction?: number | null;
  earned_income_amount?: number | null;
  personal_deduction?: number | null;
  taxable_income?: number | null;
  calculated_tax?: number | null;
  earned_income_tax_credit?: number | null;
  local_income_tax?: number | null;
  notes?: string | null;
};

export type Severity = "match" | "minor" | "major" | "missing";

export type StepDiff = {
  name: string;
  label: string;
  legal_anchor: string | null;
  our_value: number;
  company_value: number | null;
  delta: number | null;
  severity: Severity;
  note: string | null;
};

export type VerificationReport = {
  year: number;
  our_total: number;
  company_total: number | null;
  final_delta: number | null;
  refund_delta: number | null;
  steps: StepDiff[];
  summary: string;
  has_major_diff: boolean;
};

export type VerifyRequest = {
  request: AnalyzeRequest;
  filing: CompanyFiling;
  extra_income_deductions?: number;
  extra_tax_credits?: number;
};
