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
