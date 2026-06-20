import type { InternalUserRole } from "../common/api";

export function canManageMerchantPortalUsers(role: InternalUserRole | undefined) {
  return role === "ADMIN" || role === "OPS";
}
