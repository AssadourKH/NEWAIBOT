import axiosInstance from "../api/axiosInstance";

// Fetch all (admin) or today's (agent) orders
export const getOrders = async () => {
  const { data } = await axiosInstance.get("/orders");
  return data;
};

export const updateOrderStatus = async (orderId, status) => {
  await axiosInstance.put(`/orders/${orderId}/status`, { status });
};
