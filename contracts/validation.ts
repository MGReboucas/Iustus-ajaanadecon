import type { BillingPlan, ClientProfile } from './api';
const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value);
const integer = (value: unknown): value is number => Number.isSafeInteger(value);
const nonempty = (value: unknown): value is string => typeof value === 'string' && value.trim().length > 0;
export function isBillingPlan(value: unknown): value is BillingPlan {
  return object(value) && integer(value.amount) && value.amount > 0
    && integer(value.installments) && value.installments >= 1 && value.installments <= 12
    && value.amount % value.installments === 0 && nonempty(value.planVersion)
    && nonempty(value.policyVersion) && typeof value.available === 'boolean' && typeof value.sandbox === 'boolean';
}
export type MobileLogin = { token: string; expiresAt: string; user: ClientProfile };
export function isMobileLogin(value: unknown): value is MobileLogin {
  if (!object(value) || typeof value.token !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(value.token)
      || typeof value.expiresAt !== 'string' || !Number.isFinite(Date.parse(value.expiresAt))
      || Date.parse(value.expiresAt) <= Date.now() || !object(value.user)) return false;
  const user = value.user;
  return user.role === 'CLIENT' && nonempty(user.id) && typeof user.name === 'string'
    && nonempty(user.email) && typeof user.caseEmailEnabled === 'boolean';
}
