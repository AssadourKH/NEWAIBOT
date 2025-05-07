import { useQuery, useMutation } from "@tanstack/react-query";
import { useState } from "react";
import axiosInstance from "../api/axiosInstance";
import { toast } from "react-toastify";

export default function BranchesPage() {
  const [search, setSearch] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editingBranch, setEditingBranch] = useState(null);
  const [formData, setFormData] = useState({ name: "", location: "", delivery_time: "" });

  const { data: branches = [], isLoading, refetch } = useQuery({
    queryKey: ["branches", search],
    queryFn: async () => {
      const res = await axiosInstance.get("/branches", {
        params: search ? { search } : {},
      });
      return res.data;
    },
  });

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this branch?")) return;
    try {
      await axiosInstance.delete(`/branches/${id}`);
      toast.success("Branch deleted");
      refetch();
    } catch (err) {
      toast.error("Failed to delete branch");
    }
  };

  const mutation = useMutation({
    mutationFn: async () => {
      if (editingBranch) {
        return await axiosInstance.put(`/branches/${editingBranch.id}`, formData);
      } else {
        return await axiosInstance.post("/branches", formData);
      }
    },
    onSuccess: () => {
      toast.success(`Branch ${editingBranch ? "updated" : "created"} successfully`);
      setShowModal(false);
      setEditingBranch(null);
      setFormData({ name: "", location: "", delivery_time: "" });
      refetch();
    },
    onError: () => {
      toast.error("Error saving branch");
    },
  });

  const openCreateModal = () => {
    setEditingBranch(null);
    setFormData({ name: "", location: "", delivery_time: "" });
    setShowModal(true);
  };

  const openEditModal = (branch) => {
    setEditingBranch(branch);
    setFormData({ name: branch.name, location: branch.location, delivery_time: branch.delivery_time });
    setShowModal(true);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    mutation.mutate();
  };

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h3>Branches</h3>
        <button className="btn btn-primary" onClick={openCreateModal}>
          + Add Branch
        </button>
      </div>

      <div className="mb-3 d-flex">
        <input
          className="form-control me-2"
          placeholder="Search branches..."
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
              <th>Location</th>
              <th>Delivery Time</th>
              <th style={{ width: "150px" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {branches.length === 0 ? (
              <tr>
                <td colSpan="5" className="text-center">No branches found.</td>
              </tr>
            ) : (
              branches.map((branch, index) => (
                <tr key={branch.id}>
                  <td>{index + 1}</td>
                  <td>{branch.name}</td>
                  <td>{branch.location}</td>
                  <td>{branch.delivery_time}</td>
                  <td>
                    <button className="btn btn-sm btn-warning me-1" onClick={() => openEditModal(branch)}>
                      Edit
                    </button>
                    <button className="btn btn-sm btn-danger" onClick={() => handleDelete(branch.id)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      )}

      {showModal && (
        <div className="modal show fade d-block" tabIndex="-1">
          <div className="modal-dialog">
            <form onSubmit={handleSubmit}>
              <div className="modal-content">
                <div className="modal-header">
                  <h5 className="modal-title">{editingBranch ? "Edit Branch" : "Add Branch"}</h5>
                  <button type="button" className="btn-close" onClick={() => setShowModal(false)}></button>
                </div>
                <div className="modal-body">
                  <div className="mb-3">
                    <label className="form-label">Branch Name</label>
                    <input
                      className="form-control"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      required
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Location</label>
                    <input
                      className="form-control"
                      value={formData.location}
                      onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                      required
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Delivery Time</label>
                    <input
                      className="form-control"
                      value={formData.delivery_time}
                      onChange={(e) => setFormData({ ...formData, delivery_time: e.target.value })}
                      required
                    />
                  </div>
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
