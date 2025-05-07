import axiosInstance from "../api/axiosInstance";

export const createUser = async (userData) => {
  const response = await axiosInstance.post("/users", userData);
  return response.data;
};

export const updateUser = async ({ id, ...data }) => {
    const response = await axiosInstance.put(`/users/${id}`, data);
    return response.data;
  };
  