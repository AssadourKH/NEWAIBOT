// src/components/Sidebar.jsx
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function Sidebar() {
  const location = useLocation();
  const { user } = useAuth();

  const isActive = (path) => location.pathname.startsWith(path);

  return (
    <div className="bg-light border-end vh-100 p-3" style={{ width: "220px" }}>
      <h5 className="text-center mb-4">Dashboard</h5>
      <ul className="nav flex-column">
        {user?.role === "admin" && (
          <li className="nav-item">
            <Link className={`nav-link ${isActive("/dashboard/users") ? "active" : ""}`} to="/dashboard/users">
              Users
            </Link>
          </li>
        )}
        <li className="nav-item">
          <Link className={`nav-link ${isActive("/dashboard/orders") ? "active" : ""}`} to="/dashboard/orders">
            Orders
          </Link>
        </li>
        <li className="nav-item">
          <Link className={`nav-link ${isActive("/dashboard/conversations") ? "active" : ""}`} to="/dashboard/conversations">
            Conversations
          </Link>
        </li>
        {user?.role === "admin" && (
          <li className="nav-item">
            <Link className={`nav-link ${isActive("/dashboard/branches") ? "active" : ""}`} to="/dashboard/branches">
              Branches
            </Link>
          </li>
        )}
      </ul>
    </div>
  );
}

export default Sidebar;
