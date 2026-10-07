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
