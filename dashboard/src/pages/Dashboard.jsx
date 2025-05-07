import { Routes, Route } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import Topbar from "../components/Topbar";
import { useAuth } from "../context/AuthContext";

import UsersPage from "./UsersPage";
import OrdersPage from "./OrdersPage";
import ConversationsPage from "./ConversationsPage";
import BranchesPage from "./BranchesPage";
import AdminRoute from "../routes/AdminRoute";

function Dashboard() {
  const { user } = useAuth();

  return (
    <div className="d-flex">
      <Sidebar />
      <div className="flex-grow-1">
        <Topbar />
        <div className="p-4">
          <Routes>
            {/* Shared routes */}
            <Route path="/orders" element={<OrdersPage />} />
            <Route path="/conversations" element={<ConversationsPage />} />

            {/* Admin-only routes wrapped with AdminRoute */}
            <Route
              path="/users"
              element={
                <AdminRoute>
                  <UsersPage />
                </AdminRoute>
              }
            />
            <Route
              path="/branches"
              element={
                <AdminRoute>
                  <BranchesPage />
                </AdminRoute>
              }
            />
          </Routes>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
