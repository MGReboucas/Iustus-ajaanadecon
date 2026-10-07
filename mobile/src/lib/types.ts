import type { MobileCase, RecentActivity } from '../../../contracts/api';
export type Profile = { id: string; name: string; email: string; role: 'CLIENT'; caseEmailEnabled: boolean };
export type Session = { token: string; expiresAt: string; origin: string };
export type { MobileCase as Case, CaseEvent, Message, Page, ServiceProposal, ProposalResult, ProposalDecisionInput } from '../../../contracts/api';
export type Dashboard = {
  user: Profile;
  membership: { active: boolean; expiresAt: string | null };
  totalCases: number; attentionCount: number; unreadCount: number;
  states: { id: string; label: string; count: number }[];
  attentionCases: MobileCase[];
  recentActivity: RecentActivity[];
  submission: { canSubmit: boolean; mode: string; message: string; expiresAt?: string };
};
