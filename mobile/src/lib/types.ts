export type Session = { token: string; expiresAt: string; origin: string };
export type { MobileCase as Case, CaseEvent, Message, Page, ServiceProposal, ProposalResult, ProposalDecisionInput } from '../../../contracts/api';
export type { ClientProfile as Profile, MobileDashboard as Dashboard } from '../../../contracts/api';
