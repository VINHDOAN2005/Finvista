import { request } from "./client.js";

export function getAdminSecretStatus() {
  return request("/api/admin/secrets/status");
}
