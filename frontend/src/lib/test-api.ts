// Simple test to verify API client works
import { apiClient } from './api';

export async function testApiConnection() {
  try {
    const health = await apiClient.healthCheck();
    console.log('API Health Check:', health);
    return health;
  } catch (error) {
    console.error('API Connection Failed:', error);
    throw error;
  }
}

// Test function for development
export async function testBuildSchedule() {
  try {
    const response = await apiClient.buildSchedule({
      school: 'Pitt',
      major: 'Computer Science',
      term: '2251',
      utterance: ''
    });
    console.log('Build Schedule Response:', response);
    return response;
  } catch (error) {
    console.error('Build Schedule Failed:', error);
    throw error;
  }
}

