export type Profile = { id: string; name: string; email: string; role: 'CLIENT'; caseEmailEnabled: boolean };
export type Session = { token: string; expiresAt: string; origin: string };
export type Case = {
  id: string; reference: string; title: string; categoryLabel: string;
  version: number; state: string; stateLabel: string; createdAt: string; description?: string; occurredOn?: string | null; canMessage?: boolean;
};
export type Page<T> = { results: T[]; nextCursor: string | null };
export type Message = { id: string; text: string; authorId: string; authorName: string; createdAt: string };
export type CaseEvent = { id: string; action: string; state: string; reason: string; createdAt: string };
export type Dashboard = {
  user: Profile;
  membership: { active: boolean; expiresAt: string | null };
  totalCases: number; attentionCount: number; unreadCount: number;
  states: { id: string; label: string; count: number }[];
  attentionCases: Case[];
  recentActivity: { id: string; caseId: string; reference: string; title: string; action: string; stateLabel: string; createdAt: string }[];
  submission: { canSubmit: boolean; mode: string; message: string; expiresAt?: string };
};

export type ServiceProposal = { id: string; number: number; scope: string; feeCents: number; expenses: string; paymentTerms: string; validUntil: string; status: 'OPEN' | 'ACCEPTED' | 'DECLINED' | 'SUPERSEDED'; decidedAt: string | null };
