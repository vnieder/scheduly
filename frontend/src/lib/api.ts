// Use Next.js API proxy to bypass CORS issues
const API_BASE_URL = "/api/proxy";
const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://scheduly-backend-production.railway.app";

// Core data types matching backend schemas
export interface ChooseFrom {
  label: string;
  count: number;
  options: string[];
}

export interface Prereq {
  course: string;
  requires: string[];
}

export interface RequirementSet {
  catalogYear?: string;
  required: string[];
  genEds: ChooseFrom[];
  chooseFrom: ChooseFrom[];
  minCredits?: number;
  maxCredits?: number;
  prereqs: Prereq[];
  multiSemesterPrereqs: Prereq[];
}

export interface Section {
  course: string;
  crn: string;
  section: string;
  days: string[] | string;
  start: string;
  end: string;
  instructor?: string;
  credits: number;
}

export interface SchedulePlan {
  term: string;
  totalCredits: number;
  sections: Section[];
  explanations: string[];
  alternatives: Record<string, unknown>[];
}

export interface BuildScheduleRequest {
  school: string;
  major: string;
  term?: string;
  utterance?: string;
}

export interface BuildScheduleResponse {
  session_id: string;
  requirements: RequirementSet;
  plan: SchedulePlan;
}

export interface OptimizeScheduleRequest {
  session_id: string;
  utterance: string;
}

export interface OptimizeScheduleResponse {
  plan: SchedulePlan;
}

export interface HealthCheckResponse {
  ok: boolean;
  mode: string;
  development_mode: boolean;
  production_mode: boolean;
  supported_schools: string[];
  features: {
    hardcoded_requirements: boolean;
    ai_requirements: boolean;
    ai_prerequisites: boolean;
    multi_university: boolean;
  };
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    // Use Next.js API proxy to bypass CORS
    const url = this.baseUrl;

    const config: RequestInit = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      body: JSON.stringify({
        endpoint: endpoint,
        ...(options.body ? JSON.parse(options.body as string) : {}),
      }),
    };

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error("Network error occurred");
    }
  }

  async healthCheck(): Promise<HealthCheckResponse> {
    return this.request<HealthCheckResponse>("/health");
  }

  async buildSchedule(
    data: BuildScheduleRequest
  ): Promise<BuildScheduleResponse> {
    return this.request<BuildScheduleResponse>("/build", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async optimizeSchedule(
    data: OptimizeScheduleRequest
  ): Promise<OptimizeScheduleResponse> {
    return this.request<OptimizeScheduleResponse>("/optimize", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }
}

export const apiClient = new ApiClient();
