import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import Layout from "./components/Layout";
import Ballot from "./pages/Ballot";
import Login from "./pages/Login";
import PublicBoard from "./pages/PublicBoard";
import Receipt from "./pages/Receipt";
import Tally from "./pages/Tally";

const SESSION_KEY = "diaspora-vote-session";
const RECEIPT_KEY = "diaspora-vote-receipt";

function readStoredJson(key) {
  const value = window.sessionStorage.getItem(key);
  if (!value) {
    return null;
  }

  try {
    return JSON.parse(value);
  } catch {
    window.sessionStorage.removeItem(key);
    return null;
  }
}

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [session, setSession] = useState(() => readStoredJson(SESSION_KEY));
  const [receipt, setReceipt] = useState(() => readStoredJson(RECEIPT_KEY));

  useEffect(() => {
    if (session) {
      window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
    } else {
      window.sessionStorage.removeItem(SESSION_KEY);
    }
  }, [session]);

  useEffect(() => {
    if (receipt) {
      window.sessionStorage.setItem(RECEIPT_KEY, JSON.stringify(receipt));
    } else {
      window.sessionStorage.removeItem(RECEIPT_KEY);
    }
  }, [receipt]);

  function handleAuthenticated(nextSession) {
    setSession(nextSession);
    navigate("/ballot");
  }

  function handleReceipt(nextReceipt) {
    setReceipt(nextReceipt);
    navigate("/receipt");
  }

  function handleLogout() {
    setSession(null);
    setReceipt(null);
    navigate("/login");
  }

  const isAuthenticated = Boolean(session?.token);

  return (
    <Layout
      isAuthenticated={isAuthenticated}
      currentPath={location.pathname}
      onLogout={handleLogout}
    >
      <Routes>
        <Route
          path="/"
          element={<Navigate to={isAuthenticated ? "/ballot" : "/login"} replace />}
        />
        <Route
          path="/login"
          element={
            <Login
              session={session}
              onAuthenticated={handleAuthenticated}
            />
          }
        />
        <Route
          path="/ballot"
          element={
            isAuthenticated ? (
              <Ballot session={session} onReceiptReady={handleReceipt} />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
        <Route
          path="/receipt"
          element={
            isAuthenticated ? (
              <Receipt receipt={receipt} />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
        <Route path="/board" element={<PublicBoard />} />
        <Route path="/tally" element={<Tally />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
