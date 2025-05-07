import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import axiosInstance from "../api/axiosInstance";
import { toast } from "react-toastify";
import { createUser, updateUser } from "../api/userapi";

export default function UsersPage() {
  const [search, setSearch] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState({ name: "", email: "", role: "", password: "" });

  const { data: users = [], isLoading, refetch } = useQuery({
    queryKey: ["users", search],
    queryFn: async () => {
      const res = await axiosInstance.get("/users", {
        params: search ? { search } : {},
      });
      return res.data;
    },
  });

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this user?")) return;
    try {
      await axiosInstance.delete(`/users/${id}`);
      toast.success("User deleted");
      refetch();
    } catch (err) {
      toast.error("Failed to delete user");
    }
  };

  const mutation = useMutation({
    mutationFn: async () => {
      if (editingUser) {
        const payload = { id: editingUser.id, ...formData };
        if (!formData.password) delete payload.password; // ✅ Remove if empty
        return await updateUser(payload);
      } else {
        return await createUser(formData);
      }
    },
    onSuccess: () => {
      toast.success(`User ${editingUser ? "updated" : "created"} successfully`);
      setShowModal(false);
      setEditingUser(null);
      setFormData({ name: "", email: "", role: "", password: "" });
      refetch();
    },
    onError: () => {
      toast.error("Error saving user");
    },
  });

  const openCreateModal = () => {
    setEditingUser(null);
    setFormData({ name: "", email: "", role: "", password: "" });
    setShowModal(true);
  };

  const openEditModal = (user) => {
    setEditingUser(user);
    setFormData({ name: user.name, email: user.email, role: user.role, password: "" });
    setShowModal(true);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    mutation.mutate();
  };

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h3>System Users</h3>
        <button className="btn btn-primary" onClick={openCreateModal}>
          + Add User
        </button>
      </div>

      <div className="mb-3 d-flex">
        <input
          className="form-control me-2"
          placeholder="Search by name or email..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button className="btn btn-secondary" onClick={() => refetch()}>
          Search
        </button>
      </div>

      {isLoading ? (
        <p>Loading...</p>
      ) : (
        <table className="table table-striped table-bordered">
          <thead>
            <tr>
              <th>#</th>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th style={{ width: "150px" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 ? (
              <tr>
                <td colSpan="5" className="text-center">
                  No users found.
                </td>
              </tr>
            ) : (
              users.map((user, index) => (
                <tr key={user.id}>
                  <td>{index + 1}</td>
                  <td>{user.name}</td>
                  <td>{user.email}</td>
                  <td>{user.role}</td>
                  <td>
                    <button
                      className="btn btn-sm btn-warning me-1"
                      onClick={() => openEditModal(user)}
                    >
                      Edit
                    </button>
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => handleDelete(user.id)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      )}

      {/* Modal */}
      {showModal && (
        <div className="modal show fade d-block" tabIndex="-1">
          <div className="modal-dialog">
            <form onSubmit={handleSubmit}>
              <div className="modal-content">
                <div className="modal-header">
                  <h5 className="modal-title">{editingUser ? "Edit User" : "Add User"}</h5>
                  <button type="button" className="btn-close" onClick={() => setShowModal(false)}></button>
                </div>
                <div className="modal-body">
                  <div className="mb-3">
                    <label className="form-label">Name</label>
                    <input
                      className="form-control"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      required
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Email</label>
                    <input
                      type="email"
                      className="form-control"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      required
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Role</label>
                    <select
                      className="form-select"
                      value={formData.role}
                      onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                      required
                    >
                      <option value="">Select</option>
                      <option value="admin">Admin</option>
                      <option value="agent">Agent</option>
                    </select>
                  </div>
                  {editingUser && (
                    <div className="mb-3">
                      <label className="form-label">Password (leave blank to keep current)</label>
                      <input
                        type="password"
                        className="form-control"
                        value={formData.password}
                        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                        required
                      />
                    </div>
                  )}
                </div>
                <div className="modal-footer">
                  <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary" disabled={mutation.isLoading}>
                    {mutation.isLoading ? "Saving..." : "Save"}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
