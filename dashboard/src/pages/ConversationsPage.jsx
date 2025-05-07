import React, { useEffect, useState } from "react";
import { getAllConversations, getMessagesByConversationId } from "../api/conversationApi";
import { ListGroup, Spinner, Container, Row, Col, Card, Form } from "react-bootstrap";
import { useAuth } from "../context/AuthContext";

export default function ConversationsPage() {
  const { user } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [selectedDate, setSelectedDate] = useState("");

  useEffect(() => {
    fetchConversations();
  }, [selectedDate]);

  const fetchConversations = async () => {
    try {
      const dateParam = user?.role === "admin" && selectedDate ? `?date=${selectedDate}` : "";
      const data = await getAllConversations(dateParam);
      setConversations(data);
    } catch (err) {
      console.error("Failed to fetch conversations", err);
    } finally {
      setLoadingConversations(false);
    }
  };

  const handleConversationSelect = async (conv) => {
    setSelectedConversation(conv);
    setLoadingMessages(true);
    try {
      const msgs = await getMessagesByConversationId(conv.id);
      setMessages(msgs);
    } catch (err) {
      console.error("Failed to fetch messages", err);
    } finally {
      setLoadingMessages(false);
    }
  };

  return (
    <Container fluid className="mt-4">
      <Row>
        <Col md={4} className="border-end" style={{ height: "80vh", overflowY: "auto" }}>
          <h5>Conversations</h5>

          {/* ✅ Only admin sees date filter */}
          {user?.role === "admin" && (
            <Form.Control
              type="date"
              className="mb-3"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
            />
          )}

          {loadingConversations ? (
            <Spinner animation="border" />
          ) : (
            <ListGroup>
              {conversations.map((conv) => (
                <ListGroup.Item
                  key={conv.id}
                  action
                  active={selectedConversation?.id === conv.id}
                  onClick={() => handleConversationSelect(conv)}
                >
                  🧑 {conv.customer_name}
                  <br />
                  <small>{new Date(conv.started_at).toLocaleString()}</small>
                </ListGroup.Item>
              ))}
            </ListGroup>
          )}
        </Col>

        <Col md={8} style={{ height: "80vh", overflowY: "auto" }}>
          {selectedConversation ? (
            <>
              <h5>Chat with {selectedConversation.customer_name}</h5>
              {loadingMessages ? (
                <Spinner animation="border" />
              ) : (
                <div className="d-flex flex-column gap-2">
                  {messages.map((msg) => (
                    <Card
                      key={msg.id}
                      className={`p-2 ${
                        msg.direction === "incoming"
                          ? "align-self-start bg-light"
                          : "align-self-end bg-success text-white"
                      }`}
                      style={{ maxWidth: "70%" }}
                    >
                      <div>{msg.message_text}</div>
                      <small
                        className="text-muted d-block text-end"
                        style={{ fontSize: "0.75em" }}
                      >
                        {new Date(msg.timestamp).toLocaleString()}
                      </small>
                    </Card>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="text-muted">Select a conversation to view messages</div>
          )}
        </Col>
      </Row>
    </Container>
  );
}
