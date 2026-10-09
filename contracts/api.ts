/** Wire contracts shared by web and mobile. Dates are ISO 8601, money is BRL cents.
 * Type-only module: no runtime dependency or authorization logic.
 */
export type Page<T> = { results: T[]; nextCursor: string | null };
export type ProposalStatus = 'OPEN' | 'ACCEPTED' | 'DECLINED' | 'SUPERSEDED';
export type ServiceProposal = {
  id: string;
  number: number;
  scope: string;
  feeCents: number;
  currency: 'BRL';
  expenses: string;
  paymentTerms: string;
  validUntil: string;
  status: ProposalStatus;
  authorId: string;
  decidedById: string | null;
  decidedAt: string | null;
  createdAt: string;
};
export type ProposalInput = {
  version: number;
  scope: string;
  feeCents: number;
  expenses: string;
  paymentTerms: string;
  validUntil: string;
};
export type ProposalDecisionInput = { version: number; accepted: boolean };
export type ProposalResult = { proposal: ServiceProposal; version: number };

export type CaseState = 'RASCUNHO' | 'SUBMETIDO' | 'EM_TRIAGEM' | 'AGUARDANDO_CLIENTE'
  | 'ACEITO' | 'RECUSADO' | 'AGUARDANDO_PROCURACAO' | 'EM_PREPARACAO'
  | 'EM_ACOMPANHAMENTO' | 'ENCERRADO';
/** Title and narrative are omitted from administrative responses. */
export type CaseItem = {
  id: string; reference: string; category: string; categoryLabel: string;
  state: CaseState; stateLabel: string; version: number; lawyerId: string | null;
  createdAt: string; submittedAt: string | null; title?: string;
  description?: string; occurredOn?: string | null; scopeAcknowledged?: boolean;
};
/** canMessage is added only by the native detail endpoint. */
export type MobileCase = CaseItem & { title: string; canMessage?: boolean };
export type CaseEvent = { id: string; action: string; state: CaseState; reason: string; createdAt: string };
export type Message = {
  id: string; text: string; visibility: 'PUBLIC' | 'INTERNAL';
  authorId: string; authorName: string; createdAt: string;
};
export type RecentActivity = {
  id: string; caseId: string; reference: string; title: string;
  action: string; stateLabel: string; createdAt: string;
};

export type Portal = 'client' | 'team';
export type UserRole = 'CLIENT' | 'LAWYER' | 'ADMIN';
export type Profile = { id: string; name: string; email: string; caseEmailEnabled: boolean; role: UserRole };
export type ClientProfile = Omit<Profile, 'role'> & { role: 'CLIENT' };
export type AuthContext = { csrfToken: string; portal: Portal; policyVersion: string; mfaRequired: boolean; registrationAvailable: boolean };
export type Membership = { active: boolean; expiresAt: string | null };
export type SubmissionAccess = {
  canSubmit: boolean; mode: 'MEMBERSHIP' | 'INACTIVE' | 'ADMINISTRATIVE' | 'LOCAL_TEST' | 'UNAVAILABLE';
  message: string; expiresAt?: string;
};
export type Overview = {
  totalCases: number; attentionCount: number; unreadCount: number;
  states: { id: CaseState; label: string; count: number }[];
  attentionCases: CaseItem[]; recentActivity: RecentActivity[]; submission: SubmissionAccess | null;
};
export type MobileDashboard = Omit<Overview, 'attentionCases' | 'submission'> & {
  user: ClientProfile; membership: Membership; attentionCases: MobileCase[]; submission: SubmissionAccess;
};
export type Notice = {
  id: string; caseId: string; reference: string; kind: string; title: string;
  createdAt: string; readAt: string | null;
};
export type DocumentStatus = 'UPLOADING' | 'QUARANTINED' | 'SCANNING' | 'AVAILABLE' | 'REJECTED' | 'ERROR';
export type DocumentVersion = {
  id: string; documentId: string; uploadedById: string; number: number; filename: string;
  sizeBytes: number; status: DocumentStatus; statusLabel: string; createdAt: string;
};
export type DocumentUpload = { uploadId: string; uploadUrl: string; expiresAt: string; directUpload: boolean; version: DocumentVersion };
export type DirectUpload = { url: string; method: 'PUT'; headers: Record<string, string>; expiresIn: number };
export type BillingPlan = { amount: number; installments: number; planVersion: string; available: boolean; sandbox: boolean; policyVersion: string };
export type CaseCatalog = { categories: { id: string; label: string }[]; documentsAvailable: boolean; intakeRequired: boolean; submission: SubmissionAccess };
export type InformationRequest = { id: string; description: string; response: string; resolution: string; resolved: boolean; responded: boolean; attachments: DocumentVersion[] };
export type LegalWorkflow = {
  version: number; state: CaseState; scope: string; position: string; processNumber: string; authority: string;
  publishedText: string; protocol: string; mandate: DocumentVersion | null; signedMandate: DocumentVersion | null; receipt: DocumentVersion | null;
  tasks: { id: string; kind: string; title: string; dueAt: string; completedAt: string | null; outcome: string }[];
};
export type PrivacyRequest = { id: string; kind: 'ACCESS' | 'CORRECTION' | 'DELETION' | 'OTHER'; description: string; status: string; response: string; createdAt: string };
export type MobileContext = { policyVersion: string; registrationAvailable: boolean; billingAvailable: boolean; checkoutAvailable: boolean };
