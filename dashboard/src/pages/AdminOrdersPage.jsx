import React, { useEffect, useState } from "react";
import { getOrders, updateOrderStatus } from "../api/orderapi";
import { Table, Form, Button } from "react-bootstrap";

const statusOptions = ["confirmed", "preparing", "completed"];

export default function AdminOrdersPage() {
  const [orders, setOrders] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedOrder, setSelectedOrder] = useState(null);

  useEffect(() => {
    fetchOrders();
  }, []);

  const fetchOrders = async () => {
    try {
      const data = await getOrders();
      setOrders(data);
      console.log("Fetched orders:", data);
    } catch (err) {
      console.error("Failed to fetch orders:", err);
    }
  };

  const handleStatusChange = async (orderId, newStatus) => {
    try {
      await updateOrderStatus(orderId, newStatus);
      setOrders((prev) =>
        prev.map((order) =>
          order.id === orderId ? { ...order, status: newStatus } : order
        )
      );
    } catch (err) {
      console.error("Failed to update status:", err);
    }
  };

  const filteredOrders = statusFilter
    ? orders.filter((order) => order.status === statusFilter)
    : orders;

  return (
    <div className="container mt-4">
      <h2>All Orders </h2>

      <Form.Select
        className="w-25 my-3"
        value={statusFilter}
        onChange={(e) => setStatusFilter(e.target.value)}
      >
        <option value="">Filter by Status</option>
        {statusOptions.map((status) => (
          <option key={status}>{status}</option>
        ))}
      </Form.Select>

      <Table bordered hover responsive>
        <thead>
          <tr>
            <th>ID</th>
            <th>Customer</th>
            <th>Type</th>
            <th>Location</th>
            <th>Status</th>
            <th>Total</th>
            <th>Created At</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {filteredOrders.map((order) => (
            <tr key={order.id}>
              <td>{order.id}</td>
              <td>{order.customer_name}</td>
              <td className="text-capitalize">{order.order_type}</td>
              <td>
                {order.order_type === "delivery"
                  ? order.delivery_address
                  : order.branch}
              </td>
              <td>
                <Form.Select
                  value={order.status}
                  onChange={(e) =>
                    handleStatusChange(order.id, e.target.value)
                  }
                >
                  {statusOptions.map((status) => (
                    <option key={status}>{status}</option>
                  ))}
                </Form.Select>
              </td>
              <td>{order.total_price} LBP</td>
              <td>{new Date(order.created_at).toLocaleString()}</td>
              <td>
                <Button
                  variant="outline-primary"
                  onClick={() => setSelectedOrder(order)}
                >
                  View
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>

      {selectedOrder && (
        <div className="mt-4 p-3 border rounded bg-light">
          <Button
            variant="outline-secondary"
            size="sm"
            className="mb-3"
            onClick={() => setSelectedOrder(null)}
          >
            Close Details
          </Button>
          <h4>Order #{selectedOrder.id} Details</h4>
          <p>
            <strong>Customer:</strong> {selectedOrder.customer_name}
          </p>
          <p>
            <strong>Order Type:</strong> {selectedOrder.order_type}
          </p>
          <p>
            <strong>Location:</strong>{" "}
            {selectedOrder.order_type === "delivery"
              ? selectedOrder.delivery_address
              : selectedOrder.branch}
          </p>
          <p>
            <strong>Status:</strong> {selectedOrder.status}
          </p>
          <p>
            <strong>Contact:</strong> {selectedOrder.contact_phone}
          </p>
          <p>
            <strong>Total:</strong> {selectedOrder.total_price} LBP
          </p>
          <p>
            <strong>Created At:</strong>{" "}
            {new Date(selectedOrder.created_at).toLocaleString()}
          </p>

          <hr />
          <h5>Items:</h5>
          <ul>
            {(() => {
              try {
                const items = JSON.parse(selectedOrder.items);
                return items.map((item, index) => (
                  <li key={index}>
                    {item.name} — Qty: {item.quantity}
                    {item.modifications?.length > 0 && (
                      <ul>
                        {item.modifications.map((mod, i) => (
                          <li key={i} style={{ fontSize: "0.9em" }}>
                            {mod}
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                ));
              } catch (err) {
                return <li>⚠️ Failed to parse items</li>;
              }
            })()}
          </ul>
        </div>
      )}
    </div>
  );
}
