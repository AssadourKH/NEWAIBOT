// src/components/Topbar.jsx
import { useAuth } from "../context/AuthContext";

function Topbar() {
  const { user, logout } = useAuth();
 

  return (
    <nav className="navbar navbar-light bg-white border-bottom px-4">
      <span className="navbar-brand mb-0 h1">Welcome, {user?.name || "User"}</span>
      <button className="btn btn-outline-danger btn-sm" onClick={logout}>Logout</button>
    </nav>
  );
}

export default Topbar;
