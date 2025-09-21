// Use Next.js API proxy to bypass CORS issues
const API_BASE_URL = "/api/proxy";

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

export interface ScheduleHistory {
  id: string;
  title: string;
  school: string;
  major: string;
  term: string;
  is_favorite: boolean;
  created_at: string;
  updated_at: string;
}

export interface SaveScheduleRequest {
  session_id: string;
  title?: string;
}

export interface SaveScheduleResponse {
  id: string;
  title: string;
  school: string;
  major: string;
  term: string;
  created_at: string;
}

export interface GetSchedulesResponse {
  schedules: ScheduleHistory[];
}

export interface GetScheduleResponse {
  id: string;
  title: string;
  school: string;
  major: string;
  term: string;
  schedule_data: SchedulePlan;
  is_favorite: boolean;
  created_at: string;
  updated_at: string;
}

export interface UpdateScheduleRequest {
  title?: string;
  is_favorite?: boolean;
}

export interface UserProfile {
  sub: string;
  email: string;
  name: string;
  picture: string;
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

    // Parse the request body if it exists
    let requestData = {};
    if (options.body) {
      try {
        requestData = JSON.parse(options.body as string);
      } catch (e) {
        console.error("Failed to parse request body:", e);
        requestData = {};
      }
    }

    const config: RequestInit = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      body: JSON.stringify({
        endpoint: endpoint,
        ...requestData,
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

  // User and Schedule Management Methods
  async saveSchedule(
    data: SaveScheduleRequest,
    authToken: string
  ): Promise<SaveScheduleResponse> {
    return this.request<SaveScheduleResponse>("/schedules", {
      method: "POST",
      body: JSON.stringify(data),
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    });
  }

  async getUserSchedules(
    authToken: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<GetSchedulesResponse> {
    return this.request<GetSchedulesResponse>(
      `/schedules?limit=${limit}&offset=${offset}`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      }
    );
  }

  async getSchedule(
    scheduleId: string,
    authToken: string
  ): Promise<GetScheduleResponse> {
    return this.request<GetScheduleResponse>(`/schedules/${scheduleId}`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    });
  }

  async updateSchedule(
    scheduleId: string,
    data: UpdateScheduleRequest,
    authToken: string
  ): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/schedules/${scheduleId}`, {
      method: "PUT",
      body: JSON.stringify(data),
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    });
  }

  async deleteSchedule(
    scheduleId: string,
    authToken: string
  ): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/schedules/${scheduleId}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    });
  }

  async getUserProfile(authToken: string): Promise<UserProfile> {
    return this.request<UserProfile>("/user/profile", {
      method: "GET",
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    });
  }
}

export const apiClient = new ApiClient();
