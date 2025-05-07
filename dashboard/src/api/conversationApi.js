import axiosInstance from "./axiosInstance";

export const getAllConversations = async (query = "") => {
    const { data } = await axiosInstance.get(`/conversations${query}`);
    return data;
  };
  
export const getMessagesByConversationId = async (id) => {
  const { data } = await axiosInstance.get(`/conversations/${id}/messages`);
  return data;
};
