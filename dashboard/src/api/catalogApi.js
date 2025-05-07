import axiosInstance from "./axiosInstance";

export const fetchCatalogFromFacebook = async () => {
  const { data } = await axiosInstance.get("/catalog/fetch");
  return data;
};
