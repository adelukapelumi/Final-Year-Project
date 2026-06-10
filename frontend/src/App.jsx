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

function createSessionInstanceId() {
  return window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [session, setSession] = useState(() => {
    const storedSession = readStoredJson(SESSION_KEY);
    if (storedSession?.token && !storedSession.sessionInstanceId) {
      return {
        ...storedSession,
        sessionInstanceId: createSessionInstanceId()
      };
    }
    return storedSession;
  });
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
      sessionInstanceId: createSessionInstanceId(),
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
    setReceipt({
      ...nextReceipt,
      sessionInstanceId: session.sessionInstanceId
    });
    navigate("/receipt");
  }

  function handleEndSession() {
    setSession(null);
    setReceipt(null);
    window.sessionStorage.removeItem(SESSION_KEY);
    window.sessionStorage.removeItem(RECEIPT_KEY);
    navigate("/");
  }

  const isAuthenticated = Boolean(session?.token);
  const isAccredited = isAuthenticated && Boolean(session?.biometricVerified);
  const onboardingRedirect = isAccredited ? "/dashboard" : "/camera";
  const hasCurrentReceipt =
    Boolean(receipt) &&
    Boolean(session?.sessionInstanceId) &&
    receipt?.sessionInstanceId === session.sessionInstanceId;

  return (
    <Layout
      isAuthenticated={isAuthenticated}
      currentPath={location.pathname}
      onLogout={handleEndSession}
      session={session}
    >
      <Routes>
        <Route
          path="/"
          element={isAuthenticated ? <Navigate to={onboardingRedirect} replace /> : <Home />}
        />
        <Route
          path="/login"
          element={
            isAuthenticated ? (
              <Navigate to={onboardingRedirect} replace />
            ) : (
              <Login onAuthenticated={handleAuthenticated} />
            )
          }
        />
        <Route
          path="/camera"
          element={
            isAccredited ? (
              <Navigate to="/dashboard" replace />
            ) : isAuthenticated ? (
              <BiometricVerification
                session={session}
                onEndSession={handleEndSession}
                onVerified={handleBiometricVerified}
              />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
        <Route
          path="/dashboard"
          element={
            isAccredited ? (
              <Dashboard session={session} onEndSession={handleEndSession} />
            ) : (
              <Navigate to={isAuthenticated ? "/camera" : "/login"} replace />
            )
          }
        />
        <Route
          path="/eligibility"
          element={<Navigate to={isAuthenticated ? onboardingRedirect : "/login"} replace />}
        />
        <Route
          path="/biometric-verify"
          element={<Navigate to={isAuthenticated ? onboardingRedirect : "/login"} replace />}
        />
        <Route
          path="/ballot"
          element={
            isAccredited && session?.eligibilityConfirmed ? (
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
            isAccredited && hasCurrentReceipt ? (
              <Receipt receipt={receipt} />
            ) : isAccredited ? (
              <Navigate to="/dashboard" replace />
            ) : (
              <Navigate to={isAuthenticated ? "/camera" : "/login"} replace />
            )
          }
        />
        <Route path="/board" element={<PublicBoard />} />
        <Route path="/tally" element={<Tally />} />
        <Route
          path="*"
          element={<Navigate to={isAuthenticated ? onboardingRedirect : "/"} replace />}
        />
      </Routes>
    </Layout>
  );
}
