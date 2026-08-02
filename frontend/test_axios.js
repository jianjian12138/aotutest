const axios = require('axios');
const fs = require('fs');

// Mock the API instance as close as possible to the frontend
const api = axios.create({
  baseURL: 'http://localhost:5656/api', // Use Proxy URL
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    return Promise.reject(error);
  }
);

async function testExport() {
  try {
    const reportId = 10;
    const format = 'excel';
    
    console.log("Making Axios request...");
    const response = await api({
      url: `/reports/reports/${reportId}/fetch_report_file/`,
      method: 'get',
      params: { file_format: format },
      responseType: 'blob'
    });
    
    console.log("Axios Response structure:");
    console.log("- response type:", typeof response);
    console.log("- response.data type:", typeof response.data);
    console.log("- response.data constructor:", response.data && response.data.constructor ? response.data.constructor.name : 'null');
    console.log("- response Object keys:", Object.keys(response).join(", "));
    
    if (typeof response.data === 'object' && response.data !== null) {
      if (response.data instanceof Buffer) {
        console.log("Data is a Buffer!");
      } else {
        console.log("Data Object details (first 100 chars):", JSON.stringify(response.data).substring(0, 100));
      }
    } else if (typeof response.data === 'string') {
        console.log("Data is a String! Length:", response.data.length);
    }
  } catch (error) {
    console.error("Error:", error.message);
  }
}

testExport();
