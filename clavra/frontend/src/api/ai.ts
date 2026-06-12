import axios from "axios";

const API = "http://127.0.0.1:8000";

export const askAI = async (prompt: string) => {
  const response = await axios.post(`${API}/ai/ask`, {
    prompt,
  });

  return response.data;
};