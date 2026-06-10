import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import Layout from "./components/Layout";
import Ballot from "./pages/Ballot";
import BiometricVerification from "./pages/BiometricVerification";
import Dashboard from "./pages/Dashboard";
import Home from "./pages/Home";
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
    setSession({
      ...nextSession,
      eligibilityConfirmed: true,
      biometricVerified: false
    });
    setReceipt(null);
    navigate("/camera");
  }

  function handleBiometricVerified({ capturedImage, detectionMode }) {
    setSession((currentSession) => ({
      ...currentSession,
      biometricVerified: true,
      capturedImage,
      detectionMode
    }));
    navigate("/dashboard");
  }

  function handleReceipt(nextReceipt) {
    setReceipt(nextReceipt);
    navigate("/receipt");
  }

  function handleLogout() {
    setSession(null);
    setReceipt(null);
    navigate("/");
  }

  const isAuthenticated = Boolean(session?.token);

  return (
    <Layout
      isAuthenticated={isAuthenticated}
      currentPath={location.pathname}
      onLogout={handleLogout}
      session={session}
    >
      <Routes>
        <Route path="/" element={<Home />} />
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
          path="/camera"
          element={
            isAuthenticated ? (
              <BiometricVerification session={session} onVerified={handleBiometricVerified} />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
        <Route
          path="/dashboard"
          element={
            isAuthenticated && session?.biometricVerified ? (
              <Dashboard session={session} />
            ) : (
              <Navigate to={isAuthenticated ? "/camera" : "/login"} replace />
            )
          }
        />
        <Route path="/eligibility" element={<Navigate to={isAuthenticated ? "/camera" : "/login"} replace />} />
        <Route path="/biometric-verify" element={<Navigate to={isAuthenticated ? "/camera" : "/login"} replace />} />
        <Route
          path="/ballot"
          element={
            isAuthenticated && session?.eligibilityConfirmed && session?.biometricVerified ? (
              <Ballot session={session} onReceiptReady={handleReceipt} />
            ) : isAuthenticated ? (
              <Navigate to="/camera" replace />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
        <Route
          path="/receipt"
          element={
            isAuthenticated && session?.biometricVerified ? (
              <Receipt receipt={receipt} />
            ) : (
              <Navigate to={isAuthenticated ? "/camera" : "/login"} replace />
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
