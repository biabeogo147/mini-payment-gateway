import type { MerchantUserRole } from "../common/api";

type PortalUserRoleSelectProps = {
  disabled: boolean;
  email: string;
  role: MerchantUserRole;
  onChange: (role: MerchantUserRole) => void;
};

export function PortalUserRoleSelect({
  disabled,
  email,
  role,
  onChange,
}: PortalUserRoleSelectProps) {
  return (
    <select
      aria-label={`Role for ${email}`}
      className="portal-user-role-select"
      disabled={disabled}
      value={role}
      onChange={(event) => onChange(event.target.value as MerchantUserRole)}
    >
      <option value="MERCHANT_ADMIN">MERCHANT_ADMIN</option>
      <option value="MERCHANT_VIEWER">MERCHANT_VIEWER</option>
    </select>
  );
}
