import React from "react";
import { useAuth } from "../context/AuthContext";
import AdminOrdersPage from "./AdminOrdersPage";
import AgentOrdersPage from "./AgentOrdersPage";

export default function OrdersPage() {
  const { user } = useAuth();

  if (!user) {
    return <div className="text-center mt-5 text-danger">Unauthorized</div>;
  }

  if (user.role === "admin") {
    return <AdminOrdersPage />;
  }

  if (user.role === "agent") {
    return <AgentOrdersPage />;
  }

  return <div className="text-center mt-5 text-danger">Invalid role</div>;
}
