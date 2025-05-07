import React, { useEffect, useState, useRef } from "react";
import { getOrders, updateOrderStatus } from "../api/orderapi";
import { Card, Button, Row, Col, Spinner, Offcanvas } from "react-bootstrap";
import notificationSound from "../assets/Tech.wav"; // ✅ your sound file

const statusGroups = ["confirmed", "preparing", "completed"];

export default function AgentOrdersPage() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [showDetails, setShowDetails] = useState(false);
  const audioRef = useRef(null);
  const previousOrderIds = useRef(new Set());

  useEffect(() => {
    fetchOrders(true); // first load with sound disabled
    const interval = setInterval(() => fetchOrders(), 5000); // ✅ poll every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchOrders = async (initialLoad = false) => {
    try {
      const data = await getOrders();
      const newOrderIds = new Set(data.map((o) => o.id));

      // ✅ Detect new orders and play sound
      if (!initialLoad) {
        const isNewOrder = data.some((o) => !previousOrderIds.current.has(o.id));
        if (isNewOrder && audioRef.current) {
          audioRef.current.play().catch((err) => {
            console.warn("🔇 Unable to play sound (user interaction required)", err);
          });
        }
      }

      previousOrderIds.current = newOrderIds;
      setOrders(data);
    } catch (err) {
      console.error("Failed to fetch orders:", err);
    } finally {
      setLoading(false);
    }
  };

  const getNextStatus = (current) => {
    if (current === "confirmed") return "preparing";
    if (current === "preparing") return "completed";
    return null;
  };

  const handleStatusAdvance = async (orderId, currentStatus) => {
    const nextStatus = getNextStatus(currentStatus);
    if (!nextStatus) return;

    try {
      await updateOrderStatus(orderId, nextStatus);
      setOrders((prev) =>
        prev.map((order) =>
          order.id === orderId ? { ...order, status: nextStatus } : order
        )
      );
      if (selectedOrder?.id === orderId) {
        setSelectedOrder((prev) => ({ ...prev, status: nextStatus }));
      }
    } catch (err) {
      console.error("Failed to update status:", err);
    }
  };

  const handleCardClick = (order) => {
    setSelectedOrder(order);
    setShowDetails(true);
  };

  if (loading) {
    return (
      <div className="text-center mt-5">
        <Spinner animation="border" />
        <div>Loading today's orders...</div>
      </div>
    );
  }

  return (
    <div className="container-fluid mt-4">
      <audio ref={audioRef} src={notificationSound} preload="auto" />
      <h2>Today's Orders</h2>
      <Row className="flex-nowrap overflow-auto">
        {statusGroups.map((status) => (
          <Col key={status} style={{ minWidth: "300px" }}>
            <h5 className="text-center mb-3 text-capitalize">{status}</h5>
            {orders
              .filter((order) => order.status === status)
              .map((order) => (
                <Card
                  className="mb-3 shadow-sm cursor-pointer"
                  key={order.id}
                  onClick={() => handleCardClick(order)}
                >
                  <Card.Body>
                    <Card.Title>{order.customer_name}</Card.Title>
                    <Card.Subtitle className="mb-2 text-muted">
                      {order.order_type === "delivery"
                        ? `Address: ${order.delivery_address}`
                        : `Branch: ${order.branch}`}
                    </Card.Subtitle>
                    <Card.Text>
                      Total: {order.total_price} LBP
                      <br />
                      <small className="text-muted">Status: {order.status}</small>
                    </Card.Text>
                    {getNextStatus(order.status) && (
                      <Button
                        variant="success"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleStatusAdvance(order.id, order.status);
                        }}
                      >
                        Move to {getNextStatus(order.status)}
                      </Button>
                    )}
                  </Card.Body>
                </Card>
              ))}
          </Col>
        ))}
      </Row>

      <Offcanvas
        show={showDetails}
        onHide={() => setShowDetails(false)}
        placement="end"
        backdrop={false}
      >
        <Offcanvas.Header closeButton>
          <Offcanvas.Title>Order #{selectedOrder?.id}</Offcanvas.Title>
        </Offcanvas.Header>
        <Offcanvas.Body>
          {selectedOrder ? (
            <>
              <p>
                <strong>Customer:</strong> {selectedOrder.customer_name}
              </p>
              <p>
                <strong>Order Type:</strong> {selectedOrder.order_type}
              </p>
              <p>
                <strong>
                  {selectedOrder.order_type === "delivery" ? "Address:" : "Branch:"}
                </strong>{" "}
                {selectedOrder.order_type === "delivery"
                  ? selectedOrder.delivery_address
                  : selectedOrder.branch}
              </p>
              <p>
                <strong>Phone:</strong> {selectedOrder.contact_phone}
              </p>
              <p>
                <strong>Status:</strong>{" "}
                <span className="text-capitalize">{selectedOrder.status}</span>
              </p>
              <p>
                <strong>Total:</strong> {selectedOrder.total_price} LBP
              </p>
              <p>
                <strong>Created:</strong>{" "}
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
            </>
          ) : (
            <p>No order selected</p>
          )}
        </Offcanvas.Body>
      </Offcanvas>
    </div>
  );
}
