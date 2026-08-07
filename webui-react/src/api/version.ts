import { apiGet } from "./client";

export interface VersionStatus {
  current_version: string;
  complete: boolean;
  available_version: string | null;
  release_url: string;
}

export const getVersionStatus = () => apiGet<VersionStatus>("/version");
