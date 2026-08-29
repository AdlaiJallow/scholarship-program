export type ApplicationStatus =
  | "not_started"
  | "in_progress"
  | "submitted"
  | "under_review"
  | "additional_info_required"
  | "approved"
  | "rejected"
  | "resubmission_required";

export const STATUS_LABELS: Record<ApplicationStatus, string> = {
  not_started: "Not Started",
  in_progress: "In Progress",
  submitted: "Submitted",
  under_review: "Under Review",
  additional_info_required: "Additional Information Required",
  approved: "Approved",
  rejected: "Rejected",
  resubmission_required: "Resubmission Required",
};

export type DocumentSlotStatus = "pending" | "verified" | "rejected" | "needs_clarification";

export interface RequiredDocument {
  id: number;
  name: string;
  description: string;
  is_mandatory: boolean;
  accepted_file_types: string[];
  max_file_size_bytes: number;
}

export interface DocumentVersion {
  id: string;
  version_number: number;
  original_filename: string;
  content_type: string;
  file_size_bytes: number;
  uploaded_at: string;
  scan_status: "pending" | "clean" | "infected" | "error";
  download_url: string;
}

export interface DocumentReview {
  id: string;
  verdict: DocumentSlotStatus;
  comment: string;
  officer_name: string;
  created_at: string;
}

export interface SubmittedDocument {
  id: number;
  status: DocumentSlotStatus;
  required_document: RequiredDocument;
  current_version: DocumentVersion | null;
  reviews: DocumentReview[];
}

export interface RequirementRow {
  required_document: RequiredDocument;
  submitted: SubmittedDocument | null;
}

export interface RequirementsResponse {
  application_id: string;
  application_status: ApplicationStatus;
  requirements: RequirementRow[];
}

export interface StatusHistoryEntry {
  from_status: string;
  to_status: string;
  changed_by_email: string | null;
  note: string;
  created_at: string;
}

export interface ApplicationListItem {
  id: string;
  reference_number: string;
  status: ApplicationStatus;
  student_name: string;
  scholarship_id: string;
  institution: string;
  country: string;
  scholarship_type: string;
  assigned_officer_name: string | null;
  submitted_at: string | null;
  updated_at: string;
}

export interface ApplicationDetail {
  id: string;
  reference_number: string;
  status: ApplicationStatus;
  student_name: string;
  student_email: string;
  student_dob: string;
  student_gender: string;
  student_phone: string;
  scholarship: {
    scholarship_reference_id: string;
    scholarship_type: string;
    institution: string;
    country: string;
    program: string | null;
    status: string;
    start_date: string;
    end_date: string;
  };
  assigned_officer: number | null;
  submitted_documents: SubmittedDocument[];
  status_history: StatusHistoryEntry[];
  declaration_confirmed_at: string | null;
  submitted_at: string | null;
  decided_at: string | null;
  decision_remarks: string;
  rejection_reason: string;
  rejection_reason_display: string;
  rejection_detail: string;
}

export interface StudentProfile {
  full_name: string;
  date_of_birth: string;
  gender: string;
  phone_number: string;
  address: string;
  email: string;
  user_type: "student";
}

export interface OfficerProfile {
  full_name: string;
  employee_id: string;
  department: string;
  role: string;
  email: string;
  user_type: "officer";
}

export interface VerifyIdentityResponse {
  detail: string;
}

export interface VerifyCodeResponse {
  verification_token: string;
  detail: string;
}

export interface ResendCodeResponse {
  detail: string;
  retry_after_seconds?: number;
}

export interface CreateAccountResponse {
  user_type: "student";
  email: string;
}

export interface PasswordResetRequestResponse {
  detail?: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
